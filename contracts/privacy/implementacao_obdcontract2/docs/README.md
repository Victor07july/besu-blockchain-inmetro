# Implementação OBD Contract 2 - Distância Euclidiana

Sistema completo de monetização E1 com cálculo de distância euclidiana aproximada e emissão de CO2 baseada em dados reais de telemetria OBD.

## Arquitetura

```
implementacao_obdcontract2/
├── contracts/
│   └── E1RegistryEuclidean.sol      → Contrato inteligente
├── scripts/
│   ├── process_obd_euclidean.py     → Processamento de dados OBD
│   ├── deploy_e1_euclidean.py       → Deploy do contrato
│   └── send_trips_to_blockchain.py  → Envio de dados à blockchain
├── data/
│   └── OBDLink.csv                  → Dados brutos de telemetria
└── docs/
    ├── FORMULA_MONETIZACAO_EUCLIDIANA.md  → Documentação das fórmulas
    └── README.md                          → Este arquivo
```

## 📄 Descrição dos Arquivos

### 1. E1RegistryEuclidean.sol

**Localização:** `contracts/E1RegistryEuclidean.sol`

**Função:** Contrato inteligente Solidity que armazena e gerencia dados de viagens com monetização E1.

**Principais características:**
- Recebe dados já calculados off-chain (distância euclidiana, emissão CO2, valor E1)
- Armazena coordenadas GPS com privacidade diferencial aplicada
- Mantém registro de créditos vs débitos de carbono
- Permite consultas por VIN e estatísticas agregadas
- Sistema de pagamento para créditos E1 positivos

**Struct principal:**
```solidity
struct TripData {
    string vin;                  // Identificador do veículo
    uint256 timestamp;           // Momento da viagem
    uint256 totalDistance;       // Distância euclidiana (km × 1e6)
    uint256 fuelConsumed;        // Combustível consumido (l × 1e6)
    uint256 co2Real;             // Emissão real (kg × 1e6)
    uint256 co2Meta;             // Meta do fabricante (kg × 1e6)
    int256 valorE1;              // Valor monetário (R$ × 1e6)
    uint256 avgEthanolPercent;   // % médio de etanol
    GPSLocation startLocation;   // GPS início (com DP)
    GPSLocation endLocation;     // GPS fim (com DP)
    address pseudonimo;          // Endereço pseudônimo
    bool pago;                   // Status de pagamento
}
```

**Funções principais:**
- `registerTrip()` - Registra nova viagem (apenas oracle)
- `getTrip()` - Consulta viagem por ID
- `getStats()` - Estatísticas gerais (total viagens, créditos, débitos)
- `getVinStats()` - Estatísticas de um veículo específico
- `processPayment()` - Processa pagamento de créditos (apenas owner)

---

### 2. process_obd_euclidean.py

**Localização:** `scripts/process_obd_euclidean.py`

**Função:** Processa arquivo OBDLink.csv bruto e calcula todas as métricas necessárias para a monetização E1.

**Pipeline de processamento:**

1. **Identificação de viagens** - Detecta início/fim de viagens baseado em gaps de tempo (>5 minutos)

2. **Cálculo de distância euclidiana** - Para cada par de pontos consecutivos:
   - Converte diferença de latitude/longitude para km
   - Aplica correção de latitude no cálculo de longitude
   - Soma todos os segmentos = distância total

3. **Cálculo de emissão CO2 real** - Para cada segmento entre medições:
   - Multiplica fuel rate pelo intervalo de tempo
   - Aplica fatores de emissão (2.31 kg/l gasolina, 1.51 kg/l etanol)
   - Pondera pelo mix de combustível (% etanol do sensor)
   - Soma todos os segmentos = emissão total

4. **Cálculo de emissão meta** - Baseado no consumo declarado pelo fabricante:
   - Divide distância total pelo consumo (km/l)
   - Aplica mesmos fatores de emissão
   - Usa mix médio de etanol da viagem

5. **Monetização E1** - Fórmula comparativa:
   - Diferença = Meta - Real (kg CO2)
   - Valor E1 = (Diferença / 1000) × Preço carbono
   - Positivo = crédito (economizou), Negativo = débito (desperdiçou)

