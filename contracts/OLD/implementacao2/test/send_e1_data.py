#!/usr/bin/env python3
"""
Envia dados E1 (SEM GPS) para o contrato na blockchain
Implementação 2: Differential Privacy nas DISTÂNCIAS + Pseudônimos HD
"""

import json
import numpy as np
import pandas as pd
from web3 import Web3
from eth_account import Account
from datetime import datetime
import argparse

# Configurações
pd.set_option("display.float_format", lambda v: f"{v:.6f}")

CSV_PATH = "../../dados_monetizacao_novas_emissões_etanol_original_gas_1720_v2.csv"
CONTRACT_JSON = "../deploy_contract/e1_contract_address.json"
OUTPUT_JSON = "e1_send_results.json"

def add_laplace_noise(value, epsilon, sensitivity=1.0):
    """Adiciona ruído Laplace para Differential Privacy"""
    scale = sensitivity / epsilon
    noise = np.random.laplace(loc=0, scale=scale)
    noisy_value = value + noise
    # Garantir que distâncias não fiquem negativas
    return max(0, noisy_value)

def process_csv_data(apply_dp=True, epsilon=1.0):
    """Processa CSV e aplica DP às distâncias"""
    print("📊 Carregando dados do CSV...")
    
    df = pd.read_csv(CSV_PATH)
    
    if apply_dp:
        print(f"🔐 Aplicando Differential Privacy nas distâncias (epsilon = {epsilon})...")
        
        # Sensibilidade baseada na média das distâncias
        highway_sensitivity = df['highway (distance)'].mean() * 0.1
        city_sensitivity = df['city (distance)'].mean() * 0.1
        
        df['highway_distance'] = df['highway (distance)'].apply(
            lambda x: add_laplace_noise(x, epsilon, highway_sensitivity)
        )
        df['city_distance'] = df['city (distance)'].apply(
            lambda x: add_laplace_noise(x, epsilon, city_sensitivity)
        )
        
        error_highway = np.abs(df['highway_distance'] - df['highway (distance)']).mean()
        error_city = np.abs(df['city_distance'] - df['city (distance)']).mean()
        print(f"   Ruído médio rodovia: ±{error_highway:.2f} km")
        print(f"   Ruído médio cidade: ±{error_city:.2f} km")
    else:
        print("⚠️  SEM Differential Privacy - usando distâncias originais")
        df['highway_distance'] = df['highway (distance)']
        df['city_distance'] = df['city (distance)']
    
    # Dados de consumo do fabricante
    city_gasoline = [10.3, 10.3, 10.3, 10.3, 12.15, 12.15, 12.15, 12.15, 12.6, 12.6, 12.6, 12.6, 11.8, 12.83, 12.83, 12.83, 12.83, 11.6, 11.6, 11.6, 11.6, 11.6, 11.6, 11.6, 11.6, 11.6, 11.6, 11.6, 11.6, 11.6, 11.6, 12.0, 12.0]
    road_gasoline = [11.3, 11.3, 11.3, 11.3, 13.65, 13.65, 13.65, 13.65, 13.9, 13.9, 13.9, 13.9, 13.3, 14.44, 14.44, 14.44, 14.44, 14.1, 14.1, 14.1, 14.1, 14.1, 14.1, 14.1, 14.1, 14.1, 14.1, 14.1, 14.1, 14.1, 14.1, 14.4, 14.4]
    city_ethanol = [" ", " ", " ", " ", 8.2, 8.2, 8.2, 8.2, 8.9, 8.9, 8.9, 8.9, 8.1, 9.11, 9.11, 9.11, 9.11, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8.3, 8.3]
    road_ethanol = [" ", " ", " ", " ", 9.5, 9.5, 9.5, 9.5, 9.8, 9.8, 9.8, 9.8, 9.2, 10.26, 10.26, 10.26, 10.26, 9.8, 9.8, 9.8, 9.8, 9.8, 9.8, 9.8, 9.8, 9.8, 9.8, 9.8, 9.8, 9.8, 9.8, 10.0, 10.0]
    
    df["city_gasoline"] = pd.to_numeric(pd.Series(city_gasoline), errors="coerce").fillna(10.0)
    df["road_gasoline"] = pd.to_numeric(pd.Series(road_gasoline), errors="coerce").fillna(11.0)
    df["city_ethanol"] = pd.to_numeric(pd.Series(city_ethanol), errors="coerce").fillna(8.0)
    df["road_ethanol"] = pd.to_numeric(pd.Series(road_ethanol), errors="coerce").fillna(9.0)
    
    # Preços carbono europeu
    Carbon_Price_European = [67.13, 67.13, 67.69, 67.69, 67.13, 67.13, 67.13, 67.13, 80.91, 80.74, 69.88, 67.13, 68.98,
                             67.13, 67.13, 67.13, 67.13, 80.91, 80.91, 80.92, 78.64, 78.64, 78.64, 78.64, 78.64, 69.56,
                             68.69, 68.69, 67.13, 67.10, 67.69, 67.91, 65.25]
    Euro_price = [6.1708, 6.1708, 6.1447, 6.1447, 6.1708, 6.1708, 6.1708, 6.1708, 6.1031, 6.0524, 5.9424, 6.1708, 6.1315,
                  6.1708, 6.1708, 6.1708, 6.1708, 6.1031, 6.1031, 5.9710, 5.9851, 5.9851, 5.9851, 5.9851, 5.9851,
                  6.2429, 6.2070, 6.2070, 6.1708, 6.1708, 6.1447, 6.1031, 6.2200]
    
    df["Carbon_Price_European"] = pd.Series(Carbon_Price_European)
    df["Euro_price"] = pd.Series(Euro_price)
    df["Real_price"] = df["Carbon_Price_European"] * df["Euro_price"]
    
    print(f"✅ Carregadas {len(df)} viagens")
    return df

