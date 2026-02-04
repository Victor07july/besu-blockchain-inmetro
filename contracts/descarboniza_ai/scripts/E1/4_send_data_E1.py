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

# === 3. Carregar endereço do contrato E1 ===
try:
    with open("contract_address_E1.txt") as f:
        contract_address = f.read().strip()
    print(f"📄 Contrato E1: {contract_address}")
except FileNotFoundError:
    print("❌ Erro: Arquivo contract_address_E1.txt não encontrado")
    print("Execute o deploy primeiro: python3 2_deploy_E1.py")
    exit(1)

# === 4. Carregar ABI do contrato E1 ===
try:
    with open("../contracts/CarbonCreditNFT_E1.json") as f:
        contract_json = json.load(f)
        # Tentar localizar a ABI no JSON compilado
        if 'abi' in contract_json:
            abi = contract_json['abi']
        elif 'contracts' in contract_json:
            # Formato do solc
            contract_key = list(contract_json['contracts'].keys())[0]
            contract_name = 'CarbonCreditNFT_E1'
            abi = contract_json['contracts'][contract_key][contract_name]['abi']
        else:
            raise KeyError("Formato de ABI não reconhecido")
except FileNotFoundError:
    print("❌ Erro: Arquivo CarbonCreditNFT_E1.json não encontrado")
    print("Compile o contrato primeiro: solc --combined-json abi,bin ../contracts/CarbonCreditNFT_E1.sol > ../contracts/CarbonCreditNFT_E1.json")
    exit(1)

# === 5. Criar instância do contrato ===
contract = w3.eth.contract(address=contract_address, abi=abi)

# === 6. Verificar se a conta está autorizada ===
is_authorized = contract.functions.authorized(account.address).call()
print(f"🔐 Conta autorizada: {is_authorized}")

if not is_authorized:
    print("⚠️ Conta não autorizada. Tentando autorizar...")
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

# Constantes de emissão (mesmas do código Python e Solidity)
EMISSAO_GASOLINA = 1.720  # kg CO2/L
EMISSAO_ETANOL = 1.510    # kg CO2/L

# Preço do carbono (exemplo: €80/tonelada ~ R$450/tonelada)
CARBON_PRICE_PER_TON = 450.0  # BRL por tonelada

