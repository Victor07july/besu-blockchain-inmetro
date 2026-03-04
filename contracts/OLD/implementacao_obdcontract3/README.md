# Implementação OBD Contract 3 - Sistema com Score de Qualidade

Sistema de monetização de emissões com **penalização automática** baseada na qualidade dos dados.

## 🎯 Conceito

Dados de trajeto de **baixa qualidade** (esparsos ou redundantes) recebem **menos créditos** automaticamente.

**Score de Qualidade:** 0-100  
**Multiplicador de Crédito:** 0.2-1.0 (20%-100%)

### Penalidades:

1. **Redundância Espacial** (pontos parados/repetitivos)
   - Detecta: % de pontos com movimento <5m
   - Penaliza: até -60 pontos

2. **Esparsidade Temporal** (intervalos grandes entre leituras)
   - Detecta: intervalo médio e gaps críticos
   - Penaliza: até -70 pontos

---

## 📂 Estrutura

```
implementacao_obdcontract3/
├── contracts/
│   └── E1MonetizationWithQuality.sol  # Smart contract com qualidade
├── scripts/
│   ├── calculate_quality_score.py     # Módulo de cálculo de qualidade
│   └── process_with_quality.py        # Processamento de trajetos
├── data/
│   ├── exemplo_ideal.csv              # Trajeto ideal (score ~100)
│   ├── exemplo_esparso.csv            # GPS espaçado (score ~50)
│   ├── exemplo_estacionado.csv        # Veículo parado (score ~40)
│   └── exemplo_ruim.csv               # Esparso + parado (score ~30)
└── demo.py                            # Demonstração dos 4 cenários
```

---

## 🚀 Uso Rápido

### 1. Demonstração Completa

```bash
cd /home/inmetro/besu-starter-victor/contracts/privacy/implementacao_obdcontract3
python3 demo.py
```

Testa 4 cenários e mostra comparação de scores.

### 2. Processar Arquivo Próprio

```bash
python3 scripts/process_with_quality.py input.csv output.csv VEHICLE_ID 0.175
```

**Parâmetros:**
- `input.csv`: CSV com colunas `lat`, `lon`, `timestamp`
- `output.csv`: Resultado com qualidade calculada
- `VEHICLE_ID`: ID do veículo
- `0.175`: Emissão em kg CO2 por km

### 3. Usar Módulo Diretamente

```python
from calculate_quality_score import calculate_quality_score

trajectory = [
    {'lat': -22.9068, 'lon': -43.1729, 'timestamp': 0},
    {'lat': -22.9069, 'lon': -43.1730, 'timestamp': 5},
    # ... mais pontos
]

result = calculate_quality_score(trajectory)
print(f"Score: {result['score']}")
print(f"Multiplicador: {result['multiplier']}")
```

---

## 📊 Formato CSV de Entrada

```csv
lat,lon,timestamp
-22.9068,-43.1729,0
-22.9069,-43.1730,5
-22.9070,-43.1731,10
```

**Colunas obrigatórias:**
- `lat`: Latitude (float)
- `lon`: Longitude (float)
- `timestamp`: Tempo em segundos desde início (float)

---

## 🎲 Cenários de Teste

### 1. Trajeto Ideal (Score ~100)
- GPS a cada 5 segundos
- Movimento fluido
- **Multiplicador:** 1.0 (100% dos créditos)

### 2. Trajeto Esparso (Score ~50)
- GPS a cada 5 minutos
- Movimento fluido
- **Multiplicador:** ~0.6 (60% dos créditos)

### 3. Veículo Estacionado (Score ~40)
- GPS a cada 5 segundos
- 0% movimento
- **Multiplicador:** ~0.5 (50% dos créditos)

### 4. Trajeto Ruim (Score ~30)
- GPS irregular (3-6 minutos)
- 50% pontos parados
- **Multiplicador:** ~0.4 (40% dos créditos)

---

## 💰 Exemplo de Impacto

