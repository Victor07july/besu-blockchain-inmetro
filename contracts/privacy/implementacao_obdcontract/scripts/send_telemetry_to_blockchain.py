#!/usr/bin/env python3
"""
Script para enviar dados de telemetria processados ao E1RegistryTelemetry
Integração Web3.py + Hyperledger Besu

Entrada: CSV de telemetria processado (process_obdlink_telemetry.py)
Saída: Transações no contrato E1RegistryTelemetry

Autor: Victor
Data: 2026-02-23
"""

import pandas as pd
import json
from web3 import Web3
from eth_account import Account
from datetime import datetime
from typing import Dict, List
import time
import sys


class E1TelemetryContractInterface:
    """Interface para contrato E1RegistryTelemetry"""
    
    def __init__(self, rpc_url: str, contract_address: str, 
                 contract_abi: List, private_key: str):
        """
        Inicializa conexão com o contrato
        
        Args:
            rpc_url: URL do nó Besu
            contract_address: Endereço do contrato
            contract_abi: ABI do contrato
            private_key: Chave privada da conta oracle
        """
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        
        # Adicionar middleware POA para Besu/QBFT
        from web3.middleware import ExtraDataToPOAMiddleware
        self.w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
        
        try:
            chain_id = self.w3.eth.chain_id
            block_number = self.w3.eth.block_number
            print(f"✓ Conectado ao Besu: {rpc_url}")
            print(f"  Chain ID: {chain_id}")
            print(f"  Block number: {block_number}")
        except Exception as e:
            raise ConnectionError(f"Não foi possível conectar ao nó: {rpc_url} - {e}")
        
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
        
        print(f"✓ Contrato E1RegistryTelemetry: {contract_address}")
        
    def coords_to_int256(self, lat: float, lon: float) -> tuple:
        """
        Converte coordenadas para int256 (× 1e6)
        
        Args:
            lat: Latitude
            lon: Longitude
            
        Returns:
            Tupla (lat_int, lon_int)
        """
        lat_int = int(lat * 1_000_000)
        lon_int = int(lon * 1_000_000)
        return lat_int, lon_int
    
    def prepare_telemetry_params(self, row: pd.Series, 
                                 carbon_price: int = 50_000_000) -> Dict:
        """
        Prepara parâmetros para registerTrip do E1RegistryTelemetry
        
        Args:
            row: Linha do DataFrame
            carbon_price: Preço do carbono (R$/ton × 1e6)
            
        Returns:
            Dicionário com parâmetros formatados
        """
        # Converter coordenadas
        start_lat, start_lon = self.coords_to_int256(
            row['start_lat_private'],
            row['start_lon_private']
        )
        end_lat, end_lon = self.coords_to_int256(
            row['end_lat_private'],
            row['end_lon_private']
        )
        
        # Elevação
        start_elevation = int(row['start_elevation']) if pd.notna(row['start_elevation']) else 0
        end_elevation = int(row['end_elevation']) if pd.notna(row['end_elevation']) else 0
        
        # Velocidade média (km/h × 1e3)
        avg_speed = int(row['avg_speed'] * 1_000)
        
        # Percentual de etanol (% × 1e3)
        ethanol_percent = int(row['ethanol_percent'] * 1_000)
        
        # Fuel rate (l/hr × 1e3)
        fuel_rate_avg = int(row['fuel_rate_avg'] * 1_000)
        
        # Duração da viagem (segundos)
        trip_duration = int(row['trip_duration'])
        
        # Timestamp
        timestamp = int(row['timestamp'])
        
        # Gerar pseudônimo (20 bytes = 40 hex chars de um endereço)
        pseudonimo_hash = self.w3.keccak(text=row['vin'])
        pseudonimo_address = self.w3.to_checksum_address(pseudonimo_hash[:20])  # Primeiros 20 bytes
        
        params = {
            'vin': row['vin'],
            'timestamp': timestamp,
            'startLocation': (start_lat, start_lon),
            'endLocation': (end_lat, end_lon),
            'startElevation': start_elevation,
            'endElevation': end_elevation,
            'avgSpeed': avg_speed,
            'ethanolPercent': ethanol_percent,
            'fuelRateAvg': fuel_rate_avg,
            'tripDuration': trip_duration,
            'carbonPrice': carbon_price,
            'pseudonimo': pseudonimo_address
        }
        
        return params
    
    def register_trip(self, params: Dict) -> str:
        """
        Registra viagem no contrato
        
        Args:
            params: Parâmetros da viagem
            
        Returns:
            Hash da transação
        """
        nonce = self.w3.eth.get_transaction_count(self.address)
        
        # Estimar gas
        try:
            gas_estimate = self.contract.functions.registerTrip(params).estimate_gas({
                'from': self.address
            })
        except Exception as e:
            print(f"  ⚠️  Erro ao estimar gas: {e}")
            gas_estimate = 500_000
        
        # Construir transação
        transaction = self.contract.functions.registerTrip(params).build_transaction({
            'from': self.address,
            'nonce': nonce,
            'gas': gas_estimate + 50_000,
            'gasPrice': self.w3.eth.gas_price,
        })
        
        # Assinar
        signed_txn = self.w3.eth.account.sign_transaction(
            transaction, 
            private_key=self.account.key
        )
        
        # Enviar
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)
        
        print(f"  📤 TX enviada: {tx_hash.hex()}")
        
        return tx_hash.hex()
    
    def wait_for_receipt(self, tx_hash: str, timeout: int = 120) -> dict:
        """
        Aguarda confirmação da transação
        
        Args:
            tx_hash: Hash da transação
            timeout: Tempo máximo de espera (segundos)
            
        Returns:
            Receipt da transação
        """
        try:
            receipt = self.w3.eth.wait_for_transaction_receipt(
                tx_hash, timeout=timeout
            )
            return receipt
        except Exception as e:
            print(f"  ❌ Timeout aguardando confirmação: {e}")
            return None


