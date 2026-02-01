import json
from web3 import Web3
from eth_account import Account

# === 1. Carregar configurações ===
with open("keys.json") as f:
    keys = json.load(f)

rpc_url = keys['besu']['rpcnode']['url']
private_key = "0x60bbe10a196a4e71451c0f6e9ec9beab454c2a5ac0542aa5b8b733ff5719fec3"
account = Account.from_key(private_key)

# === 2. Conectar ao nó ===
w3 = Web3(Web3.HTTPProvider(rpc_url))
assert w3.is_connected(), "Erro: Não conectado ao nó Ethereum"

print("✅ Conectado ao nó Besu")
print(f"👤 Conta: {account.address}")

# === 3. Carregar contrato ===
try:
    with open("contract_address_E1.txt") as f:
        contract_address = f.read().strip()
    print(f"📄 Contrato E1: {contract_address}")
except FileNotFoundError:
    print("❌ Erro: contract_address_E1.txt não encontrado")
    exit(1)

try:
    with open("../contracts/CarbonCreditNFT_E1.json") as f:
        contract_json = json.load(f)
        if 'abi' in contract_json:
            abi = contract_json['abi']
        elif 'contracts' in contract_json:
            contract_key = list(contract_json['contracts'].keys())[0]
            contract_name = 'CarbonCreditNFT_E1'
            abi = contract_json['contracts'][contract_key][contract_name]['abi']
        else:
            raise KeyError("Formato de ABI não reconhecido")
except FileNotFoundError:
    print("❌ Erro: CarbonCreditNFT_E1.json não encontrado")
    exit(1)

contract = w3.eth.contract(address=contract_address, abi=abi)

# === 4. Consultar informações gerais ===
print(f"\n{'='*70}")
print("📊 INFORMAÇÕES DO CONTRATO E1")
print(f"{'='*70}")

print(f"\n📝 Dados Gerais:")
print(f"   Nome: {contract.functions.name().call()}")
print(f"   Símbolo: {contract.functions.symbol().call()}")
print(f"   Owner: {contract.functions.owner().call()}")
print(f"   Next Token ID: {contract.functions.nextTokenId().call()}")

# === 5. Consultar NFTs da conta ===
balance = contract.functions.balanceOf(account.address).call()
print(f"\n🎨 NFTs da conta:")
print(f"   Total: {balance} NFTs")

if balance == 0:
    print("\n⚠️  Nenhum NFT encontrado para esta conta")
    print("   Execute: python3 4_send_data_E1.py")
    exit(0)

# === 6. Listar todos os NFTs ===
print(f"\n{'='*70}")
print(f"📋 LISTA DE TODOS OS NFTs ({balance} total)")
print(f"{'='*70}")

total_e1_value = 0
total_co2_saved = 0
total_distance = 0

print(f"\n{'ID':<5} {'E1 Value':<12} {'Meta CO2':<12} {'Economia':<12} {'Distância':<10}")
print(f"{'-'*70}")

for i in range(balance):
    try:
        token_id = contract.functions.tokenOfOwnerByIndex(account.address, i).call()
        details = contract.functions.getCalculationDetails(token_id).call()
        
        # Extrair valores (todos em 1e6)
        e1_value = details[5] / 1_000_000
        meta_co2 = details[3] / 1_000_000
        diff = details[4] / 1_000_000
        distance = details[6] / 1_000_000
        
        # Acumular totais
        total_e1_value += e1_value
        total_co2_saved += diff
        total_distance += distance
        
        print(f"{token_id:<5} R$ {e1_value:>8.4f}  {meta_co2:>10.2f}g  {diff:>10.2f}g  {distance:>8.2f}km")
        
    except Exception as e:
        print(f"❌ Erro ao consultar token {i}: {str(e)}")

# === 7. Estatísticas ===
print(f"\n{'='*70}")
print("📈 ESTATÍSTICAS GERAIS")
print(f"{'='*70}")

print(f"\n💰 Valor Total E1: R$ {total_e1_value:.4f}")
print(f"🌱 CO2 Total Economizado: {total_co2_saved:.2f} g ({total_co2_saved/1000:.4f} kg)")
print(f"📏 Distância Total: {total_distance:.2f} km")

if balance > 0:
    avg_e1 = total_e1_value / balance
    avg_co2 = total_co2_saved / balance
    avg_dist = total_distance / balance
    
    print(f"\n📊 Médias por Viagem:")
    print(f"   E1 médio: R$ {avg_e1:.4f}")
    print(f"   CO2 economizado médio: {avg_co2:.2f} g")
    print(f"   Distância média: {avg_dist:.2f} km")
    
    if total_distance > 0:
        co2_per_km = total_co2_saved / total_distance
        print(f"\n🎯 Eficiência:")
        print(f"   CO2 economizado por km: {co2_per_km:.2f} g/km")

# === 8. Detalhes de NFTs específicos (últimos 5) ===
if balance > 0:
    num_to_show = min(5, balance)
    print(f"\n{'='*70}")
    print(f"🔍 DETALHES DOS ÚLTIMOS {num_to_show} NFTs")
    print(f"{'='*70}")
    
    for i in range(balance - num_to_show, balance):
        token_id = contract.functions.tokenOfOwnerByIndex(account.address, i).call()
        details = contract.functions.getCalculationDetails(token_id).call()
        
        print(f"\n🎨 Token #{token_id}")
        print(f"   {'─'*66}")
        print(f"   Tanque Gasolina:  {details[0] / 1_000_000:>10.2f}%")
        print(f"   Parte 1 (rodovia): {details[1] / 1_000_000:>10.2f} g CO2")
        print(f"   Parte 2 (cidade):  {details[2] / 1_000_000:>10.2f} g CO2")
        print(f"   Meta CO2:          {details[3] / 1_000_000:>10.2f} g")
        print(f"   Economia CO2:      {details[4] / 1_000_000:>10.2f} g")
        print(f"   💰 Valor E1:       R$ {details[5] / 1_000_000:>7.4f}")
        print(f"   📏 Distância:      {details[6] / 1_000_000:>10.2f} km")

# === 9. Opções de exportação ===
print(f"\n{'='*70}")
print("📤 OPÇÕES DE EXPORTAÇÃO")
print(f"{'='*70}")

print("\n💡 Para exportar dados para CSV:")
print("   import csv")
print("   # ... (código de consulta dos tokens)")
print("   with open('nfts_e1.csv', 'w') as f:")
print("       writer = csv.writer(f)")
print("       writer.writerow(['Token ID', 'E1 Value', 'Meta CO2', 'Economia', 'Distância'])")
print("       # ... escrever dados")

print("\n💡 Para transferir NFT:")
print("   # token_id = 1")
print("   # to_address = '0x...'")
print("   # contract.functions.transferFrom(account.address, to_address, token_id).transact()")

print("\n💡 Para consultar por token ID específico:")
print("   python3 -c \"import json; from web3 import Web3;")
print("   w3=Web3(Web3.HTTPProvider('http://localhost:8545'));")
print("   # ... carregar contrato")
print("   print(contract.functions.getCalculationDetails(TOKEN_ID).call())\"")

print(f"\n{'='*70}")
print("✅ Consulta concluída!")
print(f"{'='*70}")
