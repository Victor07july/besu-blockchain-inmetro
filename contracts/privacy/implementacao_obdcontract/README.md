# 📦 OBDContract - Pipeline Simplificado para OBDLink.csv

Versão alternativa do sistema E1 que trabalha **diretamente com dados de telemetria OBD** sem necessidade de pré-agregação complexa.

## 📁 Estrutura

```
obdcontract/
├── README.md                              # Este arquivo
├── PIPELINE_SIMPLIFICADO.md               # Documentação completa
├── contracts/
│   └── E1RegistryTelemetry.sol           # Contrato Solidity simplificado
└── scripts/
    ├── process_obdlink_telemetry.py      # Processa OBDLink.csv + DP + Elevação
    └── send_telemetry_to_blockchain.py   # Envia ao blockchain
```

## 🎯 Objetivo

Processar arquivos **OBDLink.csv** (telemetria OBD-II bruta) e enviar ao blockchain com:
- ✅ Differential Privacy nas coordenadas GPS
- ✅ Dados de elevação (SRTM/NASA)
- ✅ Cálculo de emissões baseado em fuel rate
- ✅ Correção topográfica (15-40% em montanhas)

## 🔄 Fluxo Rápido

```bash
# 1. Processar OBDLink.csv
cd scripts
python3 process_obdlink_telemetry.py \
    ../data/OBDLink.csv \
    trips_telemetry.csv \
    VEHICLE_001 \
    0.5

# 2. Enviar ao blockchain
python3 send_telemetry_to_blockchain.py \
    trips_telemetry.csv \
    0x<CONTRACT_ADDRESS> \
    0x<PRIVATE_KEY>
```

## 📊 Diferenças vs Pipeline Original

| Aspecto | Original (E1RegistryGPS) | Simplificado (E1RegistryTelemetry) |
|---------|--------------------------|-------------------------------------|
| **Entrada** | CSV pré-agregado | OBDLink.csv (telemetria bruta) |
| **Campos** | 12 campos obrigatórios | 8 campos + médias calculadas |
| **Distâncias** | highway/city separados | Velocidade média |
| **Emissões** | Baseado em km/l | Baseado em l/hr (fuel rate) |
| **Pré-processamento** | Complexo | Simples (identifica viagens) |

## 📚 Documentação

Leia [PIPELINE_SIMPLIFICADO.md](PIPELINE_SIMPLIFICADO.md) para:
- Guia de uso detalhado
- Exemplos de cálculos
- Solução de problemas
- Comparação com pipeline original

## 🚀 Início Rápido

### Pré-requisitos

```bash
# 1. Instalar SRTM (elevação)
cd ..
./elevation/install.sh

# 2. Verificar DP
cd scripts
python3 -c "import differential_privacy_gps; print('✓ DP disponível')"
```

### Processar Dados

```bash
python3 process_obdlink_telemetry.py ../data/OBDLink.csv output.csv VEHICLE_123 0.5
```

**Parâmetros**:
- `../data/OBDLink.csv` - arquivo OBD entrada
- `output.csv` - arquivo de saída
- `VEHICLE_123` - VIN do veículo
- `0.5` - epsilon (privacidade)

### Compilar Contrato

```bash
cd ../contracts
npx hardhat compile
```

### Deploy

```bash
npx hardhat run scripts/deploy_telemetry.js --network besu
```

### Enviar Viagens

```bash
cd ../scripts
python3 send_telemetry_to_blockchain.py \
    output.csv \
    0x1234... \
    0xabc...
```

## 🔍 Contrato E1RegistryTelemetry

### Struct Principal

```solidity
struct TelemetryParams {
    string vin;
    uint256 timestamp;
    GPSLocation startLocation;     // Com DP
    GPSLocation endLocation;       // Com DP
    uint16 startElevation;         // metros
    uint16 endElevation;           // metros
    uint256 avgSpeed;              // km/h × 1e3
    uint256 ethanolPercent;        // % × 1e3
    uint256 fuelRateAvg;           // l/hr × 1e3
    uint256 tripDuration;          // segundos
    uint256 carbonPrice;           // R$/ton × 1e6
    address pseudonimo;
}
```

### Cálculos

1. **Consumo**: `fuel = fuelRate × duration / 3600`
2. **Emissão base**: `CO2 = fuel × emissionFactor(ethanol%)`
3. **Correção**: `CO2_final = CO2 × elevationFactor`
4. **Valor E1**: `E1 = CO2 × carbonPrice`

## 📈 Exemplo

**Entrada** (1 viagem de 5 minutos):
```
Time: 0s
Lat: -23.03084, Lon: -44.54698
Speed: 45 km/h
Fuel rate: 4.24 l/hr
Ethanol: 32.5%
```

**Processamento**:
- DP aplicado: ε=0.5 (~200m ruído)
- Map matching: snap para via
- Elevação: 42m (SRTM)

**Blockchain**:
- Consumo: 0.35 litros
- Emissão: 680 gCO2
- Fator elevação: 100 (plano)
- Valor E1: R$ 0,000034

## 🧪 Testar

```bash
# Processar 1 viagem
cd scripts
python3 -c "
from process_obdlink_telemetry import process_obdlink_telemetry
process_obdlink_telemetry('../data/OBDLink.csv', 'test.csv', 'TEST', 0.5)
"

# Ver resultado
head -5 test.csv
```

## ✅ Status

- ✅ Contrato implementado
- ✅ Scripts de processamento criados
- ✅ Integração DP + Elevação
- ✅ Documentação completa
- ⏳ Deploy em rede

## 📞 Suporte

Veja [PIPELINE_SIMPLIFICADO.md](PIPELINE_SIMPLIFICADO.md) seção "Solução de Problemas"

---

**Criado**: 23 de fevereiro de 2026  
**Versão**: 1.0 - implementacao3.5/obdcontract
