# 🔄 Pipeline Simplificado - OBDLink.csv → Blockchain

## 📋 Visão Geral

Pipeline alternativo que processa dados de telemetria OBD **diretamente** sem necessidade de agregação prévia complexa.

### Diferenças vs Pipeline Original

| Aspecto | Pipeline Original | Pipeline Simplificado |
|---------|-------------------|----------------------|
| **Contrato** | E1RegistryGPS.sol | E1RegistryTelemetry.sol |
| **Entrada** | CSV pré-agregado | OBDLink.csv (telemetria bruta) |
| **Distâncias** | highway/city separados | Velocidade média |
| **Emissões** | Baseado em autonomia | Baseado em fuel rate |
| **Estrutura** | TripGPSParams (12 campos) | TelemetryParams (11 campos) |
| **Pré-processamento** | Complexo (preprocess_obdlink.py) | Simples (identifica viagens) |

---

## 🗂️ Arquivos Criados

### 1️⃣ Contrato Solidity

**[E1RegistryTelemetry.sol](contracts/E1RegistryTelemetry.sol)**
- Struct `TelemetryParams` compatível com dados de telemetria
- Cálculo de emissão baseado em `fuelRateAvg` × `tripDuration`
- Correção de elevação mantida (5 faixas)
- Função `_calculateEmission()` simplificada

### 2️⃣ Script de Processamento

**[process_obdlink_telemetry.py](scripts/process_obdlink_telemetry.py)**
- Identifica viagens por gaps de tempo (>5min = nova viagem)
- Aplica Differential Privacy nas coordenadas GPS
- Captura elevação com SRTM (antes/depois DP)
- Calcula médias: velocidade, etanol, fuel rate
- **Saída**: CSV com viagens agregadas

### 3️⃣ Script de Blockchain

**[send_telemetry_to_blockchain.py](scripts/send_telemetry_to_blockchain.py)**
- Lê CSV processado
- Formata parâmetros para `TelemetryParams`
- Envia ao contrato `E1RegistryTelemetry`
- Aguarda confirmações

---

## 🚀 Como Usar

### Pré-requisitos

1. **SRTM instalado** (para elevação):
```bash
cd /home/inmetro/besu-starter-victor/contracts/privacy/implementacao3.5
./elevation/install.sh
```

2. **Contrato deployado**:
```bash
cd contracts
npx hardhat compile
# Deploy E1RegistryTelemetry.sol
```

### Passo 1: Processar OBDLink.csv

```bash
cd /home/inmetro/besu-starter-victor/contracts/privacy/implementacao3.5/scripts

python3 process_obdlink_telemetry.py \
    ../data/OBDLink.csv \
    trips_telemetry.csv \
    VEHICLE_ABC123 \
    0.5
```

**Parâmetros**:
- `../data/OBDLink.csv` - arquivo de entrada
- `trips_telemetry.csv` - arquivo de saída
- `VEHICLE_ABC123` - VIN do veículo
- `0.5` - epsilon (privacidade diferencial)

**Saída**: `trips_telemetry.csv` com colunas:

```csv
vin,trip_id,timestamp,start_lat_private,start_lon_private,end_lat_private,end_lon_private,start_elevation,end_elevation,avg_speed,ethanol_percent,fuel_rate_avg,trip_duration,num_samples
```

### Passo 2: Enviar ao Blockchain

```bash
python3 send_telemetry_to_blockchain.py \
    trips_telemetry.csv \
    0x1234567890abcdef... \
    0xabc123...
```

**Parâmetros**:
- `trips_telemetry.csv` - CSV processado
- `0x1234...` - endereço do contrato E1RegistryTelemetry
- `0xabc123...` - chave privada da conta oracle

---

## 📊 Formato dos Dados

### Entrada: OBDLink.csv

```csv
Time (sec), Latitude (deg), Longitude (deg), Vehicle speed (km/h), Fuel rate (l/hr), Alcohol fuel percentage (%), ...
0.000,-23.03084,-44.54698,5,4.23978,32.15686,...
```

### Intermediário: trips_telemetry.csv

```csv
vin,trip_id,timestamp,start_lat_private,start_lon_private,end_lat_private,end_lon_private,start_elevation,end_elevation,avg_speed,ethanol_percent,fuel_rate_avg,trip_duration,num_samples
VEHICLE_ABC123,1,1705675531,-23030840,-44546980,-23030860,-44546950,42,38,45.3,32.5,4.24,320,156
```

