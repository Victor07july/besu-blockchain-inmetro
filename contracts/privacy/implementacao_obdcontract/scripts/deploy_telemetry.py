#!/usr/bin/env python3
"""
Script para deploy do contrato E1RegistryTelemetry na rede Besu
Utiliza Web3.py e solcx para compilação e deploy

Autor: Victor
Data: 2026-02-23
"""

# 0xfe3b557e8fb62b89f4916b721be55ceb828dbd73

import json
import sys
from web3 import Web3
from eth_account import Account
from pathlib import Path
import time

# Tentar importar solcx para compilação
try:
    from solcx import compile_source, install_solc, set_solc_version
    SOLCX_AVAILABLE = True
except ImportError:
    print("⚠️  solcx não encontrado. Instale com: pip install py-solc-x")
    SOLCX_AVAILABLE = False


def compile_contract(contract_path: str) -> dict:
    """
    Compila o contrato Solidity
    
    Args:
        contract_path: Caminho para o arquivo .sol
        
    Returns:
        Dicionário com abi e bytecode
    """
    if not SOLCX_AVAILABLE:
        print("❌ Compilação não disponível. Use Hardhat ou forneça ABI/bytecode manualmente.")
        sys.exit(1)
    
    print("📝 Compilando contrato...")
    
    # Ler arquivo do contrato
    with open(contract_path, 'r') as f:
        contract_source = f.read()
    
    # Instalar versão do Solidity se necessário
    try:
        install_solc('0.8.19')
        set_solc_version('0.8.19')
    except Exception as e:
        print(f"⚠️  Usando versão padrão do solc: {e}")
    
    # Compilar
    try:
        compiled_sol = compile_source(
            contract_source,
            output_values=['abi', 'bin']
        )
        
        # Pegar primeiro contrato (E1RegistryTelemetry)
        contract_id = list(compiled_sol.keys())[0]
        contract_interface = compiled_sol[contract_id]
        
        print("✓ Contrato compilado com sucesso")
        
        return {
            'abi': contract_interface['abi'],
            'bytecode': contract_interface['bin']
        }
        
    except Exception as e:
        print(f"❌ Erro ao compilar: {e}")
        sys.exit(1)


def load_compiled_contract(abi_path: str = None, bytecode_path: str = None) -> dict:
    """
    Carrega ABI e bytecode de arquivos JSON (alternativa à compilação)
    
    Args:
        abi_path: Caminho para arquivo ABI JSON
        bytecode_path: Caminho para arquivo bytecode
        
    Returns:
        Dicionário com abi e bytecode
    """
    print("📦 Carregando contrato compilado...")
    
    # Tentar carregar do Hardhat artifacts
    if not abi_path:
        hardhat_artifact = "../contracts/artifacts/contracts/E1RegistryTelemetry.sol/E1RegistryTelemetry.json"
        if Path(hardhat_artifact).exists():
            with open(hardhat_artifact, 'r') as f:
                artifact = json.load(f)
                return {
                    'abi': artifact['abi'],
                    'bytecode': artifact['bytecode']
                }
    
    # Carregar de arquivos específicos
    if abi_path and bytecode_path:
        with open(abi_path, 'r') as f:
            abi = json.load(f)
        
        with open(bytecode_path, 'r') as f:
            bytecode = f.read().strip()
        
        return {'abi': abi, 'bytecode': bytecode}
    
    print("❌ Não foi possível carregar ABI/bytecode. Compile o contrato primeiro.")
    sys.exit(1)