6. **Privacidade diferencial** - Adiciona ruído Laplace às coordenadas GPS de início/fim

**Entrada:** `OBDLink.csv` (dados brutos com colunas Time, Latitude, Longitude, Fuel rate, Alcohol percentage)

**Saída:** `trips_processed.csv` (uma linha por viagem com todos os dados agregados)

**Uso:**


















































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































```bash
python3 process_obd_euclidean.py ../data/OBDLink.csv trips_processed.csv VEHICLE_001 0.5 12.0
```

**Parâmetros:**
- `VEHICLE_001` - VIN ou identificador do veículo
- `0.5` - Epsilon para privacidade diferencial (menor = mais privacidade)
- `12.0` - Consumo do fabricante em km/l

---

### 3. deploy_e1_euclidean.py

**Localização:** `scripts/deploy_e1_euclidean.py`

**Função:** Compila e deploya o contrato E1RegistryEuclidean no Hyperledger Besu.

**O que faz:**

1. **Compilação:**
   - Instala Solidity 0.8.19 se necessário
   - Compila contrato com modo `via-IR` (resolve erro "Stack too deep")
   - Otimização habilitada (200 runs)

2. **Conexão:**
   - Conecta ao Besu em `localhost:8545`
   - Injeta middleware POA para compatibilidade QBFT
   - Valida conexão usando `eth_chain_id` e `eth_block_number`

3. **Deploy:**
   - Constrói transação de deploy
   - Assina com chave privada do deployer
   - Envia à blockchain e aguarda confirmação

4. **Salvamento:**
   - Gera `deployment_info.json` com:
     - Endereço do contrato
     - ABI completa
     - RPC URL
     - Hash da transação
     - Gas usado

**Saída:** `deployment_info.json` (usado pelos outros scripts)

**Uso:**
```bash
python3 deploy_e1_euclidean.py
```

**Requisitos:**
- Besu rodando em `localhost:8545`
- Conta com ETH para pagar gas

---

### 4. send_trips_to_blockchain.py

**Localização:** `scripts/send_trips_to_blockchain.py`

**Função:** Lê CSV processado e envia cada viagem como transação ao contrato.

**O que faz:**

1. **Carregamento:**
   - Lê `trips_processed.csv` gerado pelo script de processamento
   - Carrega endereço/ABI do contrato de `deployment_info.json`

2. **Preparação de dados:**
   - Converte coordenadas GPS para int256 (× 1e6)
   - Converte valores monetários para int256 (× 1e6)
   - Gera pseudônimo baseado em hash(VIN + trip_id)

3. **Envio:**
   - Para cada viagem no CSV:
     - Monta struct `TripData` com todos os campos
     - Constrói transação chamando `registerTrip()`
     - Assina com chave privada do oracle
     - Envia à blockchain
     - Aguarda confirmação (timeout 120s)

4. **Monitoramento:**
   - Conta sucessos vs falhas
   - Mostra progresso em tempo real
   - Exibe estatísticas finais do contrato

**Entrada:** `trips_processed.csv`

**Saída:** Transações na blockchain

**Uso:**
```bash
python3 send_trips_to_blockchain.py trips_processed.csv
```

---

## 🚀 Fluxo de Execução Completo

### Passo 1: Deploy do Contrato
```bash
cd scripts/
python3 deploy_e1_euclidean.py
```

**Resultado:** Contrato deployado, arquivo `deployment_info.json` criado

---

### Passo 2: Processar Dados OBD
```bash
python3 process_obd_euclidean.py ../data/OBDLink.csv trips_processed.csv MY_VEHICLE 0.5 12.0
```

**Resultado:** Arquivo `trips_processed.csv` com todas as viagens processadas

**Exemplo de saída:**
```
Viagens processadas: 5
Distância total: 123.45 km
CO2 real total: 28.50 kg
CO2 meta total: 30.20 kg
Economia CO2: +1.70 kg
Saldo E1 total: R$ +0.085
```

---

### Passo 3: Enviar à Blockchain
```bash
python3 send_trips_to_blockchain.py trips_processed.csv
```

**Resultado:** Todas as viagens registradas no contrato

