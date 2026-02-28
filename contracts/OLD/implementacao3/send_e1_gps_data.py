#!/usr/bin/env python3
"""
Envia dados E1 com coordenadas GPS (com DP aplicado) para o contrato na blockchain
Implementação 2: GPS + Differential Privacy + Pseudônimos HD
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
CONTRACT_JSON = "../deploy_contract/e1_gps_contract_address.json"
OUTPUT_JSON = "e1_gps_send_results.json"

def parse_location(location_str):
    """Parseia string de localização"""
    try:
        parts = location_str.strip().split(',')
        lat = float(parts[0].strip())
        lon = float(parts[1].strip())
        return lat, lon
    except:
        return None, None

def add_laplace_noise(value, epsilon, sensitivity=1.0):
    """Adiciona ruído Laplace para Differential Privacy"""
    scale = sensitivity / epsilon
    noise = np.random.laplace(loc=0, scale=scale)
    return value + noise

def process_csv_data(apply_dp=True, epsilon=1.0):
    """Processa CSV e aplica DP às coordenadas"""
    print("📊 Carregando dados do CSV...")
    
    df = pd.read_csv(CSV_PATH)
    
    # Parsear coordenadas GPS
    print("🗺️  Parseando coordenadas GPS...")
    start_coords = df['start_location'].apply(parse_location)
    end_coords = df['end_location'].apply(parse_location)
    
    df['start_lat'] = [coord[0] for coord in start_coords]
    df['start_lon'] = [coord[1] for coord in start_coords]
    df['end_lat'] = [coord[0] for coord in end_coords]
    df['end_lon'] = [coord[1] for coord in end_coords]
    
    # Remover linhas com coordenadas inválidas
    df = df.dropna(subset=['start_lat', 'start_lon', 'end_lat', 'end_lon'])
    
    # Aplicar Differential Privacy
    if apply_dp:
        print(f"🔐 Aplicando Differential Privacy (epsilon = {epsilon})...")
        df['start_lat_dp'] = df['start_lat'].apply(lambda x: add_laplace_noise(x, epsilon))
        df['start_lon_dp'] = df['start_lon'].apply(lambda x: add_laplace_noise(x, epsilon))
        df['end_lat_dp'] = df['end_lat'].apply(lambda x: add_laplace_noise(x, epsilon))
        df['end_lon_dp'] = df['end_lon'].apply(lambda x: add_laplace_noise(x, epsilon))
        
        # Calcular erro médio
        error_lat = np.abs(df['start_lat_dp'] - df['start_lat']).mean()
        error_meters = error_lat * 111000
        print(f"   Ruído médio: ±{error_meters:.0f} metros")
    else:
        print("⚠️  Sem Differential Privacy (coordenadas originais)")
        df['start_lat_dp'] = df['start_lat']
        df['start_lon_dp'] = df['start_lon']
        df['end_lat_dp'] = df['end_lat']
        df['end_lon_dp'] = df['end_lon']
    
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
    
    print(f"✅ Carregadas {len(df)} viagens com GPS")
    return df

def generate_hd_pseudonimo(index):
    """Gera pseudônimo HD"""
    Account.enable_unaudited_hdwallet_features()
    mnemonic = "test test test test test test test test test test test junk"
    account = Account.from_mnemonic(mnemonic, account_path=f"m/44'/60'/0'/0/{index}")
    return account.address

def parse_timestamp(ts_str):
    """Converte timestamp"""
    try:
        # Remover 'T' se existir
        ts_str = ts_str.replace('T', ' ')
        dt = datetime.fromisoformat(ts_str)
        return int(dt.timestamp())
    except:
        return 0

def send_to_blockchain(df):
    """Envia dados com GPS para blockchain"""
    print("\n📡 Enviando dados para blockchain...\n")
    
    # Carregar contrato
    with open(CONTRACT_JSON, 'r') as f:
        deployment = json.load(f)
    
    # Private key do oracle
    private_key = "0x60bbe10a196a4e71451c0f6e9ec9beab454c2a5ac0542aa5b8b733ff5719fec3"
    oracle_account = Account.from_key(private_key)
    
    # Conectar
    w3 = Web3(Web3.HTTPProvider(deployment['rpc_url']))
    
    # Adicionar middleware POA (necessário antes de qualquer chamada)
    from web3.middleware import ExtraDataToPOAMiddleware
    w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    
    # Verificar conexão usando métodos eth_* (não requerem autenticação adicional)
    try:
        chain_id = w3.eth.chain_id
        block_number = w3.eth.block_number
        print(f"✅ Conectado ao Besu: {deployment['rpc_url']}")
        print(f"   Chain ID: {chain_id} | Block: {block_number}")
    except Exception as e:
        print(f"❌ Erro ao conectar: {e}")
        raise Exception(f"Não foi possível conectar ao Besu em {deployment['rpc_url']}")
    
    contract = w3.eth.contract(
        address=deployment['address'],
        abi=deployment['abi']
    )
    
    print(f"📍 Contrato: {deployment['address']}")
    print(f"🔮 Oracle: {oracle_account.address}\n")
    
    results = {
        "success": [],
        "failed": [],
        "pseudonimos": {},
        "epsilon_used": "inline",
        "gps_privacy": "Differential Privacy applied"
    }
    
    # Enviar cada viagem
    for idx, row in df.iterrows():
        try:
            # Gerar pseudônimo HD
            pseudonimo = generate_hd_pseudonimo(idx)
            
            vin = str(row["VIN"])
            timestamp = parse_timestamp(str(row["start_time"]))
            
            # Preparar GPS Location (× 1e6 para precisão)
            start_location = (
                int(row["start_lat_dp"] * 1e6),
                int(row["start_lon_dp"] * 1e6)
            )
            
            end_location = (
                int(row["end_lat_dp"] * 1e6),
                int(row["end_lon_dp"] * 1e6)
            )
            
            # Preparar TripGPSParams
            trip_params = (
                vin,
                timestamp,
                int(float(row["highway (distance)"]) * 1e6),
                int(float(row["city (distance)"]) * 1e6),
                int(float(row["ethanol (%)"]) * 1e6),
                int(float(row["road_gasoline"]) * 1e6),
                int(float(row["road_ethanol"]) * 1e6),
                int(float(row["city_gasoline"]) * 1e6),
                int(float(row["city_ethanol"]) * 1e6),
                int(float(row["co2_etanol_original_gas_1720_flex"]) * 1e6),
                int(float(row["Real_price"]) * 1e6),
                pseudonimo,
                start_location,
                end_location
            )
            
            print(f"[{idx+1}/{len(df)}] VIN: {vin[:10]}...")
            print(f"   Pseudônimo: {pseudonimo}")
            print(f"   GPS Start (DP): ({row['start_lat_dp']:.6f}, {row['start_lon_dp']:.6f})")
            print(f"   GPS End (DP):   ({row['end_lat_dp']:.6f}, {row['end_lon_dp']:.6f})")
            print(f"   Highway: {row['highway (distance)']:.2f} km, City: {row['city (distance)']:.2f} km")
            
            # Construir e assinar transação
            txn = contract.functions.registerTrip(trip_params).build_transaction({
                'from': oracle_account.address,
                'nonce': w3.eth.get_transaction_count(oracle_account.address),
                'gas': 600000,
                'gasPrice': w3.eth.gas_price,
            })
            
            signed_txn = w3.eth.account.sign_transaction(txn, private_key)
            tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)
            
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
            
            print(f"   ✅ TxHash: {receipt.transactionHash.hex()[:20]}...")
            print(f"   Gas: {receipt.gasUsed}")
            
            # Buscar dados calculados pelo contrato
            trip_data = contract.functions.getTrip(idx).call()
            
            # trip_data: [vin, timestamp, totalDistance, emissaoReal, metaCO2, diff, realPrice, valorE1, pseudonimo, pago, startLocation, endLocation, gpsDistance]
            meta_co2 = trip_data[4] / 1e6
            diff = trip_data[5] / 1e6
            valor_e1 = trip_data[7] / 1e6
            gps_distance = trip_data[12] / 1e6
            
            print(f"   📊 CALCULADO PELO CONTRATO:")
            print(f"      Meta CO2: {meta_co2:.2f} g")
            print(f"      Diferença: {diff:.2f} g")
            print(f"      💰 Valor E1: R$ {valor_e1:.4f}")
            print(f"      📏 Distância GPS: {gps_distance:.2f} km\n")
            
            results["success"].append({
                "tripId": idx,
                "vin": vin,
                "txHash": receipt.transactionHash.hex(),
                "pseudonimo": pseudonimo,
                "gps_start_dp": f"({row['start_lat_dp']:.6f}, {row['start_lon_dp']:.6f})",
                "gps_end_dp": f"({row['end_lat_dp']:.6f}, {row['end_lon_dp']:.6f})",
                "gps_start_original": f"({row['start_lat']:.6f}, {row['start_lon']:.6f})",
                "gps_end_original": f"({row['end_lat']:.6f}, {row['end_lon']:.6f})",
                "metaCO2_calculated": meta_co2,
                "diff_calculated": diff,
                "valorE1_calculated": valor_e1,
                "gpsDistance_calculated": gps_distance
            })
            
            if vin not in results["pseudonimos"]:
                results["pseudonimos"][vin] = []
            
            results["pseudonimos"][vin].append({
                "tripId": idx,
                "pseudonimo": pseudonimo,
                "hdPath": f"m/44'/60'/0'/0/{idx}"
            })
            
        except Exception as e:
            print(f"   ❌ Erro: {e}\n")
            results["failed"].append({
                "tripId": idx,
                "vin": str(row["VIN"]),
                "error": str(e)
            })
    
    # Estatísticas
    print("\n" + "="*60)
    print("📊 RESUMO")
    print("="*60)
    print(f"✅ Sucesso: {len(results['success'])}")
    print(f"❌ Falhas: {len(results['failed'])}")
    
    # Consultar contrato
    if len(results['success']) > 0:
        stats = contract.functions.getStats().call()
        print(f"\n📈 ESTATÍSTICAS DO CONTRATO:")
        print(f"   Total viagens: {stats[0]}")
        print(f"   Total pago: R$ {stats[1] / 1e6:.2f}")
        print(f"   Média: R$ {stats[2] / 1e6:.4f}")
    
    # Salvar resultados
    with open(OUTPUT_JSON, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n📁 Resultados salvos em: {OUTPUT_JSON}")

def main():
    """Função principal"""
    parser = argparse.ArgumentParser(description='Envia dados E1 com GPS e DP para blockchain')
    parser.add_argument('--epsilon', type=float, default=1.0,
                        help='Parâmetro epsilon para Differential Privacy (default: 1.0)')
    parser.add_argument('--no-dp', action='store_true',
                        help='Não aplicar DP (usar coordenadas originais)')
    
    args = parser.parse_args()
    
    print("🚀 Iniciando envio de dados E1 + GPS + DP...\n")
    print("⚙️  Implementação 2: Proof-of-concept para pesquisa\n")
    
    if args.no_dp:
        print("⚠️  ATENÇÃO: DP desabilitado - coordenadas ORIGINAIS serão enviadas\n")
    
    # Processar CSV
    df = process_csv_data(apply_dp=not args.no_dp, epsilon=args.epsilon)
    
    # Enviar para blockchain
    send_to_blockchain(df)
    
    print("\n✅ Processo concluído!")
    print("\n💡 Para analisar privacidade:")
    print("   - Compare coordenadas originais vs DP nos resultados")
    print("   - Teste diferentes valores de epsilon (0.1, 1.0, 10.0)")
    print("   - Analise o trade-off entre privacidade e utilidade")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
