#!/usr/bin/env python3
"""
Script para enviar viagens SUMO processadas para o contrato E1RegistryEuclidean

Lê o CSV processado e submete transações para a blockchain.

Autor: Victor  
Data: 2026-03-03
"""

import pandas as pd
import json
import sys
import time
from web3 import Web3
from web3.middleware import geth_poa_middleware
from eth_account import Account

# ==================== CONFIGURAÇÕES ====================
RPC_URL = "http://localhost:8545"
CHAIN_ID = 1337
GAS_LIMIT = 500000
GAS_PRICE_GWEI = 0  # 0 para rede de desenvolvimento

# Arquivo com deployment info
DEPLOYMENT_FILE = "../deployment_info.json"
# =======================================================


def load_deployment_info(deployment_file: str) -> dict:
    """Carrega informações do deployment"""
    with open(deployment_file, 'r') as f:
        return json.load(f)


def coords_to_int256(coord: float) -> int:
    """
    Converte coordenada float para int256 (× 1e6)
    
    Args:
        coord: Coordenada em graus decimais
        
    Returns:
        Coordenada como int256
    """
    return int(coord * 1_000_000)


def value_to_uint256(value: float, decimals: int = 6) -> int:
    """
    Converte valor float para uint256
    
    Args:
        value: Valor float
        decimals: Casas decimais (padrão: 6)
        
    Returns:
        Valor como uint256
    """
    return int(value * (10 ** decimals))


