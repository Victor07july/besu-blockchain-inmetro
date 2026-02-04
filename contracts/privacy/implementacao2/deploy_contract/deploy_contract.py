#!/usr/bin/env python3
"""
Script para compilar e fazer deploy de contratos Solidity no Besu
Uso: python3 deploy_contract.py <arquivo.sol> [--constructor-args arg1 arg2 ...]

Exemplo:
  python3 deploy_contract.py MyContract.sol
  python3 deploy_contract.py MyContract.sol --constructor-args 42 "Hello"
"""

import argparse
import json
import sys
from pathlib import Path
from web3 import Web3
from eth_account import Account

def compile_contract(contract_path: str):
    """Compila contrato Solidity"""
    try:
        from solcx import compile_source, install_solc, set_solc_version, get_installed_solc_versions
        import re
    except ImportError:
        print("❌ Erro: py-solc-x não está instalado")
        print("   Instale com: pip install py-solc-x")
        sys.exit(1)
    
    print(f"📦 Compilando contrato: {contract_path}")
    
    # Ler arquivo
    if not Path(contract_path).exists():
        print(f"❌ Arquivo não encontrado: {contract_path}")
        sys.exit(1)
    
    with open(contract_path, 'r') as f:
        source_code = f.read()
    
    # Detectar versão do Solidity
    pragma_match = re.search(r'pragma\s+solidity\s+[\^~]?([0-9]+\.[0-9]+\.[0-9]+)', source_code)
    if pragma_match:
        solc_version = pragma_match.group(1)
        
        # Limitar a 0.8.19 (Besu não suporta 0.8.20+)
        version_parts = list(map(int, solc_version.split('.')))
        if version_parts[0] == 0 and version_parts[1] == 8 and version_parts[2] >= 20:
            solc_version = "0.8.19"
            print(f"⚠️  Usando Solidity 0.8.19 (Besu não suporta 0.8.20+)")
    else:
        # Tentar detectar major.minor
        pragma_match = re.search(r'pragma\s+solidity\s+[\^~]?([0-9]+\.[0-9]+)', source_code)
        if pragma_match:
            version = pragma_match.group(1)
            if version.startswith('0.8'):
                solc_version = "0.8.19"
            elif version.startswith('0.7'):
                solc_version = "0.7.6"
            elif version.startswith('0.6'):
                solc_version = "0.6.12"
            else:
                solc_version = "0.8.19"
        else:
            solc_version = "0.8.19"
    
    # Instalar versão do compilador
    try:
        if solc_version not in [str(v) for v in get_installed_solc_versions()]:
            print(f"📥 Instalando Solidity {solc_version}...")
            install_solc(solc_version)
        set_solc_version(solc_version)
    except Exception as e:
        print(f"❌ Erro ao instalar compilador: {e}")
        sys.exit(1)
    
    # Compilar
    try:
        # Tentar com remappings OpenZeppelin
        import_remappings = [
            '@openzeppelin/contracts=/usr/local/lib/node_modules/@openzeppelin/contracts',
        ]
        
        try:
            compiled = compile_source(
                source_code,
                import_remappings=import_remappings,
                allow_paths='/usr/local/lib/node_modules'
            )
        except:
            # Fallback sem remappings
            compiled = compile_source(source_code)
        
        # Pegar contrato principal (maior bytecode)
        main_contract = None
        max_size = 0
        
        for contract_id, interface in compiled.items():
            bytecode_size = len(interface['bin'])
            if bytecode_size > max_size:
                max_size = bytecode_size
                main_contract = (contract_id, interface)
        
        if not main_contract:
            contract_id, interface = next(iter(compiled.items()))
        else:
            contract_id, interface = main_contract
        
        contract_name = contract_id.split(':')[-1]
        
        print(f"✅ Contrato compilado: {contract_name}")
        print(f"   Bytecode: {len(interface['bin'])} bytes")
        print(f"   ABI: {len(interface['abi'])} funções")
        
        return {
            'name': contract_name,
            'abi': interface['abi'],
            'bytecode': interface['bin']
        }
        
    except Exception as e:
        print(f"❌ Erro de compilação: {e}")
        sys.exit(1)

