import json
from web3 import Web3
from eth_account import Account

# === 1. Carregar chaves da conta e URL do nó ===
with open("keys.json") as f:
    keys = json.load(f)

rpc_url = keys['besu']['rpcnode']['url']

# Conectar ao nó Besu primeiro
w3 = Web3(Web3.HTTPProvider(rpc_url))

# Usar conta com saldo (account_a) em vez da conta sem saldo
account_address = w3.to_checksum_address(keys['accounts']['a']['address'])
private_key = keys['accounts']['a']['privateKey']

print(f"Conectado: {w3.is_connected()}")
print(f"Usando conta: {account_address}")
print(f"Saldo: {w3.from_wei(w3.eth.get_balance(account_address), 'ether')} ETH")

# Endereço do contrato - DEVE SER ATUALIZADO para o contrato correto
contract_address = "0x9A8ea6736DF00Af70D1cD70b1Daf3619C8c0D7F4"

# Carregar ABI do contrato
with open("../contracts/CarbonCredit.json") as f:
    contract_json = json.load(f)
    abi = contract_json['contracts']['../contracts/CarbonCredit.sol']['CarbonCreditNFT_Final']["abi"]

# === 8. Interagir com o contrato ===
contract = w3.eth.contract(address=contract_address, abi=abi)

# Verificar se a conta é o admin do contrato
try:
    admin_address = contract.functions.admin().call()
    print(f"Admin do contrato: {admin_address}")
    print(f"Conta atual é admin: {account_address.lower() == admin_address.lower()}")
except Exception as e:
    print(f"Erro ao verificar admin: {e}")

# Preparar dados para a transação registrarViagemDetalhada
condutor = account_address  # ou outro endereço que receberá o NFT
co2_meta_g = 1000  # Meta de CO2 em gramas
economia_co2 = 500  # Economia de CO2 em gramas  
recompensa_wei = w3.to_wei(0.001, 'ether')  # Recompensa em wei (0.001 ETH)
dados_hash = w3.keccak(text="viagem_teste_001")  # Hash dos dados da viagem

print(f"\n=== PARÂMETROS DA TRANSAÇÃO ===")
print(f"Condutor: {condutor}")
print(f"CO2 Meta (g): {co2_meta_g}")
print(f"Economia CO2 (g): {economia_co2}")
print(f"Recompensa (wei): {recompensa_wei}")
print(f"Dados Hash: {dados_hash.hex()}")

# Construir transação registrarViagemDetalhada
tx = contract.functions.registrarViagemDetalhada(
    condutor,
    co2_meta_g,
    economia_co2,
    recompensa_wei,
    dados_hash
).build_transaction({
    'from': account_address,
    'nonce': w3.eth.get_transaction_count(account_address),
    'gas': 300000,  # Gas suficiente para mint NFT + storage
    'gasPrice': w3.eth.gas_price or 1000000000,  # 1 gwei se gas_price for 0
    'chainId': 1337,
})

print(f"\n=== ENVIANDO TRANSAÇÃO ===")
print(f"Gas limit: {tx['gas']}")
print(f"Gas price: {tx['gasPrice']}")

signed_tx = w3.eth.account.sign_transaction(tx, private_key)
tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
print(f"Hash da transação: {tx_hash.hex()}")

print("Aguardando confirmação...")
receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

print(f"\n=== RESULTADO ===")
print(f"Status: {receipt.status}")
print(f"Gas usado: {receipt.gasUsed}")
print(f"Bloco: {receipt.blockNumber}")

if receipt.status == 1:
    print("✅ Transação bem-sucedida!")
    
    # Buscar eventos da transação
    try:
        viagem_events = contract.events.ViagemRegistrada().process_receipt(receipt)
        if viagem_events:
            event = viagem_events[0]
            token_id = event['args']['tokenId']
            print(f"🎟️  NFT criado com Token ID: {token_id}")
            print(f"Condutor: {event['args']['condutor']}")
            print(f"CO2 Meta: {event['args']['co2MetaG']} g")
            print(f"Economia CO2: {event['args']['economiaCO2']} g")
            print(f"Recompensa: {event['args']['recompensa']} wei")
        else:
            print("⚠️  Evento ViagemRegistrada não encontrado")
    except Exception as e:
        print(f"Erro ao processar eventos: {e}")
        
    # Verificar tokens do condutor
    try:
        tokens = contract.functions.tokensDoCondutor(condutor, 0).call()
        print(f"Primeiro token do condutor: {tokens}")
    except Exception as e:
        print(f"Erro ao verificar tokens: {e}")
        
else:
    print("❌ Transação falhou!")
    print(f"Receipt completo: {receipt}")

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
