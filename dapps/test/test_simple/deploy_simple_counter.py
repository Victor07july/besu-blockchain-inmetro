#!/usr/bin/env python3
"""
Script para compilar e fazer deploy do contrato SimpleCounter
"""

import json
import os
from web3 import Web3
from solcx import compile_source, install_solc
from pathlib import Path

# ====================================================================
# CONFIGURAÇÕES
# ====================================================================

# URL do nó RPC Besu
RPC_URL = "https://ec2-18-191-167-241.us-east-2.compute.amazonaws.com/user/"

# Chave privada da carteira que fará o deploy
# IMPORTANTE: Use uma carteira autorizada na blockchain
PRIVATE_KEY = "0x8f2a55949038a9610f50fb23b5883af3b4ecb3c3bb792cbcefbd1542c692be63"

# Caminho do contrato
CONTRACT_FILE = Path(__file__).parent / "SimpleCounter.sol"
OUTPUT_FILE = Path(__file__).parent / "simple_counter_deployment.json"

# ====================================================================
# FUNÇÕES
# ====================================================================

def compile_contract(contract_path):
    """Compila o contrato Solidity"""
    print("📦 Compilando contrato...")
    
    # Ler o código fonte
    with open(contract_path, 'r') as file:
        contract_source = file.read()
    
    # Instalar versão do Solidity se necessário
    try:
        install_solc('0.8.19')
    except:
        pass  # Já instalado
    
    # Compilar
    compiled_sol = compile_source(
        contract_source,
        output_values=['abi', 'bin'],
        solc_version='0.8.19'
    )
    
    # Pegar o contrato compilado
    contract_id, contract_interface = compiled_sol.popitem()
    
    print("✅ Contrato compilado com sucesso!")
    return contract_interface['abi'], contract_interface['bin']


def deploy_contract(w3, abi, bytecode, private_key):
    """Faz o deploy do contrato"""
    print("\n🚀 Fazendo deploy do contrato...")
    
    # Criar conta a partir da chave privada
    account = w3.eth.account.from_key(private_key)
    
    print(f"📍 Endereço do deployer: {account.address}")
    print(f"💰 Balance: {w3.from_wei(w3.eth.get_balance(account.address), 'ether')} ETH")
    
    # Criar objeto do contrato
    Contract = w3.eth.contract(abi=abi, bytecode=bytecode)
    
    # Obter nonce
    nonce = w3.eth.get_transaction_count(account.address)
    
    # Construir transação de deploy
    transaction = Contract.constructor().build_transaction({
        'from': account.address,
        'nonce': nonce,
        'gas': 2000000,
        'gasPrice': w3.eth.gas_price
    })
    
    # Assinar transação
    signed_txn = w3.eth.account.sign_transaction(transaction, private_key)
    
    # Enviar transação
    print("📤 Enviando transação de deploy...")
    tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)
    
    # Aguardar confirmação
    print("⏳ Aguardando confirmação...")
    tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
    
    contract_address = tx_receipt.contractAddress
    
    print(f"✅ Contrato deployado em: {contract_address}")
    print(f"⛽ Gas usado: {tx_receipt.gasUsed}")
    print(f"📦 Block number: {tx_receipt.blockNumber}")
    
    return contract_address, tx_receipt.gasUsed


def save_deployment_data(contract_address, abi, gas_used, output_file):
    """Salva dados do deploy em arquivo JSON"""
    deployment_data = {
        "contract_address": contract_address,
        "abi": abi,
        "gas_used": gas_used
    }
    
    with open(output_file, 'w') as f:
        json.dump(deployment_data, f, indent=2)
    
    print(f"\n💾 Dados salvos em: {output_file}")


def main():
    print("=" * 70)
    print("DEPLOY DO SIMPLE COUNTER - TESTE DE PERFORMANCE")
    print("=" * 70)
    
    # Verificar se arquivo do contrato existe
    if not CONTRACT_FILE.exists():
        print(f"❌ Erro: Arquivo do contrato não encontrado: {CONTRACT_FILE}")
        return
    
    # Conectar à blockchain
    print(f"\n🔗 Conectando ao nó Besu...")
    print(f"   URL: {RPC_URL}")
    
    # Desabilitar verificação SSL (para ambiente de desenvolvimento)
    import ssl
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    # Criar sessão com SSL desabilitado
    from web3.providers import HTTPProvider
    import requests
    
    session = requests.Session()
    session.verify = False
    
    w3 = Web3(HTTPProvider(RPC_URL, session=session))
    
    if not w3.is_connected():
        print("❌ Erro: Não foi possível conectar ao nó Besu")
        return
    
    print("✅ Conectado com sucesso!")
    print(f"   Chain ID: {w3.eth.chain_id}")
    print(f"   Latest block: {w3.eth.block_number}")
    
    # Compilar contrato
    abi, bytecode = compile_contract(CONTRACT_FILE)
    
    # Fazer deploy
    contract_address, gas_used = deploy_contract(w3, abi, bytecode, PRIVATE_KEY)
    
    # Salvar dados
    save_deployment_data(contract_address, abi, gas_used, OUTPUT_FILE)
    
    print("\n" + "=" * 70)
    print("✨ DEPLOY CONCLUÍDO COM SUCESSO!")
    print("=" * 70)
    print(f"\n📋 PRÓXIMOS PASSOS:")
    print(f"   1. Copie o arquivo: {OUTPUT_FILE}")
    print(f"   2. Use no código Go alterando a constante DeploymentJSON")
    print(f"   3. Execute o teste de performance")
    print(f"\n📍 Endereço do contrato: {contract_address}")
    print()


if __name__ == "__main__":
    main()