try:
    with open(csv_path, 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        data = list(reader)
    
    print(f"✅ {len(data)} registros encontrados no CSV")
    
except FileNotFoundError:
    print(f"❌ Erro: Arquivo {csv_path} não encontrado")
    exit(1)

# === 8. Criar mapeamento de eficiências por modelo (igual ao código Python) ===
# Consumos em km/L para cada veículo
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
print("\n🚀 Iniciando processamento E1...\n")
print("💡 Para testar apenas o primeiro registro, pressione Ctrl+C após ver os cálculos\n")

success_count = 0
error_count = 0

for idx, row in enumerate(data, 1):
    try:
        print(f"📝 Processando registro {idx}/{len(data)}:")
        print(f"   VIN: {row['VIN']}")
        print(f"   Modelo: {row['model']} ({row['brand']})")
        print(f"   Distância total: {row['total_distance']} km")

        # Ler valores do CSV
        ethanol_percent = float(row['ethanol (%)'])
        highway_distance = float(row['highway (distance)'])
        city_distance = float(row['city (distance)'])
        real_co2_emissions = float(row['co2_etanol_original_gas_1720_flex'])  # Emissões reais medidas

        # === OBTER EFICIÊNCIAS DO ARRAY ===
        array_idx = idx - 1  # idx começa em 1, array em 0

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

        # Mostrar dados de entrada
        print(f"\n   📋 DADOS DE ENTRADA:")
        print(f"      highway_distance:  {highway_distance:.2f} km")
        print(f"      city_distance:     {city_distance:.2f} km")
        print(f"      ethanol_percent:   {ethanol_percent:.2f}%")
        print(f"      road_gasoline:     {road_gasoline:.2f} km/L")
        print(f"      road_ethanol:      {road_ethanol:.2f} km/L")
        print(f"      city_gasoline:     {city_gasoline:.2f} km/L")
        print(f"      city_ethanol:      {city_ethanol:.2f} km/L")
        print(f"      real_co2:          {real_co2_emissions:.2f} g")
        print(f"      carbon_price:      R$ {CARBON_PRICE_PER_TON:.2f}/ton")

        # === CÁLCULO E1 PYTHON (para comparação) ===
        tanque_gasoline = 100 - ethanol_percent
        p_gas = tanque_gasoline / 100.0
        p_etanol = ethanol_percent / 100.0

        # Parte 1: Emissões rodovia (em gramas)
        parte_1_gas = highway_distance * (1/road_gasoline) * p_gas * EMISSAO_GASOLINA * 1000
        parte_1_eta = highway_distance * (1/road_ethanol) * p_etanol * EMISSAO_ETANOL * 1000
        parte1_python = parte_1_gas + parte_1_eta

        # Parte 2: Emissões cidade (em gramas)
        parte_2_gas = city_distance * (1/city_gasoline) * p_gas * EMISSAO_GASOLINA * 1000
        parte_2_eta = city_distance * (1/city_ethanol) * p_etanol * EMISSAO_ETANOL * 1000
        parte2_python = parte_2_gas + parte_2_eta

        # Meta CO2 total
        meta_co2_python = parte1_python + parte2_python

        # Diff (economia)
        diff_python = max(0, meta_co2_python - real_co2_emissions)

        # E1 (valor em BRL)
        e1_python = (diff_python * CARBON_PRICE_PER_TON) / 1_000_000.0

        print(f"\n   🧮 CÁLCULOS PYTHON (referência):")
        print(f"      Tanque Gasolina:   {tanque_gasoline:.2f}%")
        print(f"      Parte 1 (rodovia): {parte1_python:.2f} g CO2")
        print(f"      Parte 2 (cidade):  {parte2_python:.2f} g CO2")
        print(f"      Meta CO2:          {meta_co2_python:.2f} g")
        print(f"      Emissões Reais:    {real_co2_emissions:.2f} g")
        print(f"      Diff (economia):   {diff_python:.2f} g")
        print(f"   💰 E1 Final (Python): R$ {e1_python:.6f}")

        # === CONVERTER PARA FORMATO SOLIDITY (multiplicar por 1e6) ===
        params = {
            'highwayDistance': int(highway_distance * 1_000_000),
            'cityDistance': int(city_distance * 1_000_000),
            'ethanolPercent': int(ethanol_percent * 1_000_000),
            'roadGasoline': int(road_gasoline * 1_000_000),
            'roadEthanol': int(road_ethanol * 1_000_000),
            'cityGasoline': int(city_gasoline * 1_000_000),
            'cityEthanol': int(city_ethanol * 1_000_000),
            'realCO2Emissions': int(real_co2_emissions * 1_000_000),
            'carbonPricePerTon': int(CARBON_PRICE_PER_TON * 1_000_000)
        }

        # Construir transação para tokenização E1
        tx = contract.functions.calculateAndMint(
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
            print(f"   ✅ NFT E1 criado com sucesso!")
            
            # Buscar o tokenId do evento
            # O tokenId é o nextTokenId-1 após a criação
            balance = contract.functions.balanceOf(account.address).call()
            if balance > 0:
                token_id = contract.functions.tokenOfOwnerByIndex(account.address, balance - 1).call()
                print(f"   🎨 Token ID: {token_id}")
                
                # Buscar detalhes do token
                details = contract.functions.getCalculationDetails(token_id).call()
                e1_solidity = details[5] / 1_000_000  # e1Value
                meta_co2_solidity = details[3] / 1_000_000  # metaCO2
                diff_solidity = details[4] / 1_000_000  # diff
                
                print(f"\n   🔗 RESULTADO SOLIDITY:")
                print(f"      Meta CO2:        {meta_co2_solidity:.2f} g")
                print(f"      Diff (economia): {diff_solidity:.2f} g")
                print(f"      E1 Value:        R$ {e1_solidity:.6f}")
                
                # Comparar resultados
                diff_percentage = abs(e1_python - e1_solidity) / e1_python * 100 if e1_python > 0 else 0
                print(f"\n   📊 COMPARAÇÃO:")
                print(f"      Python:   R$ {e1_python:.6f}")
                print(f"      Solidity: R$ {e1_solidity:.6f}")
                print(f"      Diferença: {diff_percentage:.4f}%")
            
            success_count += 1
        else:
            print(f"   ❌ Transação falhou")
            error_count += 1

        print()
        
    except Exception as e:
        print(f"   ❌ Erro ao processar registro: {str(e)}")
        error_count += 1
        print()
        continue

# === 10. Resumo final ===
print("\n" + "="*60)
print("📊 RESUMO DO PROCESSAMENTO E1")
print("="*60)
print(f"✅ Sucessos: {success_count}")
print(f"❌ Erros: {error_count}")
print(f"📝 Total processado: {len(data)}")
print()

# Verificar quantos NFTs a conta possui agora
balance = contract.functions.balanceOf(account.address).call()
print(f"🎨 Total de NFTs E1 na conta: {balance}")

# Mostrar alguns detalhes dos NFTs criados
if balance > 0:
    print(f"\n📋 Últimos 5 NFTs E1 criados:")
    for i in range(max(0, balance - 5), balance):
        token_id = contract.functions.tokenOfOwnerByIndex(account.address, i).call()
        details = contract.functions.getCalculationDetails(token_id).call()
        e1_value = details[5] / 1_000_000  # e1Value
        meta_co2 = details[3] / 1_000_000  # metaCO2
        diff = details[4] / 1_000_000  # diff
        total_distance = details[6] / 1_000_000  # totalDistance
        print(f"   Token {token_id}: E1=R$ {e1_value:.4f}, Meta={meta_co2:.2f}g, Economia={diff:.2f}g, Dist={total_distance:.2f}km")

print("\n🎉 Processamento E1 concluído!")

print("\n" + "="*60)
print("📝 NOTAS IMPORTANTES")
print("="*60)
print("• Devido a arredondamento do Solidity, haverá diferenças mínimas")
print("  entre os resultados Python e Solidity (geralmente < 0.01%)")
print("• O valor E1 representa o crédito de carbono em BRL baseado na")
print("  economia de emissões CO2 comparada com a meta calculada")
print("• Preço do carbono usado: R$ {:.2f}/tonelada".format(CARBON_PRICE_PER_TON))
print("="*60)
