#!/usr/bin/env python3
"""
Script para verificar saldos de todas as contas
"""
import json
from web3 import Web3

# Carregar configuração
with open("keys.json") as f:
    keys = json.load(f)

# Conectar ao nó
rpc_url = keys['besu']['rpcnode']['url']
w3 = Web3(Web3.HTTPProvider(rpc_url))

print(f"Conectado a: {rpc_url}")
print(f"Status: {w3.is_connected()}")
print()

# Verificar saldo de todas as contas
accounts_to_check = []

# Contas do Besu
for node_name, node_data in keys['besu'].items():
    if 'accountAddress' in node_data:
        # accountAddress no keys.json já pode ter o 0x ou não
        addr = node_data['accountAddress']
        if not addr.startswith('0x'):
            addr = '0x' + addr
        address = w3.to_checksum_address(addr)
        accounts_to_check.append((node_name, address, node_data.get('accountPrivateKey', 'N/A')))

# Contas adicionais
for account_name, account_data in keys['accounts'].items():
    address = w3.to_checksum_address(account_data['address'])
    accounts_to_check.append((f"account_{account_name}", address, account_data['privateKey']))

print("=== SALDOS DAS CONTAS ===")
for name, address, private_key in accounts_to_check:
    try:
        balance = w3.eth.get_balance(address)
        balance_eth = w3.from_wei(balance, 'ether')
        print(f"{name:12}: {address} | {balance:15} wei | {balance_eth:10} ETH")
        
        if balance > 0:
            print(f"    ↳ Chave privada: {private_key}")
            
    except Exception as e:
        print(f"{name:12}: {address} | ERRO: {e}")

print()
print("=== INFORMAÇÕES DA REDE ===")
try:
    print(f"Número do bloco atual: {w3.eth.block_number}")
    print(f"Chain ID: {w3.eth.chain_id}")
    print(f"Gas price: {w3.eth.gas_price}")
except Exception as e:
    print(f"Erro ao obter informações da rede: {e}")
