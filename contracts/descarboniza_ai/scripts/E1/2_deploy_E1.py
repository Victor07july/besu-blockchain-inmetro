import json
from web3 import Web3
from eth_account import Account

# === 1. Carregar chaves da conta e URL do nó ===
with open("keys.json") as f:
    keys = json.load(f)

rpc_url = keys['besu']['rpcnode']['url']
private_key = "0x60bbe10a196a4e71451c0f6e9ec9beab454c2a5ac0542aa5b8b733ff5719fec3"
account = Account.from_key(private_key)

# === 2. Conectar ao nó Besu ===
w3 = Web3(Web3.HTTPProvider(rpc_url))
assert w3.is_connected(), "Erro: Não conectado ao nó Ethereum"

print("✅ Conectado ao nó Besu")
print(f"👤 Conta deployer: {account.address}")
print(f"💰 Balance: {w3.from_wei(w3.eth.get_balance(account.address), 'ether')} ETH")

# === 3. Carregar ABI e Bytecode do contrato E1 ===
print("\n📄 Carregando contrato E1...")
try:
    with open("../../contracts/E1/CarbonCreditNFT_E1.json") as f:
        contract_json = json.load(f)
        
                # Tentar localizar ABI e bytecode no JSON compilado
        if 'abi' in contract_json and 'bytecode' in contract_json:
            # Formato do Hardhat
            abi = contract_json['abi']
            bytecode = contract_json['bytecode']
            print("✅ Formato Hardhat detectado")
        elif 'contracts' in contract_json:
            # Formato do solc/solcx
            # Encontrar o contrato CarbonCreditNFT_E1
            contract_found = False
            for contract_path, contracts in contract_json['contracts'].items():
                if 'CarbonCreditNFT_E1' in contracts:
                    contract_data = contracts['CarbonCreditNFT_E1']
                    abi = contract_data['abi']
                    # Bytecode está em evm.bytecode.object
                    bytecode = contract_data['evm']['bytecode']['object']
                    print("✅ Formato solcx detectado")
                    contract_found = True
                    break
            
            if not contract_found:
                raise KeyError("Contrato CarbonCreditNFT_E1 não encontrado no JSON")
        else:
            raise KeyError("Formato de JSON não reconhecido")
            
except FileNotFoundError:
    print("❌ Erro: Arquivo CarbonCreditNFT_E1.json não encontrado")
    print("\n🔧 Para compilar o contrato, execute:")
    print("cd ../contracts")
    print("solc --combined-json abi,bin --optimize --base-path . @openzeppelin/=$(npm root -g)/@openzeppelin/ CarbonCreditNFT_E1.sol > CarbonCreditNFT_E1.json")
    exit(1)

# === 4. Criar contrato ===
print("📝 Preparando deploy do CarbonCreditNFT_E1...")
Contract = w3.eth.contract(abi=abi, bytecode=bytecode)

# === 5. Construir transação de deploy ===
print("🚀 Fazendo deploy do contrato...")

# O construtor não recebe parâmetros
construct_txn = Contract.constructor().build_transaction({
    'from': account.address,
    'nonce': w3.eth.get_transaction_count(account.address),
    'gas': 5000000,  # Gas suficiente para deploy com OpenZeppelin
    'gasPrice': w3.eth.gas_price,
})

# === 6. Assinar e enviar transação ===
signed_txn = w3.eth.account.sign_transaction(construct_txn, private_key)
tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)

print(f"⏳ Aguardando confirmação...")
print(f"   Transaction hash: {tx_hash.hex()}")

# === 7. Aguardar confirmação ===
tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

if tx_receipt['status'] == 1:
    contract_address = tx_receipt['contractAddress']
    print("\n✅ Contrato E1 deployado com sucesso!")
    print(f"📍 Endereço: {contract_address}")
    print(f"⛽ Gas usado: {tx_receipt['gasUsed']}")
    
    # === 8. Salvar endereço do contrato ===
    with open("contract_address_E1.txt", "w") as f:
        f.write(contract_address)
    print(f"💾 Endereço salvo em contract_address_E1.txt")
    
    # === 9. Verificar dados do contrato ===
    deployed_contract = w3.eth.contract(address=contract_address, abi=abi)
    
    print("\n📊 Informações do contrato:")
    print(f"   Nome: {deployed_contract.functions.name().call()}")
    print(f"   Símbolo: {deployed_contract.functions.symbol().call()}")
    print(f"   Owner: {deployed_contract.functions.owner().call()}")
    print(f"   Next Token ID: {deployed_contract.functions.nextTokenId().call()}")
    print(f"   Conta autorizada: {deployed_contract.functions.authorized(account.address).call()}")
    
    print("\n🎉 Deploy concluído! Você pode agora:")
    print("   1. Executar o script de envio de dados: python3 4_send_data_E1.py")
    print("   2. Interagir com o contrato através do endereço:", contract_address)
    
else:
    print("❌ Erro no deploy do contrato")
    print(f"   Status: {tx_receipt['status']}")