def send_trips_to_blockchain(
    csv_file: str,
    deployment_file: str,
    private_key: str,
    delay: float = 0.5
):
    """
    Envia viagens para a blockchain
    
    Args:
        csv_file: Arquivo CSV processado
        deployment_file: Arquivo JSON com deployment info
        private_key: Chave privada da conta oracle
        delay: Delay entre transações (segundos)
    """
    print("="*70)
    print("📤 ENVIO DE VIAGENS SUMO → BLOCKCHAIN")
    print("="*70)
    
    # Conectar ao nó
    print(f"\n🔗 Conectando a {RPC_URL}...")
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    w3.middleware_onion.inject(geth_poa_middleware, layer=0)
    
    if not w3.is_connected():
        print("❌ Erro: Não foi possível conectar ao nó")
        sys.exit(1)
    
    print(f"   ✅ Conectado! Block: {w3.eth.block_number}")
    
    # Carregar deployment info
    print(f"\n📋 Carregando deployment info de {deployment_file}...")
    deployment_info = load_deployment_info(deployment_file)
    contract_address = deployment_info['contract_address']
    abi = deployment_info['abi']
    
    print(f"   Contrato: {contract_address}")
    
    # Instanciar contrato
    contract = w3.eth.contract(address=contract_address, abi=abi)
    
    # Configurar conta
    account = Account.from_key(private_key)
    print(f"   Oracle: {account.address}")
    
    # Verificar se é oracle
    oracle_address = contract.functions.oracle().call()
    if account.address.lower() != oracle_address.lower():
        print(f"⚠️  Aviso: Conta {account.address} não é oracle ({oracle_address})")
        print("   Continuando mesmo assim...")
    
    # Ler CSV
    print(f"\n📊 Carregando viagens de {csv_file}...")
    df = pd.read_csv(csv_file)
    print(f"   Viagens encontradas: {len(df)}")
    
    # Enviar viagens
    print("\n🚀 Enviando transações...")
    print("="*70)
    
    success_count = 0
    error_count = 0
    
    for idx, row in df.iterrows():
        print(f"\n[{idx+1}/{len(df)}] Viagem: {row['vin']}")
        print(f"   📏 Distância: {row['total_distance_km']:.3f} km")
        print(f"   🏭 CO2 real: {row['co2_real_g']:.1f} g")
        print(f"   💰 Valor E1: R$ {row['valor_e1_reais']:+.4f}")
        
        try:
            # Preparar dados para TripData struct
            trip_data = (
                row['vin'],                                           # string vin
                int(row['timestamp']),                                # uint256 timestamp
                value_to_uint256(row['total_distance_km'], 6),       # uint256 totalDistance (km × 1e6)
                value_to_uint256(row['fuel_consumed_liters'], 6),    # uint256 fuelConsumed (l × 1e6)
                value_to_uint256(row['co2_real_g'] / 1000, 6),       # uint256 co2Real (kg × 1e6)
                value_to_uint256(row['co2_meta_g'] / 1000, 6),       # uint256 co2Meta (kg × 1e6)
                value_to_uint256(row['valor_e1_reais'], 6),          # int256 valorE1 (R$ × 1e6)
                0,                                                     # uint256 avgEthanolPercent (gasolina pura)
                (                                                      # GPSLocation startLocation
                    coords_to_int256(row['start_lat_private']),
                    coords_to_int256(row['start_lon_private'])
                ),
                (                                                      # GPSLocation endLocation
                    coords_to_int256(row['end_lat_private']),
                    coords_to_int256(row['end_lon_private'])
                ),
                row['pseudonimo'],                                    # address pseudonimo
                False                                                  # bool pago
            )
            
            # Construir transação
            nonce = w3.eth.get_transaction_count(account.address)
            
            txn = contract.functions.registerTrip(trip_data).build_transaction({
                'from': account.address,
                'nonce': nonce,
                'gas': GAS_LIMIT,
                'gasPrice': w3.to_wei(GAS_PRICE_GWEI, 'gwei'),
                'chainId': CHAIN_ID
            })
            
            # Assinar
            signed_txn = w3.eth.account.sign_transaction(txn, private_key)
            
            # Enviar
            tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            print(f"   📤 TX enviada: {tx_hash.hex()}")
            
            # Aguardar confirmação
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=30)
            
            if receipt['status'] == 1:
                print(f"   ✅ Confirmada no block {receipt['blockNumber']}")
                print(f"   ⛽ Gas usado: {receipt['gasUsed']:,}")
                success_count += 1
            else:
                print(f"   ❌ Transação revertida")
                error_count += 1
            
            # Delay entre transações
            if idx < len(df) - 1:
                time.sleep(delay)
        
        except Exception as e:
            print(f"   ❌ Erro: {e}")
            error_count += 1
            continue
    
    # Resumo final
    print("\n" + "="*70)
    print("📊 RESUMO DO ENVIO")
    print("="*70)
    print(f"✅ Sucesso: {success_count}")
    print(f"❌ Erros: {error_count}")
    print(f"📈 Taxa de sucesso: {(success_count/len(df)*100):.1f}%")
    print("="*70)
    
    # Verificar estatísticas on-chain
    print("\n📊 Estatísticas do contrato:")
    try:
        stats = contract.functions.getStats().call()
        print(f"   Total de viagens: {stats[0]}")
        print(f"   Total créditos: R$ {stats[1] / 1e6:.2f}")
        print(f"   Total débitos: R$ {stats[2] / 1e6:.2f}")
        print(f"   Saldo líquido: R$ {stats[3] / 1e6:+.2f}")
    except Exception as e:
        print(f"   ⚠️  Não foi possível buscar estatísticas: {e}")


def main():
    """Função principal"""
    if len(sys.argv) < 3:
        print("Uso: python3 send_sumo_to_blockchain.py <trips.csv> <private_key> [deployment_file] [delay]")
        print("\nParâmetros:")
        print("  trips.csv        : CSV processado com viagens")
        print("  private_key      : Chave privada da conta oracle (0x...)")
        print("  deployment_file  : JSON com deployment info (padrão: ../deployment_info.json)")
        print("  delay            : Segundos entre transações (padrão: 0.5)")
        print("\nExemplo:")
        print("  python3 send_sumo_to_blockchain.py trips_sumo_processed.csv 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    private_key = sys.argv[2]
    deployment_file = sys.argv[3] if len(sys.argv) > 3 else DEPLOYMENT_FILE
    delay = float(sys.argv[4]) if len(sys.argv) > 4 else 0.5
    
    send_trips_to_blockchain(csv_file, deployment_file, private_key, delay)


if __name__ == "__main__":
    main()