def deploy_contract():
    """
    Faz deploy do contrato E1RegistryTelemetry
    """
    print("🚀 Iniciando deploy do contrato E1RegistryTelemetry...\n")
    print("📍 Pipeline Simplificado: Telemetria OBDLink\n")
    
    # Configurações fixas
    rpc_url = "http://localhost:8545"
    private_key = "0x8f2a55949038a9610f50fb23b5883af3b4ecb3c3bb792cbcefbd1542c692be63"
    contract_path = "../contracts/E1RegistryTelemetry.sol"
    gas_limit = 5000000
    
    print("="*70)
    print("🚀 DEPLOY DO CONTRATO E1RegistryTelemetry")
    print("="*70)
    
    # Conectar ao Besu
    print(f"\n🌐 Conectando ao Besu: {rpc_url}")
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    
    # Adicionar middleware POA para Besu/QBFT
    from web3.middleware import ExtraDataToPOAMiddleware
    w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    
    # Verificar conexão
    try:
        chain_id = w3.eth.chain_id
        block_number = w3.eth.block_number
        print(f"✓ Conectado!")
        print(f"  Chain ID: {chain_id}")
        print(f"  Block number: {block_number}")
    except Exception as e:
        print(f"❌ Não foi possível conectar ao nó: {rpc_url}")
        print(f"  Erro: {e}")
        sys.exit(1)
    
    # Configurar conta
    account = Account.from_key(private_key)
    address = account.address
    
    balance = w3.eth.get_balance(address)
    print(f"\n👤 Conta deployer:")
    print(f"  Address: {address}")
    print(f"  Balance: {w3.from_wei(balance, 'ether')} ETH")
    
    if balance == 0:
        print("❌ Saldo insuficiente para deploy")
        sys.exit(1)
    
    # Compilar ou carregar contrato
    if contract_path and SOLCX_AVAILABLE and Path(contract_path).exists():
        contract_data = compile_contract(contract_path)
    else:
        contract_data = load_compiled_contract()
    
    # Criar objeto do contrato
    Contract = w3.eth.contract(
        abi=contract_data['abi'],
        bytecode=contract_data['bytecode']
    )
    
    # Construir transação de deploy
    print(f"\n📤 Preparando transação de deploy...")
    
    nonce = w3.eth.get_transaction_count(address)
    
    # Estimar gas
    try:
        gas_estimate = Contract.constructor().estimate_gas({'from': address})
        print(f"  Gas estimado: {gas_estimate:,}")
    except Exception as e:
        print(f"  ⚠️  Não foi possível estimar gas: {e}")
        gas_estimate = gas_limit
    
    # Construir transação
    transaction = Contract.constructor().build_transaction({
        'from': address,
        'nonce': nonce,
        'gas': min(gas_estimate + 100000, gas_limit),
        'gasPrice': w3.eth.gas_price,
    })
    
    print(f"  Nonce: {nonce}")
    print(f"  Gas limit: {transaction['gas']:,}")
    print(f"  Gas price: {w3.from_wei(transaction['gasPrice'], 'gwei')} gwei")
    
    # Assinar transação
    print(f"\n🔏 Assinando transação...")
    signed_txn = w3.eth.account.sign_transaction(transaction, private_key=private_key)
    
    # Enviar transação
    print(f"📡 Enviando transação...")
    tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)
    
    print(f"✓ Transação enviada!")
    print(f"  TX hash: {tx_hash.hex()}")
    
    # Aguardar confirmação
    print(f"\n⏳ Aguardando confirmação...")
    try:
        tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
        
        if tx_receipt['status'] == 1:
            contract_address = tx_receipt['contractAddress']
            
            print(f"\n✅ CONTRATO DEPLOYADO COM SUCESSO!")
            print("="*70)
            print(f"📍 Endereço: {contract_address}")
            print(f"📦 Block: {tx_receipt['blockNumber']}")
            print(f"⛽ Gas usado: {tx_receipt['gasUsed']:,}")
            print(f"💰 Custo: {w3.from_wei(tx_receipt['gasUsed'] * transaction['gasPrice'], 'ether')} ETH")
            print("="*70)
            
            # Salvar informações
            save_deployment_info(contract_address, contract_data['abi'], tx_hash.hex(), rpc_url)
            
            # Verificar deploy
            verify_deployment(w3, contract_address, contract_data['abi'])
            
            # Instruções finais
            print("\n" + "="*70)
            print("📋 PRÓXIMOS PASSOS")
            print("="*70)
            print("\n1. Processar dados OBD:")
            print(f"   cd scripts")
            print(f"   python3 process_obdlink_telemetry.py ../../data/OBDLink.csv trips.csv VEHICLE_001 0.5")
            print("\n2. Enviar viagens ao blockchain:")
            print(f"   python3 send_telemetry_to_blockchain.py trips.csv {contract_address}")
            print("\n3. Ou use o endereço salvo em deployment_info.json")
            print("="*70 + "\n")
            
            return contract_address
            
        else:
            print(f"❌ Deploy falhou!")
            print(f"  Receipt: {tx_receipt}")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Timeout ou erro: {e}")
        sys.exit(1)


def save_deployment_info(contract_address: str, abi: list, tx_hash: str, rpc_url: str):
    """
    Salva informações do deploy em arquivo JSON
    """
    deployment_info = {
        'contract_address': contract_address,
        'tx_hash': tx_hash,
        'rpc_url': rpc_url,
        'timestamp': time.time(),
        'abi': abi
    }
    
    output_file = '../deployment_info.json'
    
    with open(output_file, 'w') as f:
        json.dump(deployment_info, f, indent=2)
    
    print(f"\n💾 Informações salvas em: {output_file}")


def verify_deployment(w3: Web3, contract_address: str, abi: list):
    """
    Verifica se o contrato foi deployado corretamente
    """
    print(f"\n🔍 Verificando deployment...")
    
    contract = w3.eth.contract(address=contract_address, abi=abi)
    
    try:
        # Verificar owner
        owner = contract.functions.owner().call()
        print(f"  ✓ Owner: {owner}")
        
        # Verificar oracle
        oracle = contract.functions.oracle().call()
        print(f"  ✓ Oracle: {oracle}")
        
        # Verificar tripCount
        trip_count = contract.functions.tripCount().call()
        print(f"  ✓ Trip count: {trip_count}")
        
        print(f"\n✅ Contrato verificado e funcional!")
        
    except Exception as e:
        print(f"  ⚠️  Erro na verificação: {e}")


def main():
    """
    Função principal
    """
    print("\n" + "="*70)
    print("🏗️  E1RegistryTelemetry - Script de Deploy")
    print("="*70 + "\n")
    
    try:
        deployment = deploy_contract()
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        exit(1)


if __name__ == "__main__":
    main()
