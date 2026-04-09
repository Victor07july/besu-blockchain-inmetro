#!/usr/bin/env python3
"""
Script para compilar e fazer deploy do contrato CarbonCreditNFT_E1
"""

import json
import os
import subprocess
from web3 import Web3
from solcx import compile_standard, install_solc
from pathlib import Path

# ====================================================================
# CONFIGURAÇÕES
# ====================================================================

# URL do nó RPC Besu
RPC_URL = "https://ec2-18-117-120-52.us-east-2.compute.amazonaws.com/user/"

# Chave privada da carteira que fará o deploy
# IMPORTANTE: Use uma carteira autorizada na blockchain
PRIVATE_KEY = "0x8f2a55949038a9610f50fb23b5883af3b4ecb3c3bb792cbcefbd1542c692be63"

# Caminhos
CONTRACTS_DIR = Path(__file__).parent.parent / "contracts"
CONTRACT_FILE = CONTRACTS_DIR / "CarbonCreditNFT_E1.sol"
OUTPUT_FILE = Path(__file__).parent / "e1_deployment.json"

# ====================================================================
# FUNÇÕES
# ====================================================================

def ensure_openzeppelin(contracts_dir: Path):
    """Instala @openzeppelin/contracts via npm se não estiver presente"""
    oz_path = contracts_dir / "node_modules" / "@openzeppelin"
    if oz_path.exists():
        print("✅ @openzeppelin/contracts já instalado.")
        return

    print("📦 Instalando @openzeppelin/contracts via npm...")

    pkg_json = contracts_dir / "package.json"
    if not pkg_json.exists():
        subprocess.run(["npm", "init", "-y"], cwd=str(contracts_dir), check=True)

    subprocess.run(
        ["npm", "install", "@openzeppelin/contracts@4.9.3"],
        cwd=str(contracts_dir),
        check=True,
    )
    print("✅ @openzeppelin/contracts instalado com sucesso!")


def compile_contract(contract_path: Path):
    """Compila o contrato Solidity com suporte a imports OpenZeppelin"""
    print("📦 Compilando contrato...")

    contracts_dir = contract_path.parent

    # Garantir que OpenZeppelin está disponível
    ensure_openzeppelin(contracts_dir)

    # Ler o código fonte
    with open(contract_path, "r") as f:
        contract_source = f.read()

    # Instalar versão do Solidity se necessário
    try:
        install_solc("0.8.19")
    except Exception:
        pass  # Já instalado

    # Compilar usando Standard JSON Input (suporta remappings OZ)
    compiled_sol = compile_standard(
        {
            "language": "Solidity",
            "sources": {
                contract_path.name: {"content": contract_source}
            },
            "settings": {
                "remappings": [
                    f"@openzeppelin/={contracts_dir / 'node_modules' / '@openzeppelin'}/"
                ],
                "outputSelection": {
                    "*": {
                        "*": ["abi", "evm.bytecode"]
                    }
                },
            },
        },
        allow_paths=str(contracts_dir),
        solc_version="0.8.19",
    )

    contract_data = compiled_sol["contracts"][contract_path.name]["CarbonCreditNFT_E1"]
    abi = contract_data["abi"]
    bytecode = contract_data["evm"]["bytecode"]["object"]

    print("✅ Contrato compilado com sucesso!")
    return abi, bytecode


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
        "from": account.address,
        "nonce": nonce,
        "gas": 4000000,
        "gasPrice": w3.eth.gas_price,
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


def save_deployment_data(contract_address, abi, gas_used, output_file: Path):
    """Salva dados do deploy em arquivo JSON"""
    deployment_data = {
        "contract_address": contract_address,
        "abi": abi,
        "gas_used": gas_used,
    }

    with open(output_file, "w") as f:
        json.dump(deployment_data, f, indent=2)

    print(f"\n💾 Dados salvos em: {output_file}")


def main():
    print("=" * 70)
    print("DEPLOY DO CARBONCREDITNFT_E1 - CRÉDITO DE CARBONO")
    print("=" * 70)

    # Verificar se arquivo do contrato existe
    if not CONTRACT_FILE.exists():
        print(f"❌ Erro: Arquivo do contrato não encontrado: {CONTRACT_FILE}")
        return

    # Conectar à blockchain
    print(f"\n🔗 Conectando ao nó Besu...")
    print(f"   URL: {RPC_URL}")

    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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
    print(f"   2. Use o endereço do contrato para interagir via web3")
    print(f"   3. Chame calculateAndMint() com os parâmetros desejados")
    print(f"\n📍 Endereço do contrato: {contract_address}")
    print()


if __name__ == "__main__":
    main()
