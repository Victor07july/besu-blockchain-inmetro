#!/usr/bin/env python3
"""
Deploy do contrato E1Registry (SEM GPS)
Para uso com Differential Privacy nas distâncias
"""

import json
from web3 import Web3
from solcx import compile_source, install_solc
from eth_account import Account

# Instalar versão específica do Solidity
print("📦 Instalando Solidity 0.8.0...")
install_solc('0.8.0')

# Conectar ao nó Besu
RPC_URL = "http://localhost:8545"
w3 = Web3(Web3.HTTPProvider(RPC_URL))

# Adicionar middleware POA ANTES de qualquer verificação
from web3.middleware import ExtraDataToPOAMiddleware
w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

# Verificar conexão
try:
    chain_id = w3.eth.chain_id
    block_number = w3.eth.block_number
    print(f"✅ Conectado ao nó Besu")
    print(f"   Chain ID: {chain_id}")
    print(f"   Block: {block_number}")
except Exception as e:
    raise Exception(f"❌ Não foi possível conectar ao nó Besu: {e}")

# Conta do deployer (oracle)
private_key = "0x60bbe10a196a4e71451c0f6e9ec9beab454c2a5ac0542aa5b8b733ff5719fec3"
deployer = Account.from_key(private_key)

print(f"\n📍 Deployer: {deployer.address}")
print(f"   Balance: {w3.from_wei(w3.eth.get_balance(deployer.address), 'ether')} ETH")

# Ler código do contrato
print("\n📄 Lendo contrato E1Registry.sol...")
with open('E1Registry.sol', 'r') as f:
    contract_source = f.read()

# Compilar contrato
print("🔨 Compilando contrato...")
compiled = compile_source(
    contract_source,
    output_values=['abi', 'bin'],
    solc_version='0.8.0'
)

contract_interface = compiled['<stdin>:E1Registry']
abi = contract_interface['abi']
bytecode = contract_interface['bin']

print(f"✅ Contrato compilado")

# Deploy
print("\n🚀 Fazendo deploy...")
E1Registry = w3.eth.contract(abi=abi, bytecode=bytecode)

# Construir transação de deploy
deploy_txn = E1Registry.constructor().build_transaction({
    'from': deployer.address,
    'nonce': w3.eth.get_transaction_count(deployer.address),
    'gas': 3000000,
    'gasPrice': w3.eth.gas_price,
})

# Assinar e enviar
signed_txn = w3.eth.account.sign_transaction(deploy_txn, private_key)
tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)

print(f"   TX Hash: {tx_hash.hex()}")
print(f"   Aguardando confirmação...")

# Aguardar receipt
receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

if receipt.status == 1:
    print(f"✅ Deploy bem-sucedido!")
    print(f"   Endereço do contrato: {receipt.contractAddress}")
    print(f"   Gas usado: {receipt.gasUsed}")
    print(f"   Block: {receipt.blockNumber}")
    
    # Salvar informações do deploy
    deployment_info = {
        'address': receipt.contractAddress,
        'tx_hash': tx_hash.hex(),
        'deployer': deployer.address,
        'block': receipt.blockNumber,
        'gas_used': receipt.gasUsed,
        'abi': abi,
        'rpc_url': RPC_URL
    }
    
    with open('e1_contract_address.json', 'w') as f:
        json.dump(deployment_info, f, indent=2)
    
    print(f"\n💾 Informações salvas em e1_contract_address.json")
    
    # Verificar owner e oracle
    contract = w3.eth.contract(address=receipt.contractAddress, abi=abi)
    owner = contract.functions.owner().call()
    oracle = contract.functions.oracle().call()
    
    print(f"\n📋 Configurações do contrato:")
    print(f"   Owner: {owner}")
    print(f"   Oracle: {oracle}")
    
else:
    print(f"❌ Deploy falhou!")
    print(f"   Status: {receipt.status}")
