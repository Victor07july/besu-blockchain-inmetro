# Scripts E1 - Carbon Credit NFT

Scripts para compilar, fazer deploy e interagir com o contrato `CarbonCreditNFT_E1.sol` que implementa cálculos de crédito de carbono baseado em emissões de CO2.

## 📋 Pré-requisitos

1. **Solidity Compiler (solc)**
   ```bash
   sudo add-apt-repository ppa:ethereum/ethereum
   sudo apt-get update
   sudo apt-get install solc
   ```

2. **OpenZeppelin Contracts**
   ```bash
   npm install -g @openzeppelin/contracts
   ```

3. **Python 3 e dependências**
   ```bash
   pip3 install web3 eth-account
   ```

4. **Rede Besu rodando**
   - Certifique-se que a rede Besu está ativa
   - URL padrão: http://localhost:8545

5. **Arquivo keys.json**
   - Deve conter as configurações do nó RPC
   - Localização: `scripts/E1/keys.json`
   - Formato:
     ```json
     {
       "besu": {
         "rpcnode": {
           "url": "http://localhost:8545"
         }
       }
     }
     ```

## 🚀 Passo a Passo

### 1. Compilar o Contrato

```bash
cd /home/inmetro/besu-quickstarter-modified/dapps/monetiza_co2/scripts/E1
chmod +x 1_compile_E1.sh
./1_compile_E1.sh
```

**O que faz:**
- Compila `CarbonCreditNFT_E1.sol` com o solc
- Gera ABI e bytecode
- Salva em `../contracts/CarbonCreditNFT_E1.json`

### 2. Deploy do Contrato

```bash
python3 2_deploy_E1.py
```

**O que faz:**
- Conecta ao nó Besu
- Faz deploy do contrato E1
- Salva endereço em `contract_address_E1.txt`
- Exibe informações do contrato deployado

**Saída esperada:**
```
✅ Conectado ao nó Besu
👤 Conta deployer: 0x...
💰 Balance: ... ETH
✅ Contrato E1 deployado com sucesso!
📍 Endereço: 0x...
```

### 3. Enviar Dados do CSV

```bash
python3 4_send_data_E1.py
```

**O que faz:**
- Lê dados de `data/dados_gas.csv`
- Para cada viagem, calcula E1:
  - Meta de emissões CO2 baseada em consumo
  - Economia (diff) entre meta e emissões reais
  - Valor monetário do crédito de carbono
- Cria um NFT para cada viagem
- Compara resultados Python vs Solidity

**Saída esperada:**
```
✅ Conectado ao nó Besu
📄 Contrato E1: 0x...
🔐 Conta autorizada: True
📊 Lendo dados do CSV...
✅ 33 registros encontrados no CSV

📝 Processando registro 1/33:
   🧮 CÁLCULOS PYTHON (referência):
      Meta CO2:          X.XX g
      Diff (economia):   X.XX g
   💰 E1 Final (Python): R$ X.XXXXXX
   
   ✅ NFT E1 criado com sucesso!
   🔗 RESULTADO SOLIDITY:
      E1 Value:        R$ X.XXXXXX
   📊 COMPARAÇÃO:
      Diferença: 0.00XX%
```

## 📊 Estrutura dos Dados

### CSV Input (`data/dados_gas.csv`)

Colunas necessárias:
- `VIN`: Identificador do veículo
- `model`, `brand`: Modelo e marca
- `total_distance`: Distância total (km)
- `highway (distance)`: Distância rodovia (km)
- `city (distance)`: Distância cidade (km)
- `ethanol (%)`: Percentual de etanol no tanque
- `co2_etanol_original_gas_1720_flex`: Emissões reais medidas (gramas)

### Arrays de Eficiência

Os scripts usam arrays pré-definidos com consumo (km/L) para cada veículo:
- `city_gasoline_array`: Consumo cidade com gasolina
- `road_gasoline_array`: Consumo rodovia com gasolina
- `city_ethanol_array`: Consumo cidade com etanol
- `road_ethanol_array`: Consumo rodovia com etanol

## 🧮 Cálculo E1

### Fórmula

1. **Tanque Gasolina**: `100 - ethanol_percent`

2. **Parte 1 (Rodovia)**:
   ```
   parte_1 = (highway_distance / road_gasoline) * p_gas * EMISSAO_GASOLINA * 1000
           + (highway_distance / road_ethanol) * p_etanol * EMISSAO_ETANOL * 1000
   ```

