import json
from web3 import Web3
from solcx import compile_standard, install_solc
import os
from dotenv import load_dotenv
from web3.middleware import ExtraDataToPOAMiddleware

load_dotenv()


with open("../contracts/SimpleStorage.sol", "r") as file:
    simple_storage_file = file.read()

# We add these two lines that we forgot from the video!
# print("Installing...")
# install_solc("0.6.0")

# Solidity source code
compiled_sol = compile_standard(
    {
        "language": "Solidity",
        "sources": {"SimpleStorage.sol": {"content": simple_storage_file}},
        "settings": {
            "outputSelection": {
                "*": {
                    "*": ["abi", "metadata", "evm.bytecode", "evm.bytecode.sourceMap"]
                }
            }
        },
    },
    solc_version="0.8.20",
)

with open("compiled_code.json", "w") as file:
    json.dump(compiled_sol, file)

# get bytecode
bytecode = compiled_sol["contracts"]["SimpleStorage.sol"]["SimpleStorage"]["evm"][
    "bytecode"
]["object"]

# get abi
abi = json.loads(
    compiled_sol["contracts"]["SimpleStorage.sol"]["SimpleStorage"]["metadata"]
)["output"]["abi"]

# Load Besu network configuration
with open("keys.json") as f:
    keys = json.load(f)

# Connect to Besu network
rpc_url = keys['besu']['rpcnode']['url']
w3 = Web3(Web3.HTTPProvider(rpc_url))
chain_id = 1337  # Besu private network chain ID

# Add PoA middleware for private networks
w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
print(f"Connected to: {w3.client_version}")
print(f"Is connected: {w3.is_connected()}")

# Use the correct account from keys.json
my_address = "0x" + keys['besu']['rpcnode']['accountAddress']
private_key = keys['besu']['rpcnode']['accountPrivateKey']

# Create the contract in Python
SimpleStorage = w3.eth.contract(abi=abi, bytecode=bytecode)
# Get the latest transaction
nonce = w3.eth.get_transaction_count(my_address)

print(f"Account balance: {w3.eth.get_balance(my_address)} wei")
print(f"Current nonce: {nonce}")

# Submit the transaction that deploys the contract - specify gas manually
transaction = SimpleStorage.constructor().build_transaction(
    {
        "chainId": chain_id,
        "gasPrice": w3.eth.gas_price,
        "from": my_address,
        "nonce": nonce,
        "gas": 500000,  # Specify gas manually to avoid estimation
    }
)
# Sign the transaction
signed_txn = w3.eth.account.sign_transaction(transaction, private_key=private_key)
print("Deploying Contract!")
# Send it!
tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
# Wait for the transaction to be mined, and get the transaction receipt
print("Waiting for transaction to finish...")
tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
print(f"Done! Contract deployed to {tx_receipt.contractAddress}")


# Working with deployed Contracts
simple_storage = w3.eth.contract(address=tx_receipt.contractAddress, abi=abi)
print(f"Initial Stored Value {simple_storage.functions.retrieve().call()}")
greeting_transaction = simple_storage.functions.store(15).build_transaction(
    {
        "chainId": chain_id,
        "gasPrice": w3.eth.gas_price,
        "from": my_address,
        "nonce": nonce + 1,
        "gas": 100000,  # Specify gas manually
    }
)
signed_greeting_txn = w3.eth.account.sign_transaction(
    greeting_transaction, private_key=private_key
)
tx_greeting_hash = w3.eth.send_raw_transaction(signed_greeting_txn.rawTransaction)
print("Updating stored Value...")
tx_receipt = w3.eth.wait_for_transaction_receipt(tx_greeting_hash)

print(simple_storage.functions.retrieve().call())