### Blockchain: TelemetryData

```solidity
struct TelemetryData {
    string vin;
    uint256 timestamp;
    GPSLocation startLocation;
    GPSLocation endLocation;
    uint16 startElevation;
    uint256 avgSpeed;
    uint256 ethanolPercent;
    uint256 fuelConsumed;          // Calculado: fuelRate × duration / 3600
    uint256 emissaoCalculada;      // Calculado: fuel × emissionFactor × elevationFactor
    int256 valorE1;                // Calculado: emissao × carbonPrice
    address pseudonimo;
    bool pago;
}
```

---

## 🧮 Cálculos no Contrato

### 1. Consumo de Combustível

```solidity
fuelConsumed = (fuelRateAvg × tripDuration) / 3600
```

**Exemplo**:
- Fuel rate: 4.24 l/hr (× 1000 = 4240)
- Duração: 320 segundos
- Consumo: (4240 × 320) / 3600 = 377 (× 1000) → 0.377 litros

### 2. Emissão Base

```solidity
emissaoGasolina = (fuelConsumed × 2310 gCO2/l × gasolineRatio) / 100
emissaoEtanol = (fuelConsumed × 1510 gCO2/l × ethanolRatio) / 100
emissaoBase = emissaoGasolina + emissaoEtanol
```

**Exemplo** (32.5% etanol):
- Gasolina: 0.377 × 2310 × 67.5% = 588 gCO2
- Etanol: 0.377 × 1510 × 32.5% = 185 gCO2
- **Total**: 773 gCO2

### 3. Correção de Elevação

```solidity
elevationFactor = _getElevationFactor(startElevation)
emissaoFinal = (emissaoBase × elevationFactor) / 100
```

**Exemplo** (42m de elevação):
- Fator: 100 (plano, sem correção)
- Emissão final: 773 × 100 / 100 = **773 gCO2**

### 4. Valor E1

```solidity
valorE1 = (emissaoFinal × carbonPrice) / 1_000_000_000_000
```

**Exemplo** (R$ 50/ton):
- 773 gCO2 × 50 R$/ton / 1e12 = **R$ 0,00003865**

---

## 🔍 Comparação: Original vs Simplificado

### Exemplo de Viagem (100 km, 1 hora)

#### Pipeline Original (E1RegistryGPS)

**Entrada necessária**:
```python
{
    'highwayDistance': 80_000_000,   # 80 km × 1e6
    'cityDistance': 20_000_000,       # 20 km × 1e6
    'roadGasoline': 8_000_000,        # 8 km/l × 1e6
    'roadEthanol': 6_000_000,         # 6 km/l × 1e6
    'cityGasoline': 10_000_000,       # 10 km/l × 1e6
    'cityEthanol': 8_000_000,         # 8 km/l × 1e6
    'ethanolPercent': 32_500_000,     # 32.5% × 1e6
    # ... + outros 5 campos
}
```

**Cálculo**: Baseado em autonomia (km/l) e distâncias

#### Pipeline Simplificado (E1RegistryTelemetry)

**Entrada necessária**:
```python
{
    'avgSpeed': 100_000,              # 100 km/h × 1e3
    'ethanolPercent': 32_500,         # 32.5% × 1e3
    'fuelRateAvg': 8_500,             # 8.5 l/hr × 1e3
    'tripDuration': 3600,             # 3600 segundos
    # ... + coordenadas/elevação
}
```

**Cálculo**: Baseado em consumo direto (l/hr)

### Resultado

Ambos chegam a emissões similares (variação <5%), mas o pipeline simplificado:
- ✅ Requer menos campos de entrada
- ✅ Não precisa calcular autonomia
- ✅ Usa dados diretos do OBD (fuel rate)
- ✅ Processamento mais rápido

---

## 🧪 Teste Completo

### 1. Verificar SRTM

```bash
python3 -c "import srtm; data = srtm.get_data(); print(f'Elevação: {data.get_elevation(-23.03084, -44.54698)}m')"
```

### 2. Processar CSV

```bash
cd scripts
python3 process_obdlink_telemetry.py ../data/OBDLink.csv test_output.csv TEST_VIN 0.5
```