**Exemplo de saída:**
```
[1/5] VIN: MY_VEHICLE | Trip: 1
  📏 Distância: 25.40 km
  ⛽ Combustível: 2.120 l
  🏭 CO2 real: 4.900 kg
  🎯 CO2 meta: 5.200 kg
  📊 Δ CO2: +0.300 kg
  💰 Valor E1: R$ +0.0150
  ✅ Confirmada! Block: 123 | Gas: 385420

...

✅ Sucesso: 5
Total créditos: R$ 0.09
Saldo líquido: R$ +0.09
```

---

## 📊 Dados Armazenados na Blockchain

Para cada viagem, o contrato armazena:

| Campo | Descrição | Precisão |
|-------|-----------|----------|
| `vin` | Identificador do veículo | string |
| `timestamp` | Unix timestamp da viagem | segundos |
| `totalDistance` | Distância euclidiana calculada | km × 10⁶ |
| `fuelConsumed` | Combustível consumido | litros × 10⁶ |
| `co2Real` | Emissão real calculada | kg × 10⁶ |
| `co2Meta` | Meta do fabricante | kg × 10⁶ |
| `valorE1` | Valor monetário (crédito/débito) | R$ × 10⁶ |
| `avgEthanolPercent` | % médio de etanol | % × 10³ |
| `startLocation` | GPS início com DP | graus × 10⁶ |
| `endLocation` | GPS fim com DP | graus × 10⁶ |
| `pseudonimo` | Endereço pseudônimo HD | address |
| `pago` | Status de pagamento | bool |

---

## 🔐 Privacidade e Segurança

**Privacidade Diferencial (DP):**
- Aplicada apenas nas coordenadas GPS de início/fim
- Ruído Laplace com epsilon configurável (0.5 padrão)
- Distância e emissão calculadas com dados originais (não-privados)
- Trade-off: menor epsilon = mais privacidade, mais erro nas coordenadas

**Pseudônimos:**
- Cada viagem recebe endereço único baseado em hash(VIN + trip_id)
- Impossível ligar múltiplas viagens ao mesmo usuário apenas pelos endereços
- VIN é armazenado em texto plano no contrato (visível para auditorias)

**Controle de Acesso:**
- `onlyOracle` - Apenas oracle pode registrar viagens
- `onlyOwner` - Apenas owner pode processar pagamentos e trocar oracle

---

## 📈 Consultas e Estatísticas

**Consultar viagem específica:**
```solidity
contract.functions.getTrip(tripId).call()
```

**Estatísticas gerais:**
```solidity
contract.functions.getStats().call()
// Retorna: (tripCount, totalCreditos, totalDebitos, saldoLiquido)
```

**Estatísticas por VIN:**
```solidity
contract.functions.getVinStats("MY_VEHICLE").call()
// Retorna: (numTrips, totalDistance, totalCO2Real, saldoE1)
```

**Listar viagens de um VIN:**
```solidity
contract.functions.getTripsByVIN("MY_VEHICLE").call()
// Retorna: [0, 1, 2, ...] (IDs das viagens)
```

---

## 🔧 Configurações Ajustáveis

No `process_obd_euclidean.py`:
- `EMISSAO_GASOLINA = 2.31` - kg CO2 por litro de gasolina
- `EMISSAO_ETANOL = 1.51` - kg CO2 por litro de etanol
- `CONSUMO_FABRICANTE = 12.0` - consumo declarado (km/l)
- `CARBON_PRICE = 50.0` - preço do carbono (R$/ton)
- `max_gap_seconds = 300` - gap máximo para identificar viagens (5 min)
- `min_trip_duration = 60` - duração mínima de viagem (1 min)

No `deploy_e1_euclidean.py`:
- `rpc_url = "http://localhost:8545"` - endereço do nó Besu
- `SOLC_VERSION = "0.8.19"` - versão do compilador Solidity

---

## 📚 Documentação Adicional

Ver [FORMULA_MONETIZACAO_EUCLIDIANA.md](FORMULA_MONETIZACAO_EUCLIDIANA.md) para:
- Fórmulas matemáticas detalhadas
- Explicação passo-a-passo dos cálculos
- Colunas do CSV utilizadas
- Teoria por trás da distância euclidiana e emissão CO2
