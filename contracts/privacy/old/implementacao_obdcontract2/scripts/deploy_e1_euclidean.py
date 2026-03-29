#!/usr/bin/env python3
"""
Script de deploy para E1RegistryEuclidean
Compila e deploya o contrato no Hyperledger Besu

Autor: Victor
Data: 2026-02-28
"""

import json
import sys
from web3 import Web3
from eth_account import Account
from solcx import compile_standard, install_solc

# Configurações
CONTRACT_FILE = "../contracts/E1RegistryEuclidean.sol"
SOLC_VERSION = "0.8.19"


def compile_contract():
    """Compila o contrato Solidity com via-IR"""
    print("📦 Compilando contrato E1RegistryEuclidean.sol...")
    print(f"   Solidity version: {SOLC_VERSION}")
    
    # Instalar versão do compilador se necessário
    try:
        install_solc(SOLC_VERSION)
    except:
        pass
    
    # Ler código fonte
    with open(CONTRACT_FILE, 'r') as f:
        contract_source = f.read()
    
    # Compilar com via-IR (resolve Stack too deep)
    print("   Usando compilação via-IR...")
    compiled = compile_standard({
        "language": "Solidity",
        "sources": {
            "E1RegistryEuclidean.sol": {
                "content": contract_source
            }
        },
        "settings": {
            "optimizer": {
                "enabled": True,
                "runs": 200
            },
            "viaIR": True,
            "outputSelection": {
                "*": {
                    "*": ["abi", "metadata", "evm.bytecode", "evm.sourceMap"]
                }
            }
        }
    }, solc_version=SOLC_VERSION)
    
    contract_interface = compiled['contracts']['E1RegistryEuclidean.sol']['E1RegistryEuclidean']
    
    print("✅ Contrato compilado com via-IR")
    return contract_interface


def deploy_contract():
    """Deploya o contrato no Besu"""
    print("\n🚀 Iniciando deploy do contrato E1RegistryEuclidean...\n")
    
    # Compilar
    contract_interface = compile_contract()
    
    # Configurações
    rpc_url = "http://localhost:8545"
    private_key = "0x8f2a55949038a9610f50fb23b5883af3b4ecb3c3bb792cbcefbd1542c692be63"
    account = Account.from_key(private_key)
    
    print("\n📡 Conectando ao Besu...")
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    
    # Adicionar middleware POA ANTES de qualquer chamada
    from web3.middleware import ExtraDataToPOAMiddleware
    w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    
    # Verificar conexão usando métodos eth_*
    try:
        chain_id = w3.eth.chain_id
        block_number = w3.eth.block_number
        print(f"✅ Conectado ao Besu: {rpc_url}")
        print(f"   Chain ID: {chain_id}")
        print(f"   Block number: {block_number}")
    except Exception as e:
        print(f"❌ Erro ao conectar: {e}")
        raise Exception(f"Não foi possível conectar ao Besu em {rpc_url}")
    
    print(f"👤 Conta deployer: {account.address}")
    print(f"💰 Balance: {w3.from_wei(w3.eth.get_balance(account.address), 'ether')} ETH")
    
    # Preparar deploy
    print("\n📝 Preparando deploy do E1RegistryEuclidean...")
    
    Contract = w3.eth.contract(
        abi=contract_interface['abi'],
        bytecode=contract_interface['evm']['bytecode']['object']
    )
    
    # Construir transação
    nonce = w3.eth.get_transaction_count(account.address)
    
    transaction = Contract.constructor().build_transaction({
        'from': account.address,
        'nonce': nonce,
        'gas': 3000000,
        'gasPrice': w3.eth.gas_price,
    })
    
    # Assinar transação
    signed_txn = w3.eth.account.sign_transaction(transaction, private_key)
    
    # Enviar transação
    print("🚀 Fazendo deploy do contrato...")
    tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)
    
    # Aguardar confirmação
    print("⏳ Aguardando confirmação...")
    print(f"   Transaction hash: {tx_hash.hex()}")
    
    tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    
    contract_address = tx_receipt.contractAddress
    
    print("\n✅ Contrato E1RegistryEuclidean deployado com sucesso!")
    print(f"📍 Endereço: {contract_address}")
    print(f"⛽ Gas usado: {tx_receipt.gasUsed}")
    print(f"👤 Owner/Oracle: {account.address}")
    
    # Salvar informações de deployment
    deployment_info = {
        "contract_address": contract_address,
        "abi": contract_interface['abi'],
        "rpc_url": rpc_url,
        "deployer": account.address,
        "tx_hash": tx_hash.hex(),
        "block_number": tx_receipt.blockNumber,
        "gas_used": tx_receipt.gasUsed
    }
    
    output_file = "deployment_info.json"
    with open(output_file, 'w') as f:
        json.dump(deployment_info, f, indent=2)
    
    print(f"\n📁 Dados salvos em: {output_file}")
    
    # Testar contrato
    print("\n📊 Informações do contrato:")
    contract = w3.eth.contract(
        address=contract_address,
        abi=contract_interface['abi']
    )
    
    stats = contract.functions.getStats().call()
    print(f"   Total viagens: {stats[0]}")
    print(f"   Total créditos: R$ {stats[1] / 1e6:.2f}")
    print(f"   Total débitos: R$ {stats[2] / 1e6:.2f}")
    print(f"   Saldo líquido: R$ {stats[3] / 1e6:.2f}")
    
    print("\n🎉 Deploy concluído! Próximos passos:")
    print("   1. Processar dados: python3 process_obd_euclidean.py ../data/OBDLink.csv")
    print("   2. Enviar dados: python3 send_trips_to_blockchain.py trips_processed.csv")
    
    return deployment_info


def main():
    """Função principal"""
    try:
        deploy_contract()
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