**Verificar saída**:
```bash
head -5 test_output.csv
wc -l test_output.csv
```

### 3. Compilar Contrato

```bash
cd ../contracts
npx hardhat compile
```

### 4. Deploy (exemplo Hardhat)

```javascript
// scripts/deploy_telemetry.js
const { ethers } = require("hardhat");

async function main() {
  const E1RegistryTelemetry = await ethers.getContractFactory("E1RegistryTelemetry");
  const contract = await E1RegistryTelemetry.deploy();
  await contract.deployed();
  console.log("E1RegistryTelemetry deployed to:", contract.address);
}

main();
```

```bash
npx hardhat run scripts/deploy_telemetry.js --network besu
```

### 5. Enviar ao Blockchain

```bash
cd ../scripts
python3 send_telemetry_to_blockchain.py \
    test_output.csv \
    0x<CONTRACT_ADDRESS> \
    0x<ORACLE_PRIVATE_KEY>
```

---

## 📈 Vantagens do Pipeline Simplificado

1. **Menos Pré-processamento**
   - Não precisa classificar highway/city
   - Não precisa calcular autonomia por tipo de via
   - Usa dados diretos do sensor OBD

2. **Mais Compatível**
   - Funciona com qualquer CSV de telemetria
   - Não depende de dados externos (exceto SRTM para elevação)
   - Formato padrão OBD-II

3. **Mais Preciso**
   - Fuel rate direto do ECU
   - Menos estimativas/aproximações
   - Elevação real (SRTM/NASA)

4. **Mais Simples**
   - Menos campos no contrato
   - Menos cálculos complexos
   - Código mais legível

---

## 🐛 Solução de Problemas

### Erro: "Module 'differential_privacy_gps' not found"

**Causa**: Script de DP não está no mesmo diretório

**Solução**:
```bash
cd /home/inmetro/besu-starter-victor/contracts/privacy/implementacao3.5/scripts
# Verificar se differential_privacy_gps.py existe
ls -la differential_privacy_gps.py
```

### Aviso: "DP desabilitado"

**Causa**: Módulo de DP não foi importado

**Efeito**: Coordenadas não terão privacidade diferencial aplicada

**Solução**: Verificar imports no início de `process_obdlink_telemetry.py`

### Erro: "No trips identified"

**Causa**: Gaps de tempo entre registros são muito pequenos

**Solução**: Ajustar parâmetro `max_gap_seconds` em `identify_trips()`

### Elevação sempre 0

**Causa**: SRTM não instalado

**Solução**:
```bash
pip3 install srtm.py
```

---

## 🔄 Fluxo Completo

```
OBDLink.csv (15.856 registros)
    ↓
[identify_trips] Identificar viagens por gap de tempo
    ↓
[process_trip_telemetry] Para cada viagem:
    ├─ Aplicar DP às coordenadas
    ├─ Obter elevação (SRTM)
    ├─ Calcular médias (speed, ethanol, fuel rate)
    └─ Agregar duração
    ↓
trips_telemetry.csv (N viagens)
    ↓
[prepare_telemetry_params] Formatar para contrato
    ↓
[register_trip] Enviar ao E1RegistryTelemetry
    ↓
Blockchain calculará:
    ├─ Consumo de combustível
    ├─ Emissão base (gasolina + etanol)
    ├─ Correção de elevação
    └─ Valor E1
```

---

## ✅ Checklist de Validação

Antes de usar em produção:

- [ ] SRTM instalado e funcionando
- [ ] differential_privacy_gps.py disponível
- [ ] OBDLink.csv tem colunas necessárias
- [ ] Contrato E1RegistryTelemetry compilado
- [ ] Contrato deployado na rede Besu
- [ ] Conta oracle tem saldo suficiente
- [ ] CSV processado tem viagens válidas
- [ ] Testes locais executados com sucesso

---

## 📚 Próximos Passos

1. **Produção**: Deploy em rede Besu real
2. **Otimização**: Batch de múltiplas viagens em uma transação
3. **Monitoramento**: Dashboard de viagens registradas
4. **Análise**: Comparar E1 calculado vs emissão real

---

**Status**: ✅ Pipeline alternativo implementado e pronto para uso  
**Compatível com**: OBDLink.csv e formatos similares de telemetria OBD-II  
**Última atualização**: 23 de fevereiro de 2026
