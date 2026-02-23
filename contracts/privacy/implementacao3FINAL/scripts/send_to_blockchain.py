#!/usr/bin/env python3
"""
Script para enviar dados com privacidade diferencial para o contrato E1RegistryGPS
Integração Web3.py + Hyperledger Besu

Autor: Victor
Data: 2026-02-09
"""

import pandas as pd
import json
from web3 import Web3
from eth_account import Account
from datetime import datetime
from typing import Dict, List, Optional
import time


class E1GPSContractInterface:
    """Interface para interação com o contrato E1RegistryGPS no Besu"""
    
    def __init__(self, rpc_url: str, contract_address: str, 
                 contract_abi: List, private_key: str):
        """
        Inicializa a conexão com o contrato
        
        Args:
            rpc_url: URL do nó Besu (ex: http://localhost:8545)
            contract_address: Endereço do contrato deployado
            contract_abi: ABI do contrato
            private_key: Chave privada da conta oracle
        """
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        
        if not self.w3.is_connected():
            raise ConnectionError(f"Não foi possível conectar ao nó: {rpc_url}")
        
        print(f"✓ Conectado ao Besu: {rpc_url}")
        print(f"  Chain ID: {self.w3.eth.chain_id}")
        print(f"  Block number: {self.w3.eth.block_number}")
        
        # Configurar conta
        self.account = Account.from_key(private_key)
        self.address = self.account.address
        
        balance = self.w3.eth.get_balance(self.address)
        print(f"  Oracle address: {self.address}")
        print(f"  Balance: {self.w3.from_wei(balance, 'ether')} ETH")
        
        # Conectar ao contrato
        self.contract = self.w3.eth.contract(
            address=contract_address,
            abi=contract_abi
        )
        
        print(f"✓ Contrato carregado: {contract_address}")
        
    def coords_to_int256(self, lat: float, lon: float) -> tuple:
        """
        Converte coordenadas float para int256 (× 1e6)
        
        Args:
            lat: Latitude
            lon: Longitude
            
        Returns:
            Tupla (lat_int, lon_int)
        """
        lat_int = int(lat * 1_000_000)
        lon_int = int(lon * 1_000_000)
        return lat_int, lon_int
    
    def prepare_trip_params(self, row: pd.Series) -> Dict:
        """
        Prepara parâmetros para a função registerTrip do contrato
        
        Args:
            row: Linha do DataFrame com dados da viagem
            
        Returns:
            Dicionário com parâmetros formatados
        """
        # Converter coordenadas protegidas para int256
        start_lat, start_lon = self.coords_to_int256(
            row['start_lat_private'],
            row['start_lon_private']
        )
        end_lat, end_lon = self.coords_to_int256(
            row['end_lat_private'],
            row['end_lon_private']
        )
        
        # Timestamp
        if isinstance(row['start_time'], str):
            timestamp = int(datetime.fromisoformat(row['start_time']).timestamp())
        else:
            timestamp = int(row['start_time'].timestamp())
        
        # Calcular distâncias
        highway_distance = int(row['highway (distance)'] * 1_000_000)  # km → × 1e6
        city_distance = int(row['city (distance)'] * 1_000_000)
        
        # Percentual de etanol
        ethanol_percent = int(float(row['ethanol (%)']) * 100)  # Converter para base 100
        
        # Emissões por tipo de combustível e via
        # Simplificação: distribuir proporcionalmente
        total_dist = row['highway (distance)'] + row['city (distance)']
        highway_pct = row['highway (distance)'] / total_dist if total_dist > 0 else 0.5
        city_pct = row['city (distance)'] / total_dist if total_dist > 0 else 0.5
        
        emission = int(row['emission'] * 1_000_000)  # g → × 1e6
        
        # Distribuir emissão entre gasolina e etanol
        if row['fuel_type'] == 'Gasolina':
            gas_emission = emission
            eth_emission = 0
        elif row['fuel_type'] == 'Etanol':
            gas_emission = 0
            eth_emission = emission
        else:  # Flex
            eth_ratio = float(row['ethanol (%)']) / 100
            eth_emission = int(emission * eth_ratio)
            gas_emission = emission - eth_emission
        
        # Distribuir entre rodovia e cidade
        road_gasoline = int(gas_emission * highway_pct)
        city_gasoline = int(gas_emission * city_pct)
        road_ethanol = int(eth_emission * highway_pct)
        city_ethanol = int(eth_emission * city_pct)
        
        # Carbon price (exemplo: R$ 50/ton CO2 = R$ 0.05/kg = R$ 50/g × 1e6)
        carbon_price = 50_000_000  # R$ 50/ton em unidades × 1e6
        
        # Gerar pseudônimo baseado no VIN (hash)
        pseudonimo = self.w3.keccak(text=row['VIN']).hex()
        pseudonimo_address = self.w3.to_checksum_address(pseudonimo[:42])
        
        # Obter elevação (se disponível)
        start_elevation = 0
        if 'start_elevation_private' in row.index and pd.notna(row['start_elevation_private']):
            start_elevation = int(row['start_elevation_private'])
        
        params = {
            'vin': row['VIN'],
            'timestamp': timestamp,
            'highwayDistance': highway_distance,
            'cityDistance': city_distance,
            'ethanolPercent': ethanol_percent,
            'roadGasoline': max(road_gasoline, 1),  # Garantir > 0
            'roadEthanol': max(road_ethanol, 1),
            'cityGasoline': max(city_gasoline, 1),
            'cityEthanol': max(city_ethanol, 1),
            'emissaoReal': emission,
            'carbonPrice': carbon_price,
            'pseudonimo': pseudonimo_address,
            'startLocation': (start_lat, start_lon),
            'endLocation': (end_lat, end_lon),
            'startElevation': start_elevation
        }
        
        return params
    
    def register_trip(self, params: Dict) -> str:
        """
        Registra uma viagem no contrato
        
        Args:
            params: Parâmetros da viagem
            
        Returns:
            Hash da transação
        """
        # Construir transação
        nonce = self.w3.eth.get_transaction_count(self.address)
        
        # Estimar gas
        try:
            gas_estimate = self.contract.functions.registerTrip(params).estimate_gas({
                'from': self.address
            })
        except Exception as e:
            print(f"❌ Erro ao estimar gas: {e}")
            gas_estimate = 500_000  # Fallback
        
        # Construir transação
        transaction = self.contract.functions.registerTrip(params).build_transaction({
            'from': self.address,
            'nonce': nonce,
            'gas': gas_estimate + 50_000,  # Adicionar margem
            'gasPrice': self.w3.eth.gas_price,
        })
        
        # Assinar transação
        signed_txn = self.w3.eth.account.sign_transaction(
            transaction, 
            private_key=self.account.key
        )
        
        # Enviar transação
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        
        print(f"  📤 TX enviada: {tx_hash.hex()}")
        
        return tx_hash.hex()
    
    def wait_for_receipt(self, tx_hash: str, timeout: int = 120) -> Dict:
        """
        Aguarda confirmação da transação
        
        Args:
            tx_hash: Hash da transação
            timeout: Timeout em segundos
            
        Returns:
            Receipt da transação
        """
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=timeout)
        
        if receipt['status'] == 1:
            print(f"  ✓ TX confirmada no bloco {receipt['blockNumber']}")
            print(f"    Gas usado: {receipt['gasUsed']}")
        else:
            print(f"  ❌ TX falhou!")
        
        return receipt
    
    def get_trip_count(self) -> int:
        """Retorna número total de viagens registradas"""
        return self.contract.functions.tripCount().call()
    
    def get_trip(self, trip_id: int) -> Dict:
        """
        Obtém dados de uma viagem
        
        Args:
            trip_id: ID da viagem
            
        Returns:
            Dicionário com dados da viagem
        """
        trip = self.contract.functions.trips(trip_id).call()
        
        return {
            'vin': trip[0],
            'timestamp': trip[1],
            'totalDistance': trip[2],
            'emissaoReal': trip[3],
            'metaCO2': trip[4],
            'diff': trip[5],
            'realPrice': trip[6],
            'valorE1': trip[7],
            'pseudonimo': trip[8],
            'pago': trip[9],
            'startLocation': {
                'lat': trip[10][0] / 1_000_000,
                'lon': trip[10][1] / 1_000_000
            },
            'endLocation': {
                'lat': trip[11][0] / 1_000_000,
                'lon': trip[11][1] / 1_000_000
            },
            'gpsDistance': trip[12] / 1_000_000
        }