3. **Parte 2 (Cidade)**:
   ```
   parte_2 = (city_distance / city_gasoline) * p_gas * EMISSAO_GASOLINA * 1000
           + (city_distance / city_ethanol) * p_etanol * EMISSAO_ETANOL * 1000
   ```

4. **Meta CO2**: `parte_1 + parte_2` (em gramas)

5. **Diff (Economia)**: `max(0, meta_co2 - real_emissions)` (em gramas)

6. **E1 (Valor)**: `(diff * carbon_price) / 1_000_000` (em BRL)

### Constantes

- `EMISSAO_GASOLINA = 1.720 kg CO2/L = 1720 g/L`
- `EMISSAO_ETANOL = 1.510 kg CO2/L = 1510 g/L`
- `CARBON_PRICE_PER_TON = 450 BRL/ton` (configurável no script)

## 🔍 Verificação de Resultados

### Consultar NFTs

```python
from web3 import Web3

w3 = Web3(Web3.HTTPProvider('http://localhost:8545'))
contract = w3.eth.contract(address='0x...', abi=abi)

# Total de NFTs
balance = contract.functions.balanceOf('0xYOUR_ADDRESS').call()

# Detalhes de um token
token_id = 1
details = contract.functions.getCalculationDetails(token_id).call()

# details retorna:
# [0] tanqueGasoline
# [1] parte1 (rodovia)
# [2] parte2 (cidade)
# [3] metaCO2
# [4] diff (economia)
# [5] e1Value (valor em BRL)
# [6] totalDistance

print(f"E1 Value: R$ {details[5] / 1_000_000:.6f}")
print(f"Economia CO2: {details[4] / 1_000_000:.2f} g")
```

### Batch Query

```python
# Consultar múltiplos tokens de uma vez
token_ids = [1, 2, 3, 4, 5]
results = contract.functions.getBatchCalculations(token_ids).call()

for i, result in enumerate(results):
    print(f"Token {token_ids[i]}: E1 = R$ {result[5] / 1_000_000:.4f}")
```

## ⚙️ Configurações

### Alterar Preço do Carbono

Edite `4_send_data_E1.py`:
```python
# Linha ~25
CARBON_PRICE_PER_TON = 450.0  # BRL por tonelada
```

### Alterar Conta

Edite os scripts:
```python
# Linha ~8
private_key = "0xSUA_CHAVE_PRIVADA"
```

### Alterar Arrays de Eficiência

Se tiver mais veículos ou eficiências diferentes, edite:
```python
# Linhas ~91-94 em 4_send_data_E1.py
city_gasoline_array = [10.3, 10.3, ...]  # Adicione mais valores
```

## 📝 Notas Importantes

1. **Arredondamento**: Haverá diferenças mínimas (< 0.01%) entre cálculos Python e Solidity devido a arredondamento de ponto fixo.

2. **Gas**: Cada NFT criado consome ~500k gas. Certifique-se que há gas suficiente.

3. **Autorização**: A conta que faz deploy é automaticamente autorizada. Para autorizar outras contas:
   ```python
   contract.functions.setAuthorized('0xADDRESS', True).transact()
   ```

4. **Valores Negativos**: Se `real_emissions > meta_co2`, não há economia e `diff = 0`, logo `e1 = 0`.

## 🐛 Troubleshooting

### Erro: "solc não encontrado"
```bash
sudo apt-get install solc
```

### Erro: "OpenZeppelin não encontrado"
```bash
npm install -g @openzeppelin/contracts
```

### Erro: "Não conectado ao nó"
Verifique se o Besu está rodando:
```bash
curl -X POST --data '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}' http://localhost:8545
```

### Erro: "insufficient funds"
Certifique-se que a conta tem ETH:
```python
balance = w3.eth.get_balance('0xYOUR_ADDRESS')
print(f"Balance: {w3.from_wei(balance, 'ether')} ETH")
```

## 📚 Referências

- Contrato Solidity: `../../contracts/E1/CarbonCreditNFT_E1.sol`
- Código Python referência: `../../contracts/E1/carbonCreditE1.py`
- Documentação técnica: `../../contracts/E1/README_E1_E2.md`
- CSV de dados: `data/dados_gas.csv`

## 🎯 Próximos Passos

Após executar os scripts, você pode:
1. Consultar os NFTs criados através do contrato
2. Transferir NFTs para outras contas
3. Integrar com frontend (React, Vue, etc.)
4. Exportar dados para análise
5. Criar dashboards de visualização