**Viagem hipotética:** 10 km → 1.75 kg CO2

| Cenário | Score | Multiplicador | Créditos | Perda |
|---------|-------|---------------|----------|-------|
| Ideal | 100 | 1.0 | 1.75 kg | 0 kg |
| Esparso | 50 | 0.60 | 1.05 kg | 0.70 kg |
| Estacionado | 40 | 0.52 | 0.91 kg | 0.84 kg |
| Ruim | 30 | 0.44 | 0.77 kg | 0.98 kg |

---

## 🔐 Smart Contract

### Estrutura Trip:

```solidity
struct Trip {
    address user;
    string vehicleId;
    uint256 co2RawGrams;        // CO2 sem penalidade
    uint8 qualityScore;          // 0-100
    uint16 qualityMultiplier;    // 200-1000 (0.2-1.0)
    uint256 co2CreditsGrams;     // CO2 com penalidade
    // ... coordenadas, timestamp, etc
}
```

### Funções Principais:

```solidity
// Registrar viagem
registerTrip(vehicleId, ..., co2Raw, score, multiplier, co2Credits, ...)

// Consultar qualidade
getTripQuality(tripId) → (score, multiplier, co2Raw, co2Credits, penalty)

// Estatísticas de usuário
getUserTotalCO2(address) → (totalRaw, totalCredits, totalPenalty)
```

---

## 📋 Tabela de Penalidades

### Redundância (Movimento):

| % Parado | Cenário | Penalidade |
|----------|---------|------------|
| 0-20% | Movimento fluido | 0 |
| 20-40% | Tráfego com paradas | -10 |
| 40-60% | Congestionamento | -20 |
| 60-80% | Congestionamento severo | -40 |
| 80-100% | Estacionado | -60 |

### Esparsidade (Frequência):

| Intervalo Médio | Penalidade | +Gap >5min | +Gap >10min |
|-----------------|------------|------------|-------------|
| <30s | 0 | - | - |
| 30-60s | -5 | - | - |
| 1-2min | -15 | -10 | -20 |
| 2-5min | -30 | -10 | -20 |
| >5min | -50 | -10 | -20 |

**Score Final = 100 - Penalidade Redundância - Penalidade Esparsidade**

---

## ✅ Validação

### Teste Unitário do Módulo:

```bash
python3 scripts/calculate_quality_score.py
```

Roda 4 exemplos embutidos e mostra relatórios detalhados.

### Teste Completo:

```bash
python3 demo.py
```

Processa 4 CSVs e gera resumo comparativo.

---

## 🎓 Conceitos

### Redundância Espacial
Proporção de pontos consecutivos com movimento <5 metros.
- **Motivo:** GPS tem precisão ~5-10m, movimento menor pode ser drift
- **Detecta:** Veículo parado, dados repetitivos

### Esparsidade Temporal
Intervalo médio entre leituras e presença de gaps grandes.
- **Motivo:** Dados espaçados perdem eventos (aceleração, frenagem)
- **Detecta:** GPS mal configurado, dados picados

### Multiplicador Linear
`multiplier = 0.2 + (score/100) × 0.8`
- **Mínimo:** 0.2 (sempre recebe pelo menos 20%)
- **Máximo:** 1.0 (dados perfeitos = 100% créditos)
- **Suave:** sem degraus bruscos

---

## 🔍 Auditabilidade

✅ **CO2 bruto sempre registrado na blockchain**  
✅ **Score e multiplicador armazenados**  
✅ **Penalidade calculável: co2_raw - co2_credits**  
✅ **Transparência total para auditorias**

Dados ruins não são rejeitados, apenas penalizados proporcionalmente.

---

## 🛠️ Dependências

```bash
pip install pandas numpy
```

---

## 📞 Suporte

Documentação completa em: `GUIA_PRIVACIDADE_DIFERENCIAL_MAPAS.md` (pasta pai)

---

**Autor:** Victor  
**Data:** 2026-03-03  
**Licença:** MIT
