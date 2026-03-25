#!/usr/bin/env python3
"""
Modulo separado para envio de resultados do oraculo para blockchain.

O modulo e propositalmente generico: o metodo do contrato e os argumentos
sao definidos em runtime via CLI (no oraculo) para desacoplar da ABI final.
"""

import json
from typing import Any, Dict, List

from eth_account import Account
from web3 import Web3

try:
    from web3.middleware import ExtraDataToPOAMiddleware
except ImportError:
    ExtraDataToPOAMiddleware = None


DEFAULT_GAS_LIMIT = 900000


def load_deployment_info(deployment_file: str) -> Dict[str, Any]:
    with open(deployment_file, "r", encoding="utf-8") as f:
        return json.load(f)


def resolve_json_path(result: Dict[str, Any], spec: str) -> Any:
    if not spec.startswith("$."):
        return spec

    current: Any = result
    for part in spec[2:].split("."):
        if not isinstance(current, dict) or part not in current:
            raise KeyError(f"Caminho de argumento nao encontrado: {spec}")
        current = current[part]
    return current


def resolve_method_args(result: Dict[str, Any], method_args_spec: List[str]) -> List[Any]:
    args: List[Any] = []
    for spec in method_args_spec:
        args.append(resolve_json_path(result, spec))
    return args


def get_web3(rpc_url: str) -> Web3:
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    if ExtraDataToPOAMiddleware is not None:
        w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    return w3


def send_oracle_results(
    results: List[Dict[str, Any]],
    deployment_file: str,
    private_key: str,
    method_name: str,
    method_args_spec: List[str],
    gas_limit: int = DEFAULT_GAS_LIMIT,
) -> List[str]:
    deployment = load_deployment_info(deployment_file)

    contract_address = deployment["contract_address"]
    abi = deployment["abi"]
    rpc_url = deployment.get("rpc_url", "http://localhost:8545")
    chain_id = deployment.get("chain_id")
    gas_price_gwei = deployment.get("gas_price_gwei", 0)

    w3 = get_web3(rpc_url)
    if not w3.is_connected():
        raise ConnectionError(f"Nao foi possivel conectar ao RPC: {rpc_url}")

    account = Account.from_key(private_key)
    contract = w3.eth.contract(address=contract_address, abi=abi)

    tx_hashes: List[str] = []

    for result in results:
        fn_args = resolve_method_args(result, method_args_spec)

        if not hasattr(contract.functions, method_name):
            raise AttributeError(f"Metodo {method_name} nao encontrado no contrato")

        nonce = w3.eth.get_transaction_count(account.address)
        tx_payload = {
            "from": account.address,
            "nonce": nonce,
            "gas": gas_limit,
            "gasPrice": w3.to_wei(gas_price_gwei, "gwei"),
        }
        if chain_id is not None:
            tx_payload["chainId"] = int(chain_id)

        txn = getattr(contract.functions, method_name)(*fn_args).build_transaction(tx_payload)
        signed = w3.eth.account.sign_transaction(txn, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

        if receipt["status"] != 1:
            raise RuntimeError(f"Transacao revertida para vehicle_id={result.get('vehicle_id')}")

        tx_hashes.append(tx_hash.hex())

    return tx_hashes
