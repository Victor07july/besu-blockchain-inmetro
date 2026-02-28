"""
Template: enviar viagem processada para o contrato Solidity via web3.py
Você precisa fornecer: RPC URL do Besu, endereço do contrato e ABI (arquivo JSON), conta (private key) para assinar.

Este é um exemplo esquelético — adapte os nomes de campos do struct para corresponder ao ABI.
"""

import json
from web3 import Web3


def load_abi(path):
    with open(path, 'r') as f:
        return json.load(f)


def send_register_trip(rpc_url, private_key, contract_address, abi_path, trip_params: dict):
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    acct = w3.eth.account.from_key(private_key)
    abi = load_abi(abi_path)
    contract = w3.eth.contract(address=contract_address, abi=abi)

    # Exemplo: se o método for registerTrip((struct fields))
    tx = contract.functions.registerTrip(trip_params).buildTransaction({
        'from': acct.address,
        'nonce': w3.eth.get_transaction_count(acct.address),
        'gas': 6000000,
        'gasPrice': w3.toWei('1', 'gwei')
    })

    signed = acct.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
    print('tx_hash:', w3.toHex(tx_hash))
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    return receipt


if __name__ == '__main__':
    print('Este é um template: configure RPC, chave, contrato e ABI antes de usar.')

load_abi("../contract/e1_contract_address.json")