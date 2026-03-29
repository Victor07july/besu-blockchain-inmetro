#!/usr/bin/env python3
"""
Script para enviar viagens processadas ao E1RegistryEuclidean
Lê CSV gerado por process_obd_euclidean.py e envia ao blockchain

Entrada: trips_processed.csv
Saída: Transações no contrato

Autor: Victor
Data: 2026-02-28
"""

import json
import pandas as pd
import sys
import time
from web3 import Web3
from eth_account import Account


def coords_to_int256(lat: float, lon: float) -> tuple:
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


def generate_pseudonimo(vin: str, trip_id: int) -> str:
    """
    Gera pseudônimo baseado em hash do VIN + trip ID
    
    Args:
        vin: VIN do veículo
        trip_id: ID da viagem
        
    Returns:
        Endereço pseudônimo
    """
    # Criar hash único
    data_str = f"{vin}_{trip_id}"
    hash_bytes = Web3.keccak(text=data_str)
    
    # Primeiros 20 bytes = endereço
    address = Web3.to_checksum_address(hash_bytes[:20])
    return address


def send_trips_to_blockchain(csv_file: str):
    """
    Envia viagens do CSV ao contrato E1RegistryEuclidean
    
    Args:
        csv_file: Caminho do CSV processado
    """
    print("="*70)
    print("🔗 ENVIO DE VIAGENS AO BLOCKCHAIN")
    print("="*70)
    print(f"📄 Arquivo: {csv_file}")
    print("="*70)
    
    # Carregar deployment info
    deployment_file = "deployment_info.json"
    try:
        with open(deployment_file, 'r') as f:
            deployment = json.load(f)
            contract_address = deployment['contract_address']
            contract_abi = deployment['abi']
            rpc_url = deployment['rpc_url']
            print(f"\n✓ Contrato carregado: {contract_address}")
    except FileNotFoundError:
        print(f"❌ Arquivo {deployment_file} não encontrado!")
        print("   Execute o deploy primeiro: python3 deploy_e1_euclidean.py")
        return
    except KeyError as e:
        print(f"❌ Chave ausente no deployment_info.json: {e}")
        return
    
    # Carregar dados
    print("\n📊 Carregando viagens...")
    df = pd.read_csv(csv_file)
    print(f"   Total de viagens: {len(df)}")
    
    # Configurar Web3
    private_key = "0x8f2a55949038a9610f50fb23b5883af3b4ecb3c3bb792cbcefbd1542c692be63"
    account = Account.from_key(private_key)
    
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    
    # Adicionar middleware POA
    from web3.middleware import ExtraDataToPOAMiddleware
    w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    
    # Verificar conexão
    try:
        chain_id = w3.eth.chain_id
        print(f"✓ Conectado - Chain ID: {chain_id}")
    except Exception as e:
        raise ConnectionError(f"Erro ao conectar: {e}")
    
    print(f"  Oracle address: {account.address}")
    print(f"  Balance: {w3.from_wei(w3.eth.get_balance(account.address), 'ether')} ETH")
    
    # Conectar ao contrato
    contract = w3.eth.contract(
        address=contract_address,
        abi=contract_abi
    )
    
    # Enviar viagens
    print("\n🚀 Enviando viagens ao blockchain...")
    print("-" * 70)
    
    success_count = 0
    failed_count = 0
    
    for idx, row in df.iterrows():
        print(f"\n[{idx+1}/{len(df)}] VIN: {row['vin']} | Trip: {row['trip_id']}")
        
        try:
            # Converter coordenadas
            start_lat, start_lon = coords_to_int256(
                row['start_lat_private'],
                row['start_lon_private']
            )
            end_lat, end_lon = coords_to_int256(
                row['end_lat_private'],
                row['end_lon_private']
            )
            
            # Gerar pseudônimo
            pseudonimo = generate_pseudonimo(row['vin'], int(row['trip_id']))
            
            # Preparar struct TripData
            trip_data = (
                row['vin'],                                        # vin
                int(row['timestamp']),                             # timestamp
                int(row['total_distance_km'] * 1_000_000),         # totalDistance
                int(row['fuel_consumed_liters'] * 1_000_000),      # fuelConsumed
                int(row['co2_real_kg'] * 1_000_000),               # co2Real
                int(row['co2_meta_kg'] * 1_000_000),               # co2Meta
                int(row['valor_e1_reais'] * 1_000_000),            # valorE1
                int(row['avg_ethanol_percent'] * 1_000),           # avgEthanolPercent
                (start_lat, start_lon),                            # startLocation
                (end_lat, end_lon),                                # endLocation
                pseudonimo,                                        # pseudonimo
                False                                              # pago
            )
            
            print(f"  📏 Distância: {row['total_distance_km']:.2f} km")
            print(f"  ⛽ Combustível: {row['fuel_consumed_liters']:.3f} l")
            print(f"  🏭 CO2 real: {row['co2_real_kg']:.3f} kg")
            print(f"  🎯 CO2 meta: {row['co2_meta_kg']:.3f} kg")
            print(f"  📊 Δ CO2: {row['delta_co2_kg']:+.3f} kg")
            print(f"  💰 Valor E1: R$ {row['valor_e1_reais']:+.4f}")
            
            # Construir transação
            nonce = w3.eth.get_transaction_count(account.address)
            
            txn = contract.functions.registerTrip(trip_data).build_transaction({
                'from': account.address,
                'nonce': nonce,
                'gas': 500000,
                'gasPrice': w3.eth.gas_price,
            })
            
            # Assinar
            signed_txn = w3.eth.account.sign_transaction(txn, private_key)
            
            # Enviar
            tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)
            print(f"  📤 TX enviada: {tx_hash.hex()[:20]}...")
            
            # Aguardar confirmação
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            
            if receipt['status'] == 1:
                print(f"  ✅ Confirmada! Block: {receipt['blockNumber']} | Gas: {receipt['gasUsed']}")
                success_count += 1
            else:
                print(f"  ❌ Falhou na confirmação")
                failed_count += 1
            
            # Delay para não sobrecarregar
            time.sleep(0.5)
            
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
    
    # Estatísticas do contrato
    if success_count > 0:
        print("\n📊 ESTATÍSTICAS DO CONTRATO:")
        stats = contract.functions.getStats().call()
        print(f"   Total viagens: {stats[0]}")
        print(f"   Total créditos: R$ {stats[1] / 1e6:.2f}")
        print(f"   Total débitos: R$ {stats[2] / 1e6:.2f}")
        print(f"   Saldo líquido: R$ {stats[3] / 1e6:.2f}")
    
    print("="*70)


def main():
    """Função principal"""
    if len(sys.argv) < 2:
        print("Uso: python3 send_trips_to_blockchain.py <trips_processed.csv>")
        print("\nExemplo:")
        print("  python3 send_trips_to_blockchain.py trips_processed.csv")
        print("\nO endereço do contrato será carregado de deployment_info.json")
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
