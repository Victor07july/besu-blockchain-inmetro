#!/usr/bin/env python3
"""
Deploy do contrato E1RegistryGPS no Besu
Implementação 2: Com coordenadas GPS + Differential Privacy
"""

import json
from web3 import Web3
from eth_account import Account
from solcx import compile_standard, install_solc, set_solc_version, get_installed_solc_versions

CONTRACT_FILE = "../contracts/E1RegistryGPS.sol"
OUTPUT_FILE = "../config/e1_gps_contract_address.json"

def compile_contract():
    """Compila o contrato Solidity"""
    print("📦 Compilando contrato E1RegistryGPS.sol...")
    
    # Usar Solidity 0.8.19 para resolver "Stack too deep"
    solc_version = '0.8.19'
    
    # Instalar versão do compilador (se não estiver instalado)
    try:
        if solc_version not in [str(v) for v in get_installed_solc_versions()]:
            print(f"📥 Instalando Solidity {solc_version}...")
            install_solc(solc_version)
    except:
        install_solc(solc_version)
    
    # Definir versão a ser usada
    set_solc_version(solc_version)
    
    # Ler código fonte
    with open(CONTRACT_FILE, 'r') as f:
        contract_source = f.read()
    
    # Compilar com via-IR para resolver Stack too deep
    from solcx import compile_standard
    
    standard_input = {
        "language": "Solidity",
        "sources": {
            CONTRACT_FILE: {
                "content": contract_source
            }
        },
        "settings": {
            "optimizer": {
                "enabled": True,
                "runs": 200
            },
            "viaIR": True,  # Resolve Stack too deep
            "outputSelection": {
                "*": {
                    "*": ["abi", "evm.bytecode"]
                }
            }
        }
    }
    
    print("   Usando compilação via-IR (resolve Stack too deep)...")
    compiled = compile_standard(standard_input)
    
    # Extrair ABI e bytecode
    contract_data = compiled['contracts'][CONTRACT_FILE]['E1RegistryGPS']
    abi = contract_data['abi']
    bytecode = contract_data['evm']['bytecode']['object']
    
    print("✅ Contrato compilado com via-IR")
    return {'abi': abi, 'bin': bytecode}

def deploy_contract():
    """Deploy do contrato no Besu"""
    print("🚀 Iniciando deploy do contrato E1RegistryGPS...\n")
    print("📍 Implementação 2: Com GPS + Differential Privacy\n")
    
    # Compilar
    contract_interface = compile_contract()
    
    # Configurações
    rpc_url = "http://localhost:8545"
    private_key = "0x60bbe10a196a4e71451c0f6e9ec9beab454c2a5ac0542aa5b8b733ff5719fec3"
    account = Account.from_key(private_key)
    
    # Conectar ao Besu
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    
    # Adicionar middleware POA para Besu/QBFT ANTES de qualquer chamada
    from web3.middleware import ExtraDataToPOAMiddleware
    w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    
    # Verificar conexão usando métodos eth_* (não requerem autenticação adicional)
    try:
        chain_id = w3.eth.chain_id
        block_number = w3.eth.block_number
        print(f"✅ Conectado ao Besu: {rpc_url}")
        print(f"   Chain ID: {chain_id} | Block: {block_number}")
    except Exception as e:
        print(f"❌ Erro ao conectar ao Besu: {e}")
        print(f"   Verifique se o Besu está rodando com: curl -X POST {rpc_url}")
        raise Exception(f"Não foi possível conectar ao Besu em {rpc_url}")
    
    print(f"👤 Conta deployer: {account.address}")
    print(f"💰 Balance: {w3.from_wei(w3.eth.get_balance(account.address), 'ether')} ETH")
    
    # Criar contrato
    print("\n📝 Preparando deploy do E1RegistryGPS...")
    Contract = w3.eth.contract(abi=contract_interface['abi'], bytecode=contract_interface['bin'])
    
    # Construir transação de deploy
    print("🚀 Fazendo deploy do contrato...")
    construct_txn = Contract.constructor().build_transaction({
        'from': account.address,
        'nonce': w3.eth.get_transaction_count(account.address),
        'gas': 4000000,
        'gasPrice': w3.eth.gas_price,
    })
    
    # Assinar e enviar transação
    signed_txn = w3.eth.account.sign_transaction(construct_txn, private_key)
    tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)
    
    print(f"⏳ Aguardando confirmação...")
    print(f"   Transaction hash: {tx_hash.hex()}")
    
    # Aguardar confirmação
    tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    
    if tx_receipt['status'] != 1:
        raise Exception(f"Deploy falhou com status: {tx_receipt['status']}")
    
    contract_address = tx_receipt['contractAddress']
    
    print(f"\n✅ Contrato E1RegistryGPS deployado com sucesso!")
    print(f"📍 Endereço: {contract_address}")
    print(f"⛽ Gas usado: {tx_receipt['gasUsed']}")
    print(f"👤 Owner/Oracle: {account.address}")
    
    # Salvar dados do deploy
    deployment = {
        "address": contract_address,
        "owner": account.address,
        "oracle": account.address,
        "abi": contract_interface['abi'],
        "network": "besu-local",
        "rpc_url": rpc_url,
        "tx_hash": tx_hash.hex(),
        "implementation": "E1RegistryGPS",
        "features": ["GPS", "Differential Privacy", "Pseudonimos HD"]
    }
    
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(deployment, f, indent=2)
    
    print(f"\n📁 Dados salvos em: {OUTPUT_FILE}")
    
    # Verificar dados do contrato
    deployed_contract = w3.eth.contract(address=contract_address, abi=contract_interface['abi'])
    stats = deployed_contract.functions.getStats().call()
    
    print("\n📊 Informações do contrato:")
    print(f"   Total viagens: {stats[0]}")
    print(f"   Total pago: R$ {stats[1] / 1e6:.2f}")
    
    print("\n🎉 Deploy concluído! Próximos passos:")
    print("   1. Aplicar DP aos dados: python3 apply_dp.py --epsilon 1.0")
    print("   2. Enviar dados: python3 send_e1_gps_data.py")
    print("   3. Analisar resultados com GPS privatizados")
    
    return deployment

if __name__ == "__main__":
    try:
        deployment = deploy_contract()
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
