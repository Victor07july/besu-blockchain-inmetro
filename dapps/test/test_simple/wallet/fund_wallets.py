#!/usr/bin/env python3
"""
Script para transferir fundos (ETH) para carteiras criadas.
Usa uma carteira master do genesis para distribuir fundos.
"""

import json
import sys
import asyncio
from web3 import AsyncWeb3
from web3.middleware import ExtraDataToPOAMiddleware
from eth_account import Account

# Configurações
RPC_URL = "https://ec2-18-218-85-118.us-east-2.compute.amazonaws.com/user/"
CHAIN_ID = 1337

# Carteira do genesis com fundos (do QBFTgenesis.json)
MASTER_ADDRESS = "0xfe3b557e8fb62b89f4916b721be55ceb828dbd73"
MASTER_PRIVATE_KEY = "0x8f2a55949038a9610f50fb23b5883af3b4ecb3c3bb792cbcefbd1542c692be63"

# Quantidade a transferir para cada carteira (em Wei)
# 100 ETH por carteira = 100 * 10^18 wei
AMOUNT_PER_WALLET = 100_000_000_000_000_000_000  # 100 ETH

async def fund_wallets(wallets_file, start_index=None, end_index=None):
    """Transfere fundos para as carteiras do arquivo JSON."""
    
    # Carregar wallets
    with open(wallets_file, 'r') as f:
        wallets = json.load(f)
    
    print(f"📂 Carregadas {len(wallets)} carteiras de {wallets_file}")
    
    # Filtrar range se especificado
    wallet_items = list(wallets.items())
    if start_index is not None:
        wallet_items = [(k, v) for k, v in wallet_items if int(k.split('_')[-1]) >= start_index]
    if end_index is not None:
        wallet_items = [(k, v) for k, v in wallet_items if int(k.split('_')[-1]) <= end_index]
    
    print(f"🎯 Transferindo fundos para {len(wallet_items)} carteiras...")
    print(f"💰 Valor por carteira: {AMOUNT_PER_WALLET / 1e18} ETH")
    print()
    
    # Conectar ao Besu
    w3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(RPC_URL))
    w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    
    if not await w3.is_connected():
        print("❌ Erro ao conectar ao Besu!")
        return
    
    print(f"✅ Conectado ao Besu (Chain ID: {await w3.eth.chain_id})")
    
    # Verificar saldo da carteira master
    master_balance = await w3.eth.get_balance(MASTER_ADDRESS)
    print(f"💼 Saldo Master: {master_balance / 1e18:.2f} ETH")
    
    total_needed = AMOUNT_PER_WALLET * len(wallet_items)
    print(f"📊 Total necessário: {total_needed / 1e18:.2f} ETH")
    
    if master_balance < total_needed:
        print(f"⚠️  AVISO: Saldo insuficiente! Faltam {(total_needed - master_balance) / 1e18:.2f} ETH")
        response = input("Continuar mesmo assim? (s/n): ")
        if response.lower() != 's':
            return
    
    print()
    print("🚀 Iniciando transferências...")
    print("="*70)
    
    # Obter nonce inicial
    nonce = await w3.eth.get_transaction_count(MASTER_ADDRESS)
    
    master_account = Account.from_key(MASTER_PRIVATE_KEY)
    
    success_count = 0
    fail_count = 0
    
    for idx, (key, wallet) in enumerate(wallet_items, 1):
        try:
            to_address = wallet['address']
            
            # Criar transação
            tx = {
                'nonce': nonce,
                'to': to_address,
                'value': AMOUNT_PER_WALLET,
                'gas': 21000,
                'gasPrice': 0,  # zeroBaseFee
                'chainId': CHAIN_ID
            }
            
            # Assinar transação
            signed_tx = master_account.sign_transaction(tx)
            
            # Enviar transação
            tx_hash = await w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            
            print(f"[{idx}/{len(wallet_items)}] ✅ {key}: {to_address[:10]}... | TX: {tx_hash.hex()[:10]}...")
            
            nonce += 1
            success_count += 1
            
            # Pequeno delay a cada 50 transações
            if idx % 50 == 0:
                await asyncio.sleep(1)
                
        except Exception as e:
            print(f"[{idx}/{len(wallet_items)}] ❌ {key}: ERRO - {e}")
            fail_count += 1
    
    print("="*70)
    print(f"\n✅ Concluído!")
    print(f"   • Sucessos: {success_count}")
    print(f"   • Falhas: {fail_count}")
    print(f"   • Total transferido: {(success_count * AMOUNT_PER_WALLET) / 1e18:.2f} ETH")

def main():
    if len(sys.argv) < 2:
        print("Uso: python3 fund_wallets.py <arquivo_json> [start_index] [end_index]")
        print("\nExemplos:")
        print("  python3 fund_wallets.py wallets_1024_groups.json")
        print("  python3 fund_wallets.py wallets_1024_groups.json 65 128")
        sys.exit(1)
    
    wallets_file = sys.argv[1]
    start_index = int(sys.argv[2]) if len(sys.argv) > 2 else None
    end_index = int(sys.argv[3]) if len(sys.argv) > 3 else None
    
    print("="*70)
    print("💸 DISTRIBUIDOR DE FUNDOS PARA CARTEIRAS")
    print("="*70)
    print()
    
    asyncio.run(fund_wallets(wallets_file, start_index, end_index))

if __name__ == "__main__":
    main()