def deploy_contract(contract, constructor_args, rpc_url, private_key, gas_limit):
    """Faz deploy do contrato"""
    print(f"\n🚀 Fazendo deploy do contrato...")
    
    # Conectar ao Besu
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    
    # Adicionar middleware POA para Besu/QBFT
    from web3.middleware import ExtraDataToPOAMiddleware
    w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    
    if not w3.is_connected():
        print(f"❌ Não foi possível conectar ao Besu: {rpc_url}")
        sys.exit(1)
    
    print(f"✅ Conectado ao Besu: {rpc_url}")
    
    # Carregar conta
    account = Account.from_key(private_key)
    deployer = account.address
    
    balance = w3.eth.get_balance(deployer)
    print(f"👤 Deployer: {deployer}")
    print(f"💰 Balance: {w3.from_wei(balance, 'ether')} ETH")
    
    # Criar contrato
    Contract = w3.eth.contract(
        abi=contract['abi'],
        bytecode=contract['bytecode']
    )
    
    # Construir transação
    try:
        if constructor_args:
            print(f"📝 Parâmetros do construtor: {constructor_args}")
            constructor_txn = Contract.constructor(*constructor_args).build_transaction({
                'from': deployer,
                'nonce': w3.eth.get_transaction_count(deployer),
                'gas': gas_limit,
                'gasPrice': w3.eth.gas_price,
            })
        else:
            constructor_txn = Contract.constructor().build_transaction({
                'from': deployer,
                'nonce': w3.eth.get_transaction_count(deployer),
                'gas': gas_limit,
                'gasPrice': w3.eth.gas_price,
            })
    except Exception as e:
        print(f"❌ Erro ao preparar transação: {e}")
        print(f"\n💡 Dica: Verifique os parâmetros do construtor")
        sys.exit(1)
    
    # Assinar transação
    signed_txn = w3.eth.account.sign_transaction(constructor_txn, private_key)
    
    # Enviar transação
    print(f"📡 Enviando transação...")
    tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)
    print(f"   TX Hash: {tx_hash.hex()}")
    
    # Aguardar confirmação
    print(f"⏳ Aguardando confirmação...")
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
    
    if receipt['status'] != 1:
        print(f"❌ Deploy falhou!")
        print(f"   Gas usado: {receipt['gasUsed']}")
        sys.exit(1)
    
    contract_address = receipt['contractAddress']
    
    print(f"\n✅ Deploy bem-sucedido!")
    print(f"📍 Endereço: {contract_address}")
    print(f"⛽ Gas usado: {receipt['gasUsed']}")
    print(f"🔗 TX Hash: {tx_hash.hex()}")
    
    return {
        'address': contract_address,
        'tx_hash': tx_hash.hex(),
        'gas_used': receipt['gasUsed'],
        'deployer': deployer
    }

def save_deployment(contract, deployment, output_file):
    """Salva dados do deploy em JSON"""
    data = {
        'contract_name': contract['name'],
        'address': deployment['address'],
        'deployer': deployment['deployer'],
        'tx_hash': deployment['tx_hash'],
        'gas_used': deployment['gas_used'],
        'abi': contract['abi'],
        'network': 'besu-local'
    }
    
    with open(output_file, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"\n📁 Dados salvos em: {output_file}")

def main():
    parser = argparse.ArgumentParser(
        description='Compila e faz deploy de contratos Solidity no Besu',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  # Deploy simples (sem parâmetros no construtor)
  python3 deploy_contract.py MyContract.sol
  
  # Deploy com parâmetros do construtor
  python3 deploy_contract.py MyToken.sol --constructor-args "My Token" "MTK" 1000000
  
  # Deploy com RPC customizado
  python3 deploy_contract.py MyContract.sol --rpc http://localhost:20000
  
  # Deploy com gas limit maior
  python3 deploy_contract.py BigContract.sol --gas-limit 5000000
  
  # Deploy com private key customizada
  python3 deploy_contract.py MyContract.sol --private-key 0x123...
        """
    )
    
    parser.add_argument('contract_file', help='Arquivo .sol do contrato')
    parser.add_argument('--constructor-args', nargs='*', default=[], 
                       help='Argumentos do construtor (separados por espaço)')
    parser.add_argument('--rpc', default='http://localhost:8545',
                       help='URL do RPC do Besu (default: http://localhost:8545)')
    parser.add_argument('--private-key', 
                       default='0x60bbe10a196a4e71451c0f6e9ec9beab454c2a5ac0542aa5b8b733ff5719fec3',
                       help='Private key do deployer (default: oracle key)')
    parser.add_argument('--gas-limit', type=int, default=3000000,
                       help='Gas limit (default: 3000000)')
    parser.add_argument('--output', 
                       help='Arquivo de saída JSON (default: <contract_name>_deployment.json)')
    
    args = parser.parse_args()
    
    print("="*60)
    print("🔨 Deploy Automático de Contrato Solidity")
    print("="*60)
    
    # Compilar
    contract = compile_contract(args.contract_file)
    
    # Converter argumentos do construtor (tentar inferir tipos)
    constructor_args = []
    for arg in args.constructor_args:
        # Tentar converter para int
        try:
            constructor_args.append(int(arg))
            continue
        except ValueError:
            pass
        
        # Tentar converter para endereço Ethereum
        if arg.startswith('0x') and len(arg) == 42:
            constructor_args.append(arg)
            continue
        
        # Caso contrário, manter como string
        constructor_args.append(arg)
    
    # Deploy
    deployment = deploy_contract(
        contract,
        constructor_args,
        args.rpc,
        args.private_key,
        args.gas_limit
    )
    
    # Salvar
    output_file = args.output or f"{contract['name']}_deployment.json"
    save_deployment(contract, deployment, output_file)
    
    print("\n✅ Deploy concluído com sucesso!")
    print(f"\n💡 Para interagir com o contrato:")
    print(f"   Endereço: {deployment['address']}")
    print(f"   ABI: Ver arquivo {output_file}")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Deploy cancelado pelo usuário")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
