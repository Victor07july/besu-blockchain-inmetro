import json
import csv
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
print(f"👤 Conta: {account.address}")

# === 3. Carregar endereço do contrato ===
try:
    with open("contract_address.txt") as f:
        contract_address = f.read().strip()
    print(f"📄 Contrato E2: {contract_address}")
except FileNotFoundError:
    print("❌ Erro: Arquivo contract_address.txt não encontrado")
    print("Execute o deploy primeiro: python3 2_deploy.py")
    exit(1)

# === 4. Carregar ABI do contrato ===
with open("../contracts/CarbonCreditNFT_E2.json") as f:
    contract_json = json.load(f)
    abi = contract_json['contracts']['../contracts/CarbonCreditNFT_E2.sol']['CarbonCreditNFT_E2Calculator']["abi"]

# === 5. Criar instância do contrato ===
contract = w3.eth.contract(address=contract_address, abi=abi)

# === 6. Verificar se a conta está autorizada ===
is_authorized = contract.functions.authorized(account.address).call()
print(f"🔐 Conta autorizada: {is_authorized}")

if not is_authorized:
    print("⚠️ Conta não autorizada. Tentando autorizar...")
    # Como você é o owner (deployou o contrato), pode se autorizar
    tx_auth = contract.functions.setAuthorized(account.address, True).build_transaction({
        'from': account.address,
        'nonce': w3.eth.get_transaction_count(account.address),
        'gas': 100000,
        'gasPrice': w3.eth.gas_price,
    })
    signed_tx_auth = w3.eth.account.sign_transaction(tx_auth, private_key)
    tx_hash_auth = w3.eth.send_raw_transaction(signed_tx_auth.raw_transaction)
    w3.eth.wait_for_transaction_receipt(tx_hash_auth)
    print("✅ Conta autorizada com sucesso!")

# === 7. Ler dados do CSV ===
print("\n📊 Lendo dados do CSV...")
csv_path = "data/dados_gas.csv"

# Constantes para conversão (mesmas do código Python)
MJ_kWh = 0.2778
gasoline_MJ = 29.5
etanol_MJ = 21.3
PRECO_TARIFA_CONVENCIONAL = 0.774  # R$ por kWh

