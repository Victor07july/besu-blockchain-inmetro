#!/usr/bin/env python3
"""
Compara resultados COM e SEM Differential Privacy
Aplica DP nas DISTÂNCIAS (não em GPS) e envia viagens duas vezes
Gera CSV com comparação focando no impacto no valor E1
"""

import json
import numpy as np
import pandas as pd
from web3 import Web3
from eth_account import Account
from datetime import datetime
import time

# Configurações
pd.set_option("display.float_format", lambda v: f"{v:.6f}")

CSV_PATH = "../../dados_monetizacao_novas_emissões_etanol_original_gas_1720_v2.csv"
CONTRACT_JSON = "../deploy_contract/e1_contract_address.json"
OUTPUT_CSV = "comparison_dp_vs_nodp.csv"

def add_laplace_noise(value, epsilon, sensitivity=1.0):
    """Adiciona ruído Laplace para Differential Privacy"""
    scale = sensitivity / epsilon
    noise = np.random.laplace(loc=0, scale=scale)
    noisy_value = value + noise
    # Garantir que distâncias não fiquem negativas
    return max(0, noisy_value)

def process_csv_data(epsilon=1.0):
    """Processa CSV e prepara dados com e sem DP"""
    print("📊 Carregando dados do CSV...")
    
    df = pd.read_csv(CSV_PATH)
    
    # Aplicar Differential Privacy nas DISTÂNCIAS
    print(f"🔐 Aplicando Differential Privacy nas distâncias (epsilon = {epsilon})...")
    
    # Sensibilidade baseada na média das distâncias
    highway_sensitivity = df['highway (distance)'].mean() * 0.1
    city_sensitivity = df['city (distance)'].mean() * 0.1
    
    df['highway_distance_dp'] = df['highway (distance)'].apply(
        lambda x: add_laplace_noise(x, epsilon, highway_sensitivity)
    )
    df['city_distance_dp'] = df['city (distance)'].apply(
        lambda x: add_laplace_noise(x, epsilon, city_sensitivity)
    )
    
    # Calcular erro médio
    error_highway = np.abs(df['highway_distance_dp'] - df['highway (distance)']).mean()
    error_city = np.abs(df['city_distance_dp'] - df['city (distance)']).mean()
    print(f"   Ruído médio rodovia: ±{error_highway:.2f} km")
    print(f"   Ruído médio cidade: ±{error_city:.2f} km")
    
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

def generate_hd_pseudonimo(index, with_dp=True):
    """Gera pseudônimo HD diferente para DP vs no-DP"""
    Account.enable_unaudited_hdwallet_features()
    mnemonic = "test test test test test test test test test test test junk"
    offset = 1000 if not with_dp else 0
    account = Account.from_mnemonic(mnemonic, account_path=f"m/44'/60'/0'/0/{index + offset}")
    return account.address

def parse_timestamp(ts_str):
    """Converte timestamp"""
    try:
        ts_str = ts_str.replace('T', ' ')
        dt = datetime.fromisoformat(ts_str)
        return int(dt.timestamp())
    except:
        return 0

