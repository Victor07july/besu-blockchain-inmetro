#!/usr/bin/env python3
"""
Deploy do contrato E1Registry no Besu
Compila e faz deploy usando private key
"""

import json
from web3 import Web3
from eth_account import Account
from solcx import compile_source, install_solc, set_solc_version, get_installed_solc_versions

CONTRACT_FILE = "E1Registry.sol"
OUTPUT_FILE = "e1_contract_address.json"

def compile_contract():
    """Compila o contrato Solidity"""
    print("📦 Compilando contrato E1Registry.sol...")
    
    # Instalar versão do compilador (se não estiver instalado)
    try:
        if '0.8.0' not in [str(v) for v in get_installed_solc_versions()]:
            install_solc('0.8.0')
    except:
        install_solc('0.8.0')
    
    # Definir versão a ser usada
    set_solc_version('0.8.0')
    
    # Ler código fonte
    with open(CONTRACT_FILE, 'r') as f:
        contract_source = f.read()
    
    # Compilar
    compiled = compile_source(
        contract_source,
        output_values=['abi', 'bin']
    )
    
    # Pegar contrato compilado
    contract_id, contract_interface = compiled.popitem()
    
    print("✅ Contrato compilado")
    return contract_interface

def deploy_contract():
    """Deploy do contrato no Besu"""
    print("🚀 Iniciando deploy do contrato E1Registry...\n")
    
    # Compilar
    contract_interface = compile_contract()
    
    # Carregar chaves
    print("\n🔑 Carregando chaves...")
    try:
        with open("keys.json") as f:
            keys = json.load(f)
        rpc_url = keys['besu']['rpcnode']['url']
    except:
        # Fallback para rpcnode padrão
        rpc_url = "http://localhost:8545"
    
    private_key = "0x60bbe10a196a4e71451c0f6e9ec9beab454c2a5ac0542aa5b8b733ff5719fec3"
    account = Account.from_key(private_key)
    
    # Conectar ao Besu
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    
    if not w3.is_connected():
        raise Exception("Não foi possível conectar ao Besu")
    
    print(f"✅ Conectado ao Besu: {rpc_url}")
    print(f"👤 Conta deployer: {account.address}")
    print(f"💰 Balance: {w3.from_wei(w3.eth.get_balance(account.address), 'ether')} ETH")
    
    # Criar contrato
    print("\n📝 Preparando deploy do E1Registry...")
    Contract = w3.eth.contract(abi=contract_interface['abi'], bytecode=contract_interface['bin'])
    
    # Construir transação de deploy
    print("🚀 Fazendo deploy do contrato...")
    construct_txn = Contract.constructor().build_transaction({
        'from': account.address,
        'nonce': w3.eth.get_transaction_count(account.address),
        'gas': 3000000,
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
    
    print(f"\n✅ Contrato E1Registry deployado com sucesso!")
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
        "tx_hash": tx_hash.hex()
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
    
    print("\n🎉 Deploy concluído! Você pode agora:")
    print("   1. Executar o script de envio de dados: python3 send_e1_data_v2.py")
    print("   2. Interagir com o contrato através do endereço:", contract_address)
    
    return deployment

if __name__ == "__main__":
    try:
        deployment = deploy_contract()
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
