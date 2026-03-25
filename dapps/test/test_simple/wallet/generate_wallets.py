#!/usr/bin/env python3
"""
Script para gerar carteiras Ethereum e adicionar ao JSON de wallets.
Uso: python3 generate_wallets.py [quantidade] [arquivo_json]
"""

import json
import sys
from eth_account import Account

def generate_wallets(num_wallets, start_index=1):
    """Gera num_wallets carteiras Ethereum."""
    wallets = {}
    
    print(f"🔑 Gerando {num_wallets} carteiras Ethereum...")
    
    for i in range(start_index, start_index + num_wallets):
        # Gerar conta aleatória
        account = Account.create()
        
        wallet_key = f"vehicle_group_{i}"
        wallets[wallet_key] = {
            "address": account.address,
            "private_key": account.key.hex()
        }
        
        if i % 100 == 0:
            print(f"   ✓ Geradas {i - start_index + 1}/{num_wallets} carteiras...")
    
    print(f"✅ {num_wallets} carteiras geradas com sucesso!\n")
    return wallets

def load_existing_wallets(filename):
    """Carrega wallets existentes do arquivo JSON."""
    try:
        with open(filename, 'r') as f:
            wallets = json.load(f)
        print(f"📂 Arquivo existente encontrado: {len(wallets)} carteiras")
        return wallets
    except FileNotFoundError:
        print(f"📂 Arquivo {filename} não encontrado. Criando novo...")
        return {}

def save_wallets(wallets, filename):
    """Salva wallets no arquivo JSON."""
    with open(filename, 'w') as f:
        json.dump(wallets, f, indent=2)
    print(f"💾 Arquivo salvo: {filename}")
    print(f"📊 Total de carteiras: {len(wallets)}")

def main():
    # Parâmetros
    if len(sys.argv) < 2:
        print("Uso: python3 generate_wallets.py [quantidade] [arquivo_json]")
        print("\nExemplos:")
        print("  python3 generate_wallets.py 64                              # Gera 64 novas carteiras")
        print("  python3 generate_wallets.py 1024 wallets_1024_groups.json  # Gera 1024 em arquivo específico")
        sys.exit(1)
    
    num_wallets = int(sys.argv[1])
    filename = sys.argv[2] if len(sys.argv) > 2 else "wallets_64_groups.json"
    
    print("="*70)
    print("🚀 GERADOR DE CARTEIRAS ETHEREUM")
    print("="*70)
    print(f"📝 Quantidade solicitada: {num_wallets}")
    print(f"📁 Arquivo de destino: {filename}")
    print("="*70)
    print()
    
    # Carregar wallets existentes (se houver)
    existing_wallets = load_existing_wallets(filename)
    existing_count = len(existing_wallets)
    
    # Determinar índice inicial
    if existing_count > 0:
        # Encontrar o maior índice existente
        max_index = 0
        for key in existing_wallets.keys():
            if key.startswith("vehicle_group_"):
                index = int(key.split("_")[-1])
                max_index = max(max_index, index)
        
        start_index = max_index + 1
        print(f"🔢 Última carteira existente: vehicle_group_{max_index}")
        print(f"🔢 Próxima carteira será: vehicle_group_{start_index}\n")
    else:
        start_index = 1
    
    # Gerar novas carteiras
    new_wallets = generate_wallets(num_wallets, start_index)
    
    # Combinar com existentes
    all_wallets = {**existing_wallets, **new_wallets}
    
    # Salvar
    save_wallets(all_wallets, filename)
    
    print("\n" + "="*70)
    print("✅ CONCLUÍDO!")
    print("="*70)
    print(f"📊 Resumo:")
    print(f"   • Carteiras existentes: {existing_count}")
    print(f"   • Novas carteiras: {num_wallets}")
    print(f"   • Total no arquivo: {len(all_wallets)}")
    print("="*70)

if __name__ == "__main__":
    main()