def send_trips_to_blockchain(csv_file: str):
    """
    Envia viagens do CSV ao contrato E1RegistryTelemetry
    Usa configurações hardcoded (rpc_url, private_key, contract_address)
    
    Args:
        csv_file: Caminho do CSV processado
    """
    # Configurações fixas
    rpc_url = "http://localhost:8545"
    private_key = "0x8f2a55949038a9610f50fb23b5883af3b4ecb3c3bb792cbcefbd1542c692be63"
    carbon_price = 50_000_000  # R$ 50/ton × 1e6
    
    print("="*70)
    print("🔗 ENVIO DE TELEMETRIA AO BLOCKCHAIN")
    print("="*70)
    print(f"📄 Arquivo: {csv_file}")
    print(f"🌐 RPC: {rpc_url}")
    print(f"💰 Carbon price: R$ {carbon_price / 1_000_000:.2f}/ton")
    print("="*70)
    
    # Carregar dados
    print("\n📊 Carregando viagens...")
    df = pd.read_csv(csv_file)
    print(f"   Total de viagens: {len(df)}")
    
    # Carregar endereço do contrato de deployment_info.json
    deployment_file = "../deployment_info.json"
    try:
        with open(deployment_file, 'r') as f:
            deployment_info = json.load(f)
            contract_address = deployment_info['contract_address']
            contract_abi = deployment_info['abi']
            print(f"\n✓ Contrato carregado de {deployment_file}")
            print(f"  Endereço: {contract_address}")
    except FileNotFoundError:
        print(f"❌ Arquivo {deployment_file} não encontrado!")
        print("   Execute o deploy primeiro: python3 deploy_telemetry.py")
        return
    except KeyError as e:
        print(f"❌ Chave ausente no deployment_info.json: {e}")
        return
    
    interface = E1TelemetryContractInterface(
        rpc_url, contract_address, contract_abi, private_key
    )
    
    # Enviar viagens
    print("\n🚀 Enviando viagens ao blockchain...")
    print("-" * 70)
    
    success_count = 0
    failed_count = 0
    
    for idx, row in df.iterrows():
        print(f"\n[{idx+1}/{len(df)}] VIN: {row['vin']} | Trip: {row['trip_id']}")
        
        try:
            # Preparar parâmetros
            params = interface.prepare_telemetry_params(row, carbon_price)
            
            print(f"  Fuel rate: {row['fuel_rate_avg']:.2f} l/hr")
            print(f"  Duração: {row['trip_duration']:.0f}s")
            print(f"  Etanol: {row['ethanol_percent']:.1f}%")
            print(f"  Elevação: {params['startElevation']}m")
            
            # Enviar transação
            tx_hash = interface.register_trip(params)
            
            # Aguardar confirmação
            print(f"  ⏳ Aguardando confirmação...")
            receipt = interface.wait_for_receipt(tx_hash)
            
            if receipt and receipt['status'] == 1:
                print(f"  ✅ Confirmada! Block: {receipt['blockNumber']}")
                success_count += 1
            else:
                print(f"  ❌ Falhou!")
                failed_count += 1
            
            # Pequeno delay para evitar sobrecarga
            time.sleep(1)
            
        except Exception as e:
            print(f"  ❌ Erro: {e}")
            failed_count += 1
    
    # Resumo
    print("\n" + "="*70)
    print("📊 RESUMO DO ENVIO")
    print("="*70)
    print(f"✅ Sucesso: {success_count}")
    print(f"❌ Falhas: {failed_count}")
    print(f"📈 Taxa de sucesso: {success_count / len(df) * 100:.1f}%")
    print("="*70)


def main():
    """Função principal"""
    if len(sys.argv) < 2:
        print("Uso: python3 send_telemetry_to_blockchain.py <trips_telemetry.csv>")
        print("\nExemplo:")
        print("  python3 send_telemetry_to_blockchain.py trips.csv")
        print("\nO endereço do contrato será carregado de ../deployment_info.json")
        print("Execute primeiro: python3 deploy_telemetry.py")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    
    try:
        send_trips_to_blockchain(csv_file)
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