def send_batch_to_blockchain(df, with_dp=True):
    """Envia lote de viagens para blockchain"""
    label = "COM DP" if with_dp else "SEM DP (Original)"
    print(f"\n{'='*60}")
    print(f"📡 Enviando viagens {label}...")
    print(f"{'='*60}\n")
    
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
            # Escolher distâncias (com ou sem DP)
            if with_dp:
                highway_distance = row["highway_distance_dp"]
                city_distance = row["city_distance_dp"]
            else:
                highway_distance = row["highway (distance)"]
                city_distance = row["city (distance)"]
            
            # Gerar pseudônimo HD
            pseudonimo = generate_hd_pseudonimo(idx, with_dp)
            
            vin = str(row["VIN"])
            timestamp = parse_timestamp(str(row["start_time"]))
            
            # Preparar TripParams (estrutura do E1Registry SEM GPS)
            trip_params = (
                vin,
                timestamp,
                int(float(highway_distance) * 1e6),
                int(float(city_distance) * 1e6),
                int(float(row["ethanol (%)"]) * 1e6),
                int(float(row["road_gasoline"]) * 1e6),
                int(float(row["road_ethanol"]) * 1e6),
                int(float(row["city_gasoline"]) * 1e6),
                int(float(row["city_ethanol"]) * 1e6),
                int(float(row["co2_etanol_original_gas_1720_flex"]) * 1e6),
                int(float(row["Real_price"]) * 1e6),
                pseudonimo
            )
            
            print(f"[{idx+1}/{len(df)}] VIN: {vin[:10]}... {label}")
            if with_dp:
                print(f"   📏 Rodovia: {highway_distance:.2f} km | Cidade: {city_distance:.2f} km")
            
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
            
            # Buscar dados calculados pelo contrato
            total_trips = contract.functions.tripCount().call()
            trip_id = total_trips - 1
            
            trip_data = contract.functions.getTrip(trip_id).call()
            
            # trip_data: [vin, timestamp, totalDistance, emissaoReal, metaCO2, diff, realPrice, valorE1, pseudonimo, pago]
            total_distance = trip_data[2] / 1e6
            meta_co2 = trip_data[4] / 1e6
            diff = trip_data[5] / 1e6
            valor_e1 = trip_data[7] / 1e6
            
            print(f"   📊 Total: {total_distance:.2f} km | 💰 E1: R$ {valor_e1:.4f}")
            
            # Calcular erro de distância
            distance_error = abs((highway_distance + city_distance) - 
                               (row["highway (distance)"] + row["city (distance)"]))
            
            results.append({
                "trip_id": trip_id,
                "vin": vin,
                "with_dp": with_dp,
                "pseudonimo": pseudonimo,
                "highway_km_original": row["highway (distance)"],
                "city_km_original": row["city (distance)"],
                "highway_km_used": highway_distance,
                "city_km_used": city_distance,
                "total_distance_original": row["highway (distance)"] + row["city (distance)"],
                "total_distance_used": highway_distance + city_distance,
                "distance_error_km": distance_error,
                "meta_co2_g": meta_co2,
                "emissao_real_g": row["co2_etanol_original_gas_1720_flex"],
                "diff_co2_g": diff,
                "valor_e1_reais": valor_e1,
                "real_price": row["Real_price"],
                "ethanol_percent": row["ethanol (%)"],
                "tx_hash": receipt.transactionHash.hex(),
                "gas_used": receipt.gasUsed
            })
            
            # Pequeno delay
            time.sleep(0.1)
            
        except Exception as e:
            print(f"   ❌ Erro: {e}")
            results.append({
                "trip_id": None,
                "vin": vin,
                "with_dp": with_dp,
                "error": str(e)
            })
    
    print(f"\n✅ {label}: {len([r for r in results if 'error' not in r])} viagens enviadas")
    return results

