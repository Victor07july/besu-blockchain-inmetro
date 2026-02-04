# 🎯 Scripts E1 - Resumo de Arquivos Criados

## 📁 Estrutura de Arquivos

```
dapps/monetiza_co2/scripts/E1/
├── 1_compile_E1.sh          # Script bash para compilar contrato
├── 2_deploy_E1.py           # Script Python para deploy
├── 3_test_first_E1.py       # Script de teste com primeiro registro
├── 4_send_data_E1.py        # Script completo para processar CSV
├── keys.json                # Configuração do nó RPC
├── README.md                # Documentação completa
└── data/
    └── dados_gas.csv        # CSV com dados de viagens (já existe)
```

## 🚀 Ordem de Execução

### 1️⃣ Compilação
```bash
cd /home/inmetro/besu-quickstarter-modified/dapps/monetiza_co2/scripts/E1
./1_compile_E1.sh
```
**Output**: `../contracts/CarbonCreditNFT_E1.json`

### 2️⃣ Deploy
```bash
python3 2_deploy_E1.py
```
**Output**: `contract_address_E1.txt`

### 3️⃣ Teste (Opcional)
```bash
python3 3_test_first_E1.py
```
**Output**: Testa com primeiro registro e compara Python vs Solidity

### 4️⃣ Processamento Completo
```bash
python3 4_send_data_E1.py
```
**Output**: Cria NFTs para todos os registros do CSV

## 📄 Descrição dos Scripts

### `1_compile_E1.sh`
- **Função**: Compila o contrato Solidity
- **Requer**: solc, OpenZeppelin
- **Gera**: ABI e bytecode em JSON
- **Duracao**: ~5 segundos

### `2_deploy_E1.py`
- **Função**: Faz deploy do contrato na rede Besu
- **Requer**: Web3, contrato compilado, Besu rodando
- **Gera**: Endereço do contrato
- **Gas**: ~5M gas
- **Duracao**: ~10-15 segundos

### `3_test_first_E1.py`
- **Função**: Testa cálculo E1 com primeiro registro
- **Requer**: Contrato deployado, CSV
- **Compara**: Resultados Python vs Solidity
- **Gas**: ~500k gas por NFT
- **Duracao**: ~5-10 segundos

### `4_send_data_E1.py`
- **Função**: Processa todos os registros do CSV
- **Requer**: Contrato deployado, CSV
- **Cria**: Um NFT por viagem
- **Gas**: ~500k gas × número de registros
- **Duracao**: ~5-10 segundos por registro

## 🔧 Configurações Importantes

### Private Key
Todos os scripts Python usam:
```python
private_key = "0x60bbe10a196a4e71451c0f6e9ec9beab454c2a5ac0542aa5b8b733ff5719fec3"
```
⚠️ **Altere para sua chave privada antes de usar em produção!**

### RPC URL
Configurado em `keys.json`:
```json
{
  "besu": {
    "rpcnode": {
      "url": "http://localhost:8545"
    }
  }
}
```

### Preço do Carbono
Definido em `4_send_data_E1.py` e `3_test_first_E1.py`:
```python
CARBON_PRICE_PER_TON = 450.0  # BRL por tonelada
```
Altere conforme necessário.

### Constantes de Emissão
```python
EMISSAO_GASOLINA = 1.720  # kg CO2/L
EMISSAO_ETANOL = 1.510    # kg CO2/L
```
Mesmas constantes usadas no contrato Solidity.

## 📊 Dados do CSV

### Colunas Necessárias
- `VIN`: Identificador único do veículo
- `model`: Modelo do veículo
- `brand`: Marca do veículo
- `total_distance`: Distância total (km)
- `highway (distance)`: Distância em rodovia (km)
- `city (distance)`: Distância em cidade (km)
- `ethanol (%)`: Percentual de etanol no tanque
- `co2_etanol_original_gas_1720_flex`: Emissões reais medidas (gramas)

### Arrays de Eficiência
Os scripts incluem arrays pré-definidos com 33 valores cada:
- `city_gasoline_array`: Consumo cidade gasolina (km/L)
- `road_gasoline_array`: Consumo rodovia gasolina (km/L)
- `city_ethanol_array`: Consumo cidade etanol (km/L)
- `road_ethanol_array`: Consumo rodovia etanol (km/L)

**Importante**: Se o CSV tiver mais/menos registros, ajuste os arrays.

## 🧮 Cálculo E1

### Fluxo
1. **Input**: Distâncias, consumos, % etanol, emissões reais
2. **Cálculo Meta CO2**: Baseado em consumo teórico
3. **Diff**: Economia = Meta - Real (se positivo)
4. **E1 Value**: Monetização = Diff × Preço Carbono / 1M

### Precisão
- **Solidity**: Ponto fixo com 1e6 (6 decimais)
- **Python**: Float de precisão dupla
- **Diferença esperada**: < 0.01% devido a arredondamento

## 🎨 NFT Gerado

Cada NFT contém:
```solidity
struct CalculationResult {
    uint256 tanqueGasoline;   // % gasolina no tanque
    uint256 parte1;           // Emissões rodovia (g)
    uint256 parte2;           // Emissões cidade (g)
    uint256 metaCO2;          // Meta total CO2 (g)
    uint256 diff;             // Economia CO2 (g)
    uint256 e1Value;          // Valor BRL
    uint256 totalDistance;    // Distância total (km)
}
```

## 🔍 Verificação

### Consultar NFT
```python
details = contract.functions.getCalculationDetails(token_id).call()
e1_value = details[5] / 1_000_000  # Converter de 1e6 para BRL
```

### Batch Query
```python
token_ids = [1, 2, 3, 4, 5]
results = contract.functions.getBatchCalculations(token_ids).call()
```

### Total de NFTs
```python
balance = contract.functions.balanceOf(address).call()
```

## ⚠️ Troubleshooting

### "solc não encontrado"
```bash
sudo apt-get install solc
```

### "OpenZeppelin não encontrado"
```bash
npm install -g @openzeppelin/contracts
```

### "Não conectado ao nó"
```bash
# Verificar se Besu está rodando
curl -X POST --data '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}' http://localhost:8545
```

### "insufficient funds"
```bash
# Verificar balance
python3 -c "from web3 import Web3; w3=Web3(Web3.HTTPProvider('http://localhost:8545')); print(w3.from_wei(w3.eth.get_balance('0xSUA_CONTA'), 'ether'), 'ETH')"
```

### Diferença Python vs Solidity > 1%
- Verifique arrays de eficiência
- Verifique se CSV tem valores corretos
- Verifique se constantes estão iguais

## 📝 Arquivos Gerados

Após execução:
- `contract_address_E1.txt`: Endereço do contrato deployado
- `../contracts/CarbonCreditNFT_E1.json`: ABI e bytecode compilados

## 🎯 Próximos Passos

1. ✅ Scripts criados e documentados
2. ⏭️ Compilar contrato: `./1_compile_E1.sh`
3. ⏭️ Fazer deploy: `python3 2_deploy_E1.py`
4. ⏭️ Testar: `python3 3_test_first_E1.py`
5. ⏭️ Processar tudo: `python3 4_send_data_E1.py`

## 📚 Documentação Adicional

- **README.md**: Documentação completa e detalhada
- **Contrato E1**: `../../contracts/E1/CarbonCreditNFT_E1.sol`
- **Código Python referência**: `../../contracts/E1/carbonCreditE1.py`
- **Documentação técnica**: `../../contracts/E1/README_E1_E2.md`

---

**Criado em**: 2025-04-01  
**Versão**: 1.0  
**Adaptado de**: 4_send_data.py (script E2)