try:
    with open(csv_path, 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        data = list(reader)
    
    print(f"✅ {len(data)} registros encontrados no CSV")
    
except FileNotFoundError:
    print(f"❌ Erro: Arquivo {csv_path} não encontrado")
    exit(1)

# === 8. Criar mapeamento de eficiências por modelo (igual ao código Python) ===
# Passo 2 do Python: Imputando manualmente a eficiência de cada automóvel
city_gasoline_array = [10.3, 10.3, 10.3, 10.3, 12.15, 12.15, 12.15, 12.15, 12.6, 12.6, 12.6, 12.6, 11.8, 12.83, 12.83, 12.83, 12.83, 11.6, 11.6, 11.6, 11.6, 11.6, 11.6, 11.6, 11.6, 11.6, 11.6, 11.6, 11.6, 11.6, 11.6, 12.0, 12.0]
road_gasoline_array = [11.3, 11.3, 11.3, 11.3, 13.65, 13.65, 13.65, 13.65, 13.9, 13.9, 13.9, 13.9, 13.3, 14.44, 14.44, 14.44, 14.44, 14.1, 14.1, 14.1, 14.1, 14.1, 14.1, 14.1, 14.1, 14.1, 14.1, 14.1, 14.1, 14.1, 14.1, 14.4, 14.4]
city_ethanol_array  = [0, 0, 0, 0, 8.2, 8.2, 8.2, 8.2, 8.9, 8.9, 8.9, 8.9, 8.1, 9.11, 9.11, 9.11, 9.11, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8.3, 8.3]
road_ethanol_array  = [0, 0, 0, 0, 9.5, 9.5, 9.5, 9.5, 9.8, 9.8, 9.8, 9.8, 9.2, 10.26, 10.26, 10.26, 10.26, 9.8, 9.8, 9.8, 9.8, 9.8, 9.8, 9.8, 9.8, 9.8, 9.8, 9.8, 9.8, 9.8, 9.8, 10.0, 10.0]

print(f"✅ Arrays de eficiência criados (baseado no código Python)")
print(f"   - Total de registros: {len(data)}")
print(f"   - Total de eficiências: {len(city_gasoline_array)}")

if len(data) != len(city_gasoline_array):
    print(f"⚠️  AVISO: Número de registros ({len(data)}) diferente do número de eficiências ({len(city_gasoline_array)})")
    print(f"   Usando valores padrão para registros extras")

# === 9. Processar e enviar cada linha do CSV ===
print("\n🚀 Iniciando processamento...\n")
print("💡 Dica: Para testar apenas o primeiro registro, pressione Ctrl+C após ver os cálculos\n")

success_count = 0
error_count = 0

# for idx, row in enumerate(data, 1):
#     try:

row = data[0]

# print(f"📝 Processando registro {idx}/{len(data)}:")
print(f"   VIN: {row['VIN']}")
print(f"   Modelo: {row['model']} ({row['brand']})")
print(f"   Distância total: {row['total_distance']} km")

# Ler valores do CSV
ethanol_percent = float(row['ethanol (%)'])
highway_distance = float(row['highway (distance)'])
city_distance = float(row['city (distance)'])

# === CRIAR COLUNAS MANUALMENTE (igual ao código Python) ===
# Passo 2: Imputando eficiências do array baseado no índice
# array_idx = idx - 1  # idx começa em 1, array em 0

array_idx = 0

if array_idx < len(city_gasoline_array):
    city_gasoline = city_gasoline_array[array_idx] if city_gasoline_array[array_idx] != 0 else 10.3
    road_gasoline = road_gasoline_array[array_idx] if road_gasoline_array[array_idx] != 0 else 11.3
    city_ethanol = city_ethanol_array[array_idx] if city_ethanol_array[array_idx] != 0 else 8.0
    road_ethanol = road_ethanol_array[array_idx] if road_ethanol_array[array_idx] != 0 else 9.5
else:
    # Valores padrão se não houver no array
    city_gasoline = 10.3
    road_gasoline = 11.3
    city_ethanol = 8.0
    road_ethanol = 9.5

# Passo 4: preco_tarifa_convencional (constante)
preco_tarifa_convencional = PRECO_TARIFA_CONVENCIONAL  # 0.774 R$/kWh

# Comportamento
behavior_cautious = float(row['behavior_cautious (%)'])
behavior_normal = float(row['behavior_normal (%)'])
behavior_aggressive = float(row['behavior_aggressive (%)'])

# === CÁLCULOS PYTHON (igual ao CarbonCreditNFT_e2.py) ===

# PASSO 1: Tanque de gasolina (%)
# df["Tanque_gasoline"] = 100 - df["ethanol (%)"]
tanque_gasoline = 100 - ethanol_percent

# Mostrar colunas criadas
print(f"\n   📋 COLUNAS CRIADAS (não estão no CSV):")
print(f"      city_gasoline:    {city_gasoline:.2f} km/L")
print(f"      road_gasoline:    {road_gasoline:.2f} km/L")
print(f"      city_ethanol:     {city_ethanol:.2f} km/L")
print(f"      road_ethanol:     {road_ethanol:.2f} km/L")
print(f"      preco_tarifa:     R$ {preco_tarifa_convencional:.3f}/kWh")
print(f"      Tanque_gasoline:  {tanque_gasoline:.2f}%")

# PASSO 2: Conversões de energia para preço (R$/km)
# df["convert_gasoline"] = (MJ_kWh * gasoline_MJ * preco_tarifa * (Tanque_gasoline / 100))
convert_gasoline = (MJ_kWh * gasoline_MJ * PRECO_TARIFA_CONVENCIONAL * (tanque_gasoline / 100.0))

# df["convert_etanol"] = (MJ_kWh * etanol_MJ * preco_tarifa * (1 - Tanque_gasoline / 100))
convert_etanol = (MJ_kWh * etanol_MJ * PRECO_TARIFA_CONVENCIONAL * (1 - (tanque_gasoline / 100.0)))

# PASSO 3: Valores Estrada (R$)
# Custo por km de cada combustível na estrada
custo_km_estrada_gasolina = (convert_gasoline / road_gasoline) if road_gasoline > 0 else 0
custo_km_estrada_etanol = (convert_etanol / road_ethanol) if road_ethanol > 0 else 0

# df["Valores_estrada"] = ((convert_gasoline/road_gasoline) + (convert_etanol/road_ethanol)) * highway_distance
valores_estrada = (custo_km_estrada_gasolina + custo_km_estrada_etanol) * highway_distance

# PASSO 4: Valores Cidade (R$) - usar city_distance e city_*
# Custo por km de cada combustível na cidade
custo_km_cidade_gasolina = (convert_gasoline / city_gasoline) if city_gasoline > 0 else 0
custo_km_cidade_etanol = (convert_etanol / city_ethanol) if city_ethanol > 0 else 0

# df["Valores_cidade"] = ((convert_gasoline/city_gasoline) + (convert_etanol/city_ethanol)) * city_distance
valores_cidade = (custo_km_cidade_gasolina + custo_km_cidade_etanol) * city_distance

# PASSO 5: Prop_Bonus (bônus de comportamento)
# df["Prop_Bonus"] = (cautious/100)*0.05 + (normal/100)*0.02 + (aggressive/100)*0.005
prop_bonus = (
    (behavior_cautious / 100.0) * 0.05 +
    (behavior_normal / 100.0) * 0.02 +
    (behavior_aggressive / 100.0) * 0.005
)

# PASSO 6: E2 Final (R$)
# df["E2"] = df["Prop_Bonus"] * (df["Valores_estrada"] + df["Valores_cidade"])
# e2_python = prop_bonus * (valores_estrada + valores_cidade)

# Mostrar detalhes dos cálculos
# print(f"   � CÁLCULOS PYTHON (passo a passo):")
# print(f"      1. Tanque Gasolina: {tanque_gasoline:.2f}%")
# print(f"      2. Convert Gasoline: R$ {convert_gasoline:.6f}/km")
# print(f"      3. Convert Etanol: R$ {convert_etanol:.6f}/km")
# print(f"      4. Custo km Estrada (Gas): R$ {custo_km_estrada_gasolina:.6f}")
# print(f"      5. Custo km Estrada (Eta): R$ {custo_km_estrada_etanol:.6f}")
# print(f"      6. Valores Estrada: R$ {valores_estrada:.6f}")
# print(f"      7. Custo km Cidade (Gas): R$ {custo_km_cidade_gasolina:.6f}")
# print(f"      8. Custo km Cidade (Eta): R$ {custo_km_cidade_etanol:.6f}")
# print(f"      9. Valores Cidade: R$ {valores_cidade:.6f}")
# print(f"     10. Prop Bonus: {prop_bonus:.6f}")
# print(f"   💰 E2 Final (Python): R$ {e2_python:.6f}")

# === CONVERTER PARA FORMATO SOLIDITY (multiplicar por 1e6) ===
# Nota: precoGasolina e precoEtanol não são usados no novo cálculo
# O contrato usa constantes de conversão de energia (MJ -> kWh)
params = {
    'highwayDistance': int(highway_distance * 1_000_000),
    'cityDistance': int(city_distance * 1_000_000),
    'ethanolPercent': int(ethanol_percent * 1_000_000),
    'roadGasoline': int(road_gasoline * 1_000_000),
    'roadEthanol': int(road_ethanol * 1_000_000),
    'cityGasoline': int(city_gasoline * 1_000_000),
    'cityEthanol': int(city_ethanol * 1_000_000),
    'precoGasolina': 0,  # Não usado no novo cálculo
    'precoEtanol': 0,     # Não usado no novo cálculo
    'behaviorCautious': int(behavior_cautious * 1_000_000),
    'behaviorNormal': int(behavior_normal * 1_000_000),
    'behaviorAggressive': int(behavior_aggressive * 1_000_000)
}

# Construir transação para tokenização
tx = contract.functions.calculateE2AndTokenize(
    tuple(params.values()),
    account.address
).build_transaction({
    'from': account.address,
    'nonce': w3.eth.get_transaction_count(account.address),
    'gas': 500000,  # Gas suficiente para criar NFT
    'gasPrice': w3.eth.gas_price,
})

# Assinar e enviar
signed_tx = w3.eth.account.sign_transaction(tx, private_key)
tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)

