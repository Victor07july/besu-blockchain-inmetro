#!/usr/bin/env python3
"""
Processa dados E1 do CSV e envia para o contrato na blockchain
Contrato calcula E1 internamente (similar ao CarbonCreditNFT_E1)
"""

import json
import numpy as np
import pandas as pd
from web3 import Web3
from eth_account import Account
from datetime import datetime

# Configurações
pd.set_option("display.float_format", lambda v: f"{v:.6f}")

CSV_PATH = "../dados_monetizacao_novas_emissões_etanol_original_gas_1720_v2.csv"
CONTRACT_JSON = "e1_contract_address.json"
OUTPUT_JSON = "e1_send_results.json"

def process_csv_data():
    """Processa CSV básico - só prepara dados brutos"""
    print("📊 Carregando dados do CSV...")
    
    df = pd.read_csv(CSV_PATH)
    
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
    """Gera pseudônimo HD"""
    Account.enable_unaudited_hdwallet_features()
    mnemonic = "test test test test test test test test test test test junk"
    account = Account.from_mnemonic(mnemonic, account_path=f"m/44'/60'/0'/0/{index}")
    return account.address

def parse_timestamp(ts_str):
    """Converte timestamp"""
    try:
        dt = datetime.fromisoformat(ts_str.replace('T', ' '))
        return int(dt.timestamp())
    except:
        return 0

def send_to_blockchain(df):
    """Envia dados brutos - contrato calcula E1"""
    print("\n📡 Enviando dados para blockchain...")
    
    # Carregar contrato
    with open(CONTRACT_JSON, 'r') as f:
        deployment = json.load(f)
    
    # Private key do oracle
    private_key = "0x60bbe10a196a4e71451c0f6e9ec9beab454c2a5ac0542aa5b8b733ff5719fec3"
    oracle_account = Account.from_key(private_key)
    
    # Conectar
    w3 = Web3(Web3.HTTPProvider(deployment['rpc_url']))
    
    # Adicionar middleware POA para Besu/QBFT
    from web3.middleware import ExtraDataToPOAMiddleware
    w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    
    if not w3.is_connected():
        raise Exception("Não conectado ao Besu")
    
    contract = w3.eth.contract(
        address=deployment['address'],
        abi=deployment['abi']
    )
    
    print(f"📍 Contrato: {deployment['address']}")
    print(f"🔮 Oracle: {oracle_account.address}\n")
    
    results = {
        "success": [],
        "failed": [],
        "pseudonimos": {}
    }
    
    # Enviar cada viagem
    for idx, row in df.iterrows():
        try:
            # Gerar pseudônimo HD
            pseudonimo = generate_hd_pseudonimo(idx)
            
            vin = str(row["VIN"])
            timestamp = parse_timestamp(str(row["start_time"]))
            
            # Preparar TripParams (× 1e6 para precisão)
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
                pseudonimo
            )
            
            print(f"[{idx+1}/{len(df)}] VIN: {vin[:10]}...")
            print(f"   Pseudônimo: {pseudonimo}")
            print(f"   Highway: {row['highway (distance)']:.2f} km, City: {row['city (distance)']:.2f} km")
            print(f"   Contrato calculará E1 internamente...")
            
            # Construir e assinar transação
            txn = contract.functions.registerTrip(trip_params).build_transaction({
                'from': oracle_account.address,
                'nonce': w3.eth.get_transaction_count(oracle_account.address),
                'gas': 500000,
                'gasPrice': w3.eth.gas_price,
            })
            
            signed_txn = w3.eth.account.sign_transaction(txn, private_key)
            tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)
            
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
            
            print(f"   ✅ TxHash: {receipt.transactionHash.hex()[:20]}...")
            print(f"   Gas: {receipt.gasUsed}")
            
            # Buscar dados calculados pelo contrato
            trip_data = contract.functions.getTrip(idx).call()
            
            # trip_data: [vin, timestamp, totalDistance, emissaoReal, metaCO2, diff, realPrice, valorE1, pseudonimo, pago]
            meta_co2 = trip_data[4] / 1e6
            diff = trip_data[5] / 1e6
            valor_e1 = trip_data[7] / 1e6
            
            print(f"   📊 VALORES CALCULADOS PELO CONTRATO:")
            print(f"      Meta CO2: {meta_co2:.2f} g")
            print(f"      Diferença: {diff:.2f} g")
            print(f"      💰 Valor E1: R$ {valor_e1:.4f}\n")
            
            results["success"].append({
                "tripId": idx,
                "vin": vin,
                "txHash": receipt.transactionHash.hex(),
                "pseudonimo": pseudonimo,
                "metaCO2_calculated": meta_co2,
                "diff_calculated": diff,
                "valorE1_calculated": valor_e1
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
    print("🚀 Iniciando envio de dados E1...\n")
    print("⚙️  Contrato calculará Meta_CO2, Diff e e1 internamente\n")
    
    # Processar CSV
    df = process_csv_data()
    
    # Enviar para blockchain
    send_to_blockchain(df)
    
    print("\n✅ Processo concluído!")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