def send_to_blockchain(csv_file: str, config_file: str, 
                      batch_size: int = 10, delay: float = 2.0):
    """
    Envia dados processados para o contrato no blockchain
    
    Args:
        csv_file: Arquivo CSV com dados protegidos por DP
        config_file: Arquivo JSON com configurações do contrato
        batch_size: Número de transações por batch
        delay: Delay entre transações (segundos)
    """
    print("="*70)
    print("🔗 ENVIO DE DADOS PARA BLOCKCHAIN")
    print("="*70)
    
    # Carregar configurações
    print(f"📄 Carregando configurações: {config_file}")
    with open(config_file, 'r') as f:
        config = json.load(f)
    
    # Carregar dados
    print(f"📊 Carregando dados: {csv_file}")
    df = pd.read_csv(csv_file)
    
    # Filtrar apenas viagens processadas com DP
    if 'dp_processed' in df.columns:
        df = df[df['dp_processed'] == True]
        print(f"   Viagens com DP: {len(df)}")
    
    # Inicializar interface
    interface = E1GPSContractInterface(
        rpc_url=config['rpc_url'],
        contract_address=config['contract_address'],
        contract_abi=config['contract_abi'],
        private_key=config['oracle_private_key']
    )
    
    print(f"\n🚀 Iniciando envio de {len(df)} viagens...")
    print("-" * 70)
    
    results = []
    success_count = 0
    fail_count = 0
    
    for idx, row in df.iterrows():
        print(f"\n[{idx+1}/{len(df)}] VIN: {row['VIN']}")
        
        try:
            # Preparar parâmetros
            params = interface.prepare_trip_params(row)
            
            # Registrar viagem
            tx_hash = interface.register_trip(params)
            
            # Aguardar confirmação
            receipt = interface.wait_for_receipt(tx_hash)
            
            if receipt['status'] == 1:
                success_count += 1
                results.append({
                    'vin': row['VIN'],
                    'tx_hash': tx_hash,
                    'status': 'success',
                    'block': receipt['blockNumber'],
                    'gas_used': receipt['gasUsed']
                })
            else:
                fail_count += 1
                results.append({
                    'vin': row['VIN'],
                    'tx_hash': tx_hash,
                    'status': 'failed',
                    'error': 'Transaction reverted'
                })
            
            # Delay entre transações
            if (idx + 1) % batch_size == 0:
                print(f"\n⏸️  Pausa entre batches...")
                time.sleep(delay * 2)
            else:
                time.sleep(delay)
            
        except Exception as e:
            print(f"❌ Erro: {e}")
            fail_count += 1
            results.append({
                'vin': row['VIN'],
                'status': 'error',
                'error': str(e)
            })
    
    # Salvar resultados
    results_df = pd.DataFrame(results)
    results_file = csv_file.replace('.csv', '_blockchain_results.csv')
    results_df.to_csv(results_file, index=False)
    
    # Resumo
    print("\n" + "="*70)
    print("📊 RESUMO DO ENVIO")
    print("="*70)
    print(f"✓ Sucesso: {success_count}")
    print(f"❌ Falhas: {fail_count}")
    print(f"📄 Resultados salvos em: {results_file}")
    
    # Verificar contrato
    total_trips = interface.get_trip_count()
    print(f"\n🔢 Total de viagens no contrato: {total_trips}")
    
    print("="*70)


def main():
    """Função principal"""
    import sys
    
    if len(sys.argv) < 3:
        print("Uso: python send_to_blockchain.py <dados_private.csv> <config.json>")
        print("\nExemplo:")
        print("  python send_to_blockchain.py dados_private.csv e1_gps_contract_address.json")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    config_file = sys.argv[2]
    
    send_to_blockchain(csv_file, config_file)


if __name__ == "__main__":
    main()