print(f"   🔄 Aguardando confirmação... (tx: {tx_hash.hex()[:10]}...)")

# Aguardar confirmação
receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

if receipt['status'] == 1:
    print(f"   ✅ NFT criado com sucesso!")
    success_count += 1
else:
    print(f"   ❌ Transação falhou")
    error_count += 1

print()
        
    # except Exception as e:
    #     print(f"   ❌ Erro ao processar registro: {str(e)}")
    #     error_count += 1
    #     print()
    #     continue

# === 9. Resumo final ===
print("\n" + "="*60)
print("📊 RESUMO DO PROCESSAMENTO")
print("="*60)
print(f"✅ Sucessos: {success_count}")
print(f"❌ Erros: {error_count}")
print(f"📝 Total processado: {len(data)}")
print()

# Verificar quantos NFTs a conta possui agora
balance = contract.functions.balanceOf(account.address).call()
print(f"🎨 Total de NFTs na conta: {balance}")

# Mostrar alguns detalhes dos NFTs criados
if balance > 0:
    print(f"\n📋 Últimos 5 NFTs criados:")
    for i in range(max(0, balance - 5), balance):
        token_id = contract.functions.tokenOfOwnerByIndex(account.address, i).call()
        details = contract.functions.getCalculationDetails(token_id).call()
        e2_value = details[8] / 1_000_000  # e2Final
        total_distance = details[9] / 1_000_000  # totalDistance
        print(f"   Token {token_id}: E2=R$ {e2_value}, Distância={total_distance:.2f} km")

print("\n🎉 Processamento concluído!")	

'''
DEVIDO A ARREDONDAMENTO DO SOLIDITY, HAVERÁ DIFERENÇA DE ALGUMAS FRAÇÕES DE CENTAVOS NOS RESULTADO
'''