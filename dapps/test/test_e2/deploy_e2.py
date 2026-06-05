#!/usr/bin/env python3
"""
Script para compilar e fazer deploy do contrato CarbonCreditNFT_E2Calculator
"""

import json
import subprocess
from pathlib import Path

from solcx import compile_standard, install_solc
from web3 import Web3

# ====================================================================
# CONFIGURACOES
# ====================================================================

RPC_URL = "https://ec2-3-133-99-147.us-east-2.compute.amazonaws.com/user/"
PRIVATE_KEY = "0x8f2a55949038a9610f50fb23b5883af3b4ecb3c3bb792cbcefbd1542c692be63"

CONTRACTS_DIR = Path(__file__).parent.parent / "contracts"
CONTRACT_FILE = CONTRACTS_DIR / "CarbonCreditNFT_E2.sol"
OUTPUT_FILE = Path(__file__).parent / "e2_deployment.json"


def ensure_openzeppelin(contracts_dir: Path):
	"""Instala @openzeppelin/contracts via npm se nao estiver presente."""
	oz_path = contracts_dir / "node_modules" / "@openzeppelin"
	if oz_path.exists():
		print("[ok] @openzeppelin/contracts ja instalado")
		return

	print("[info] Instalando @openzeppelin/contracts...")
	pkg_json = contracts_dir / "package.json"
	if not pkg_json.exists():
		subprocess.run(["npm", "init", "-y"], cwd=str(contracts_dir), check=True)

	subprocess.run(
		["npm", "install", "@openzeppelin/contracts@4.9.3"],
		cwd=str(contracts_dir),
		check=True,
	)
	print("[ok] @openzeppelin/contracts instalado")


def compile_contract(contract_path: Path):
	"""Compila contrato Solidity com suporte a imports OpenZeppelin."""
	print("[info] Compilando contrato...")

	contracts_dir = contract_path.parent
	ensure_openzeppelin(contracts_dir)

	with open(contract_path, "r", encoding="utf-8") as f:
		contract_source = f.read()

	try:
		install_solc("0.8.19")
	except Exception:
		pass

	compiled_sol = compile_standard(
		{
			"language": "Solidity",
			"sources": {contract_path.name: {"content": contract_source}},
			"settings": {
				"remappings": [
					f"@openzeppelin/={contracts_dir / 'node_modules' / '@openzeppelin'}/"
				],
				"outputSelection": {"*": {"*": ["abi", "evm.bytecode"]}},
			},
		},
		allow_paths=str(contracts_dir),
		solc_version="0.8.19",
	)

	contract_data = compiled_sol["contracts"][contract_path.name]["CarbonCreditNFT_E2Calculator"]
	abi = contract_data["abi"]
	bytecode = contract_data["evm"]["bytecode"]["object"]

	print("[ok] Contrato compilado")
	return abi, bytecode


def deploy_contract(w3: Web3, abi, bytecode, private_key: str):
	"""Faz o deploy do contrato."""
	print("[info] Fazendo deploy...")

	account = w3.eth.account.from_key(private_key)
	print(f"[info] Deployer: {account.address}")
	print(f"[info] Balance: {w3.from_wei(w3.eth.get_balance(account.address), 'ether')} ETH")

	contract = w3.eth.contract(abi=abi, bytecode=bytecode)
	nonce = w3.eth.get_transaction_count(account.address)

	tx = contract.constructor().build_transaction(
		{
			"from": account.address,
			"nonce": nonce,
			"gas": 5000000,
			"gasPrice": w3.eth.gas_price,
		}
	)

	signed = w3.eth.account.sign_transaction(tx, private_key)
	tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
	print(f"[info] TX deploy enviada: {tx_hash.hex()}")

	receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
	print(f"[ok] Contrato deployado: {receipt.contractAddress}")
	print(f"[ok] Gas usado: {receipt.gasUsed}")
	print(f"[ok] Bloco: {receipt.blockNumber}")

	return receipt.contractAddress, receipt.gasUsed


def save_deployment_data(contract_address: str, abi, gas_used: int, output_file: Path):
	"""Salva dados de deploy em JSON."""
	payload = {
		"contract_address": contract_address,
		"abi": abi,
		"gas_used": gas_used,
	}
	with open(output_file, "w", encoding="utf-8") as f:
		json.dump(payload, f, indent=2)
	print(f"[ok] JSON salvo em: {output_file}")


def main():
	print("=" * 70)
	print("DEPLOY DO CARBONCREDITNFT_E2")
	print("=" * 70)

	if not CONTRACT_FILE.exists():
		print(f"[erro] Contrato nao encontrado: {CONTRACT_FILE}")
		return

	print(f"[info] Conectando no Besu: {RPC_URL}")

	import urllib3
	import requests
	from web3.providers import HTTPProvider

	urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
	session = requests.Session()
	session.verify = False

	w3 = Web3(HTTPProvider(RPC_URL, session=session))
	if not w3.is_connected():
		print("[erro] Nao foi possivel conectar no Besu")
		return

	print(f"[ok] Conectado | chain_id={w3.eth.chain_id} | latest_block={w3.eth.block_number}")

	abi, bytecode = compile_contract(CONTRACT_FILE)
	contract_address, gas_used = deploy_contract(w3, abi, bytecode, PRIVATE_KEY)
	save_deployment_data(contract_address, abi, gas_used, OUTPUT_FILE)

	print("=" * 70)
	print("DEPLOY CONCLUIDO")
	print("=" * 70)
	print(f"Contrato: {contract_address}")


if __name__ == "__main__":
	main()
