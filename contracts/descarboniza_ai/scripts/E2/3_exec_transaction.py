import json
from web3 import Web3
from eth_account import Account

# === 1. Carregar chaves da conta e URL do nó ===
with open("keys.json") as f:
    keys = json.load(f)

rpc_url = keys['besu']['rpcnode']['url']
private_key = "0x60bbe10a196a4e71451c0f6e9ec9beab454c2a5ac0542aa5b8b733ff5719fec3"
account = Account.from_key(private_key)

# Conectar ao nó Besu
w3 = Web3(Web3.HTTPProvider(rpc_url))

print(w3.eth.get_code(account.address))

# Endereço do contrato, deve ser alterado a cada implementação
contract_address = "0x9A8ea6736DF00Af70D1cD70b1Daf3619C8c0D7F4"

with open("../contracts/CarbonCreditV2.json") as f:
    contract_json = json.load(f)
    abi = contract_json['contracts']['../contracts/CarbonCreditV2.sol']['CarbonCreditNFT']["abi"]

# === 8. Interagir com o contrato ===
contract = w3.eth.contract(address=contract_address, abi=abi)

# Chamar função `set()` (transação)
tx = contract.functions.registrarViagemDetalhada(account.address, 10, 10, 5).build_transaction({
    'from': account.address,
    'nonce': w3.eth.get_transaction_count(account.address),
    'gas': 100000,
    'gasPrice': w3.eth.gas_price,
})

signed_tx = w3.eth.account.sign_transaction(tx, private_key)
#signed_tx2 = Account.sign_transaction(tx2, private_key)
tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
print("Enviando transação...")

w3.eth.wait_for_transaction_receipt(tx_hash)

# ======== CONSULTAR VEÍCULOS ========

# valor = contract.functions.getVeiculosDoCondutor(account.address).call()
# print("Novo valor armazenado:", valor)	


# # Chamar função `get()` (view)
# valor = contract.functions.get().call()
# print("Valor inicial armazenado:", valor)

# signed_tx2 = w3.eth.account.sign_transaction(tx2, private_key)
# #signed_tx2 = Account.sign_transaction(tx2, private_key)
# tx_hash2 = w3.eth.send_raw_transaction(signed_tx2.raw_transaction)
# print("Enviando transação para (registrarVeiculo)...")

# w3.eth.wait_for_transaction_receipt(tx_hash2)
# valor2 = contract.functions.get().call()
# print("Novo valor armazenado:", valor2)	