def main():
    """Função principal"""
    print("🚀 Iniciando comparação DP vs No-DP...\n")
    print("📋 Este script envia as mesmas viagens DUAS vezes:")
    print("   1️⃣  COM Differential Privacy nas DISTÂNCIAS (epsilon = 1.0)")
    print("   2️⃣  SEM Differential Privacy (distâncias originais)")
    print("   📊 Gera CSV com comparação resumida dos VALORES E1\n")
    
    epsilon = 1.0
    
    # Processar CSV
    df = process_csv_data(epsilon=epsilon)
    
    all_results = []
    
    # Envio 1: COM DP
    results_with_dp = send_batch_to_blockchain(df, with_dp=True)
    all_results.extend(results_with_dp)
    
    print("\n⏸️  Aguardando 3 segundos entre os lotes...")
    time.sleep(3)
    
    # Envio 2: SEM DP
    results_without_dp = send_batch_to_blockchain(df, with_dp=False)
    all_results.extend(results_without_dp)
    
    # Criar DataFrame com resultados
    print(f"\n{'='*60}")
    print("📊 Gerando CSV com comparação resumida...")
    print(f"{'='*60}\n")
    
    df_results = pd.DataFrame(all_results)
    df_success = df_results[df_results['trip_id'].notna()]
    
    if len(df_success) > 0:
        df_with_dp = df_success[df_success['with_dp'] == True]
        df_without_dp = df_success[df_success['with_dp'] == False]
        
        # Criar CSV resumido focando no E1
        summary_data = []
        
        # Linha COM DP
        summary_data.append({
            'tipo': 'COM_DP',
            'epsilon': epsilon,
            'total_viagens': len(df_with_dp),
            'valor_e1_total_reais': df_with_dp['valor_e1_reais'].sum(),
            'valor_e1_medio_reais': df_with_dp['valor_e1_reais'].mean(),
            'valor_e1_min_reais': df_with_dp['valor_e1_reais'].min(),
            'valor_e1_max_reais': df_with_dp['valor_e1_reais'].max(),
            'distancia_total_km': df_with_dp['total_distance_used'].sum(),
            'distancia_media_km': df_with_dp['total_distance_used'].mean(),
            'erro_distancia_medio_km': df_with_dp['distance_error_km'].mean(),
            'diff_co2_media_g': df_with_dp['diff_co2_g'].mean(),
            'gas_usado_total': df_with_dp['gas_used'].sum(),
            'gas_usado_medio': df_with_dp['gas_used'].mean()
        })
        
        # Linha SEM DP
        summary_data.append({
            'tipo': 'SEM_DP',
            'epsilon': 0,
            'total_viagens': len(df_without_dp),
            'valor_e1_total_reais': df_without_dp['valor_e1_reais'].sum(),
            'valor_e1_medio_reais': df_without_dp['valor_e1_reais'].mean(),
            'valor_e1_min_reais': df_without_dp['valor_e1_reais'].min(),
            'valor_e1_max_reais': df_without_dp['valor_e1_reais'].max(),
            'distancia_total_km': df_without_dp['total_distance_used'].sum(),
            'distancia_media_km': df_without_dp['total_distance_used'].mean(),
            'erro_distancia_medio_km': df_without_dp['distance_error_km'].mean(),
            'diff_co2_media_g': df_without_dp['diff_co2_g'].mean(),
            'gas_usado_total': df_without_dp['gas_used'].sum(),
            'gas_usado_medio': df_without_dp['gas_used'].mean()
        })
        
        # Linha DIFERENÇA (impacto do DP)
        summary_data.append({
            'tipo': 'DIFERENCA',
            'epsilon': epsilon,
            'total_viagens': 0,
            'valor_e1_total_reais': df_with_dp['valor_e1_reais'].sum() - df_without_dp['valor_e1_reais'].sum(),
            'valor_e1_medio_reais': df_with_dp['valor_e1_reais'].mean() - df_without_dp['valor_e1_reais'].mean(),
            'valor_e1_min_reais': df_with_dp['valor_e1_reais'].min() - df_without_dp['valor_e1_reais'].min(),
            'valor_e1_max_reais': df_with_dp['valor_e1_reais'].max() - df_without_dp['valor_e1_reais'].max(),
            'distancia_total_km': df_with_dp['total_distance_used'].sum() - df_without_dp['total_distance_used'].sum(),
            'distancia_media_km': df_with_dp['total_distance_used'].mean() - df_without_dp['total_distance_used'].mean(),
            'erro_distancia_medio_km': df_with_dp['distance_error_km'].mean(),
            'diff_co2_media_g': df_with_dp['diff_co2_g'].mean() - df_without_dp['diff_co2_g'].mean(),
            'gas_usado_total': df_with_dp['gas_used'].sum() - df_without_dp['gas_used'].sum(),
            'gas_usado_medio': df_with_dp['gas_used'].mean() - df_without_dp['gas_used'].mean()
        })
        
        df_summary = pd.DataFrame(summary_data)
        
        # Salvar CSV resumido
        df_summary.to_csv(OUTPUT_CSV, index=False)
        
        print(f"✅ CSV resumido salvo: {OUTPUT_CSV}\n")
        
        # Mostrar resumo na tela
        print(f"{'='*60}")
        print(f"📈 RESUMO DOS RESULTADOS")
        print(f"{'='*60}\n")
        
        print(f"COM DP (epsilon={epsilon}):")
        print(f"   💰 Valor E1 TOTAL: R$ {df_with_dp['valor_e1_reais'].sum():.2f}")
        print(f"   💰 Valor E1 MÉDIO: R$ {df_with_dp['valor_e1_reais'].mean():.4f}")
        print(f"   📏 Distância média: {df_with_dp['total_distance_used'].mean():.2f} km")
        print(f"   🎯 Erro distância médio: {df_with_dp['distance_error_km'].mean():.2f} km")
        
        print(f"\nSEM DP (original):")
        print(f"   💰 Valor E1 TOTAL: R$ {df_without_dp['valor_e1_reais'].sum():.2f}")
        print(f"   💰 Valor E1 MÉDIO: R$ {df_without_dp['valor_e1_reais'].mean():.4f}")
        print(f"   📏 Distância média: {df_without_dp['total_distance_used'].mean():.2f} km")
        print(f"   🎯 Erro distância médio: {df_without_dp['distance_error_km'].mean():.2f} km")
        
        print(f"\nDIFERENÇA (impacto do DP):")
        e1_diff = df_with_dp['valor_e1_reais'].sum() - df_without_dp['valor_e1_reais'].sum()
        e1_diff_pct = (e1_diff / abs(df_without_dp['valor_e1_reais'].sum())) * 100 if df_without_dp['valor_e1_reais'].sum() != 0 else 0
        print(f"   💰 Δ Valor E1 TOTAL: R$ {e1_diff:.2f} ({e1_diff_pct:+.2f}%)")
        print(f"   💰 Δ Valor E1 MÉDIO: R$ {df_with_dp['valor_e1_reais'].mean() - df_without_dp['valor_e1_reais'].mean():.4f}")
        print(f"   📏 Δ Distância: {df_with_dp['total_distance_used'].mean() - df_without_dp['total_distance_used'].mean():.2f} km")
        print(f"   🎯 Erro introduzido: {df_with_dp['distance_error_km'].mean():.2f} km")
    
    print("\n✅ Processo concluído!")
    print(f"\n💡 O CSV contém apenas 3 linhas:")
    print(f"   1. COM_DP - resultados com Differential Privacy nas distâncias")
    print(f"   2. SEM_DP - resultados sem privacidade (original)")
    print(f"   3. DIFERENCA - impacto do DP nos valores E1")

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