def generate_hd_pseudonimo(index):
    """Gera pseudônimo usando HD wallet"""
    Account.enable_unaudited_hdwallet_features()
    mnemonic = "test test test test test test test test test test test junk"
    account = Account.from_mnemonic(mnemonic, account_path=f"m/44'/60'/0'/0/{index}")
    return account.address

def parse_timestamp(ts_str):
    """Converte timestamp"""
    try:
        ts_str = ts_str.replace('T', ' ')
        dt = datetime.fromisoformat(ts_str)
        return int(dt.timestamp())
    except:
        return 0

def send_to_blockchain(df):
    """Envia dados para blockchain"""
    print("\n" + "="*60)
    print("📡 Enviando viagens para blockchain...")
    print("="*60 + "\n")
    
    # Carregar contrato
    with open(CONTRACT_JSON, 'r') as f:
        deployment = json.load(f)
    
    # Private key do oracle
    private_key = "0x60bbe10a196a4e71451c0f6e9ec9beab454c2a5ac0542aa5b8b733ff5719fec3"
    oracle_account = Account.from_key(private_key)
    
    # Conectar
    w3 = Web3(Web3.HTTPProvider(deployment['rpc_url']))
    
    # Adicionar middleware POA
    from web3.middleware import ExtraDataToPOAMiddleware
    w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    
    # Verificar conexão
    try:
        chain_id = w3.eth.chain_id
        print(f"✅ Conectado - Chain ID: {chain_id}")
    except Exception as e:
        raise Exception(f"Erro ao conectar: {e}")
    
    contract = w3.eth.contract(
        address=deployment['address'],
        abi=deployment['abi']
    )
    
    print(f"📍 Contrato: {deployment['address']}")
    print(f"🔮 Oracle: {oracle_account.address}\n")
    
    results = []
    
    # Enviar cada viagem
    for idx, row in df.iterrows():
        try:
            vin = str(row["VIN"])
            timestamp = parse_timestamp(str(row["start_time"]))
            pseudonimo = generate_hd_pseudonimo(idx)
            
            # Preparar TripParams
            trip_params = (
                vin,
                timestamp,
                int(float(row["highway_distance"]) * 1e6),
                int(float(row["city_distance"]) * 1e6),
                int(float(row["ethanol (%)"]) * 1e6),
                int(float(row["road_gasoline"]) * 1e6),
                int(float(row["road_ethanol"]) * 1e6),
                int(float(row["city_gasoline"]) * 1e6),
                int(float(row["city_ethanol"]) * 1e6),
                int(float(row["co2_etanol_original_gas_1720_flex"]) * 1e6),
                int(float(row["Real_price"]) * 1e6),
                pseudonimo
            )
            
            print(f"[{idx+1}/{len(df)}] VIN: {vin[:10]}... | Rodovia: {row['highway_distance']:.2f} km | Cidade: {row['city_distance']:.2f} km")
            
            # Construir e assinar transação
            txn = contract.functions.registerTrip(trip_params).build_transaction({
                'from': oracle_account.address,
                'nonce': w3.eth.get_transaction_count(oracle_account.address),
                'gas': 400000,
                'gasPrice': w3.eth.gas_price,
            })
            
            signed_txn = w3.eth.account.sign_transaction(txn, private_key)
            tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)
            
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
            
            print(f"   ✅ Gas: {receipt.gasUsed}")
            
            # Buscar dados calculados
            total_trips = contract.functions.tripCount().call()
            trip_id = total_trips - 1
            
            trip_data = contract.functions.getTrip(trip_id).call()
            valor_e1 = trip_data[7] / 1e6
            
            print(f"   💰 Valor E1: R$ {valor_e1:.4f}")
            
            results.append({
                "trip_id": trip_id,
                "vin": vin,
                "pseudonimo": pseudonimo,
                "highway_km": row["highway_distance"],
                "city_km": row["city_distance"],
                "total_distance": row["highway_distance"] + row["city_distance"],
                "valor_e1": valor_e1,
                "tx_hash": receipt.transactionHash.hex(),
                "gas_used": receipt.gasUsed,
                "block_number": receipt.blockNumber
            })
            
        except Exception as e:
            print(f"   ❌ Erro: {e}")
            results.append({
                "trip_id": None,
                "vin": vin,
                "error": str(e)
            })
    
    print(f"\n✅ {len([r for r in results if 'error' not in r])} viagens enviadas com sucesso")
    
    # Salvar resultados
    with open(OUTPUT_JSON, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"💾 Resultados salvos em {OUTPUT_JSON}")
    
    return results

def main():
    parser = argparse.ArgumentParser(description='Envia dados E1 com DP nas distâncias')
    parser.add_argument('--no-dp', action='store_true', help='Desabilita DP')
    parser.add_argument('--epsilon', type=float, default=1.0, help='Valor de epsilon para DP')
    
    args = parser.parse_args()
    
    print("🚀 Iniciando envio de dados E1...\n")
    
    # Processar dados
    df = process_csv_data(apply_dp=not args.no_dp, epsilon=args.epsilon)
    
    # Enviar para blockchain
    results = send_to_blockchain(df)
    
    # Estatísticas
    success = [r for r in results if 'error' not in r]
    if success:
        total_e1 = sum(r['valor_e1'] for r in success)
        avg_e1 = total_e1 / len(success)
        
        print(f"\n📊 ESTATÍSTICAS:")
        print(f"   Total de viagens: {len(success)}")
        print(f"   Valor E1 total: R$ {total_e1:.2f}")
        print(f"   Valor E1 médio: R$ {avg_e1:.4f}")
        print(f"   DP ativo: {'Não' if args.no_dp else f'Sim (epsilon={args.epsilon})'}")
    
    print("\n✅ Processo concluído!")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Processo interrompido pelo usuário")
        exit(1)
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
