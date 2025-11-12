# Mapeamento R → Solidity

Este documento mostra a correspondência exata entre o código R original e a implementação Solidity.

## 📋 Índice
- [Passo 5: Proporção de Gasolina](#passo-5-proporção-de-gasolina)
- [Parte 2: Distância Estrada](#parte-2-distância-estrada)
- [Parte 2: Distância Cidade](#parte-2-distância-cidade)
- [Parte 2: Bônus de Dirigibilidade](#parte-2-bônus-de-dirigibilidade)
- [Parte 2: Cálculo E2](#parte-2-cálculo-e2)
- [Parte 3: Tracking](#parte-3-tracking)

---

## Passo 5: Proporção de Gasolina

### Código R
```r
df$Tanque_gasoline <- 100 - (df$`ethanol (%)`)
```

### Código Solidity
```solidity
result.tanqueGasoline = (100 * 1e6) - params.ethanolPercent;
```

### Explicação
- **Entrada**: `ethanol (%)` - Percentual de etanol no tanque
- **Saída**: `Tanque_gasoline` - Percentual de gasolina no tanque
- **Fórmula**: Se 75% é etanol, então 25% é gasolina
- **Escala**: Solidity usa 1e6 para manter precisão decimal

---

## Parte 2: Distância Estrada

### 2.1 Estrada - Gasolina

#### Código R
```r
df$dt_estrada_gasolina <- df$`highway (distance)` * 
                          ((1/df$road_gasoline) * 
                          ((df$Tanque_gasoline/100) / df$Preco_Gasolina))
```

#### Código Solidity
```solidity
result.dtEstradaGasolina = (params.highwayDistance * result.tanqueGasoline * 1e6) / 
                           (params.roadGasoline * 100 * params.precoGasolina);
```

#### Tabela de Correspondência

| Variável R | Variável Solidity | Descrição |
|-----------|-------------------|-----------|
| `highway (distance)` | `params.highwayDistance` | Distância em estrada (km) |
| `road_gasoline` | `params.roadGasoline` | Eficiência estrada com gasolina (km/L) |
| `Tanque_gasoline` | `result.tanqueGasoline` | % gasolina no tanque |
| `Preco_Gasolina` | `params.precoGasolina` | Preço da gasolina (BRL/L) |

#### Matemática Detalhada

**Código R:**
```
dt_estrada_gasolina = highway × (1/road_gasoline) × (tanque_gasoline/100) / preco_gasolina
                    = highway × tanque_gasoline / (road_gasoline × 100 × preco_gasolina)
```

**Código Solidity (ajustado para escala 1e6):**
```
dt_estrada_gasolina = (highway × tanque_gasoline × 1e6) / 
                      (road_gasoline × 100 × preco_gasolina)
```

#### Exemplo Numérico

**Dados:**
- Distância: 150 km
- Eficiência: 14.1 km/L
- Tanque gasolina: 25%
- Preço: R$ 6.47/L

**Cálculo R:**
```r
dt = 150 * (1/14.1) * (25/100) / 6.47
   = 150 * 0.0709 * 0.25 / 6.47
   = 0.41
```

**Cálculo Solidity:**
```solidity
dt = (150000000 * 25000000 * 1000000) / (14100000 * 100 * 6470000)
   = 3750000000000000000000 / 9123700000000
   = 411
// Dividir por 1e6 = 0.000411 (em escala correta)
```

---

### 2.2 Estrada - Etanol

#### Código R
```r
df$dt_estrada_etanol <- df$`highway (distance)` * 
                        ((1/df$road_ethanol) * 
                        (1-(df$Tanque_gasoline/100)) / df$Preco_Etanol)
```

#### Código Solidity
```solidity
uint256 ethanolFraction = params.ethanolPercent; // já está em %
result.dtEstradaEtanol = (params.highwayDistance * ethanolFraction * 1e6) / 
                         (params.roadEthanol * 100 * params.precoEtanol);
```

#### Observação Importante

**R:** `1 - (Tanque_gasoline/100)` = percentual de etanol  
**Solidity:** `ethanolPercent` já contém esse valor diretamente

---

### 2.3 Total Estrada

#### Código R
```r
df$df_estrada <- df$dt_estrada_gasolina + df$dt_estrada_etanol
```

#### Código Solidity
```solidity
result.dfEstrada = result.dtEstradaGasolina + result.dtEstradaEtanol;
```

---

## Parte 2: Distância Cidade

### 3.1 Cidade - Gasolina

#### Código R
```r
df$dt_cidade_gasolina <- df$`city (distance)` * 
                         ((1/df$city_gasoline) * 
                         ((df$Tanque_gasoline/100) / df$Preco_Gasolina))
```

#### Código Solidity
```solidity
result.dtCidadeGasolina = (params.cityDistance * result.tanqueGasoline * 1e6) / 
                          (params.cityGasoline * 100 * params.precoGasolina);
```

**Mesma lógica da estrada, mas usando `cityDistance` e `cityGasoline`**

---

### 3.2 Cidade - Etanol

#### Código R
```r
df$dt_cidade_etanol <- df$`city (distance)` * 
                       ((1/df$city_ethanol) * 
                       (1-(df$Tanque_gasoline/100)) / df$Preco_Etanol)
```

#### Código Solidity
```solidity
uint256 ethanolFraction = params.ethanolPercent;
result.dtCidadeEtanol = (params.cityDistance * ethanolFraction * 1e6) / 
                        (params.cityEthanol * 100 * params.precoEtanol);
```

---

### 3.3 Total Cidade

#### Código R
```r
df$df_cidade <- df$dt_cidade_gasolina + df$dt_cidade_etanol
```

#### Código Solidity
```solidity
result.dfCidade = result.dtCidadeGasolina + result.dtCidadeEtanol;
```

---

## Parte 2: Bônus de Dirigibilidade

### Código R
```r
df$Prop_Bonus <- 1 + ((df$`behavior_cautious (%)`/100)*0.10 + 
                      (df$`behavior_normal (%)`/100)*0.05 + 
                      (df$`behavior_aggressive (%)`/100)*0)
```

### Código Solidity
```solidity
result.propBonus = 1e6 +                                    // 1.0
                   (params.behaviorCautious * 100000) / 1e6 +  // 0.10
                   (params.behaviorNormal * 50000) / 1e6;      // 0.05
                   // aggressive * 0 = não adiciona nada
```

### Tabela de Correspondência

| Variável R | Variável Solidity | Multiplicador |
|-----------|-------------------|---------------|
| `behavior_cautious (%)` | `params.behaviorCautious` | 0.10 (10%) |
| `behavior_normal (%)` | `params.behaviorNormal` | 0.05 (5%) |
| `behavior_aggressive (%)` | `params.behaviorAggressive` | 0.00 (0%) |

### Exemplo Numérico

**Dados:**
- Cauteloso: 60%
- Normal: 30%
- Agressivo: 10%

**Cálculo R:**
```r
Prop_Bonus = 1 + (60/100)*0.10 + (30/100)*0.05 + (10/100)*0
           = 1 + 0.60*0.10 + 0.30*0.05 + 0
           = 1 + 0.06 + 0.015
           = 1.075 (7.5% de bônus)
```

**Cálculo Solidity:**
```solidity
propBonus = 1000000 + (60000000 * 100000) / 1000000 + (30000000 * 50000) / 1000000
          = 1000000 + 60000 + 15000
          = 1075000 (1.075 em escala 1e6)
```

---

## Parte 2: Cálculo E2

### Código R
```r
df$E2 <- df$Prop_Bonus * (df$df_estrada + df$df_cidade)
```

### Código Solidity
```solidity
uint256 totalDistanceCost = result.dfEstrada + result.dfCidade;
result.e2Final = (result.propBonus * totalDistanceCost) / 1e6;
```

### Fórmula Completa

```
E2 = Prop_Bonus × (Custo_Estrada + Custo_Cidade)

Onde:
- Custo_Estrada = dt_estrada_gasolina + dt_estrada_etanol
- Custo_Cidade = dt_cidade_gasolina + dt_cidade_etanol
- Prop_Bonus = 1 + bônus_de_dirigibilidade
```

### Exemplo Completo

**Dados:**
```
highway_distance = 150 km
city_distance = 80 km
ethanol_percent = 75%
road_gasoline = 14.1 km/L
road_ethanol = 9.8 km/L
city_gasoline = 11.6 km/L
city_ethanol = 8.0 km/L
preco_gasolina = R$ 6.47
preco_etanol = R$ 4.94
behavior_cautious = 60%
behavior_normal = 30%
behavior_aggressive = 10%
```

**Passo a Passo:**

1. **Tanque Gasolina:**
   ```
   tanque_gasoline = 100 - 75 = 25%
   ```

2. **Custo Estrada:**
   ```
   dt_estrada_gasolina ≈ 0.41
   dt_estrada_etanol ≈ 2.88
   df_estrada = 0.41 + 2.88 = 3.29
   ```

3. **Custo Cidade:**
   ```
   dt_cidade_gasolina ≈ 0.26
   dt_cidade_etanol ≈ 1.53
   df_cidade = 0.26 + 1.53 = 1.79
   ```

4. **Bônus:**
   ```
   Prop_Bonus = 1 + (0.60 × 0.10) + (0.30 × 0.05) + (0.10 × 0)
              = 1.075
   ```

5. **E2 Final:**
   ```
   E2 = 1.075 × (3.29 + 1.79)
      = 1.075 × 5.08
      = 5.46 BRL
   ```

---

## Parte 3: Tracking

### Código R
```r
# Parte 3 - Plotando os gráficos
g1 <- ggplot(df, aes(x = total_distance, y = E2)) +
      geom_line(color = "blue", size = 1) +
      labs(title = "", x = "Distância em km percorrida", y = "Valor de E2 em R$")

g2 <- ggplot(df, aes(x = total_distance)) +
      geom_histogram(aes(y = ..density..), bins = 30) +
      geom_density(color = "red", size = 1)
```

### Código Solidity (Eventos)

```solidity
// Evento para tracking de E2 vs Distância (equivalente ao gráfico g1)
event E2Calculated(
    address indexed user,
    uint256 indexed tokenId,
    uint256 e2Value,
    uint256 totalDistance,
    uint256 timestamp
);

// Evento para detalhes (equivalente aos dados do gráfico g2)
event E2DetailedCalculation(
    uint256 indexed tokenId,
    uint256 dfEstrada,
    uint256 dfCidade,
    uint256 propBonus,
    uint256 tanqueGasoline
);
```

### Como Replicar os Gráficos

**JavaScript (off-chain):**
```javascript
// Buscar todos os eventos
const filter = calculator.filters.E2Calculated();
const events = await calculator.queryFilter(filter);

// Preparar dados para gráfico 1 (E2 vs Distância)
const g1Data = events.map(event => ({
    x: ethers.formatUnits(event.args.totalDistance, 6),
    y: ethers.formatUnits(event.args.e2Value, 6)
}));

// Preparar dados para gráfico 2 (Distribuição de Distâncias)
const g2Data = events.map(event => 
    parseFloat(ethers.formatUnits(event.args.totalDistance, 6))
);

// Usar biblioteca de gráficos (Chart.js, D3.js, etc)
// para criar visualizações equivalentes aos do R
```

---

## 📊 Tabela Resumo de Conversão

| Conceito | R | Solidity | Observações |
|----------|---|----------|-------------|
| **Decimais** | Nativo | 1e6 | Solidity usa inteiros |
| **Distâncias** | `km` | `km * 1e6` | 6 casas decimais |
| **Eficiência** | `km/L` | `(km/L) * 1e6` | 6 casas decimais |
| **Preços** | `BRL/L` | `(BRL/L) * 1e6` | 6 casas decimais |
| **Percentuais** | `0-100` | `0-100 * 1e6` | 6 casas decimais |
| **Multiplicador** | `1.075` | `1075000` | Escala 1e6 |
| **Divisão** | `/` | `/ (ajustado)` | Cuidado com ordem |
| **NA/Infinite** | `<- 0` | Validação prévia | Evita divisão por 0 |
| **Gráficos** | ggplot | Eventos | Off-chain analysis |

---

## 🔍 Diferenças Importantes

### 1. Tratamento de Erros

**R:**
```r
df$dt_estrada_gasolina[is.na(df$dt_estrada_gasolina) | 
                       is.infinite(df$dt_estrada_gasolina)] <- 0
```

**Solidity:**
```solidity
require(params.roadGasoline > 0, "Road gasoline deve ser > 0");
require(params.precoGasolina > 0, "Preco gasolina deve ser > 0");
```

**Explicação**: Solidity valida antes de calcular, enquanto R trata depois.

---

### 2. Escala Numérica

**R:** Usa números decimais nativos  
**Solidity:** Usa inteiros com escala 1e6

**Conversão:**
```javascript
// Para Solidity
const toContract = (value) => ethers.parseUnits(value.toString(), 6);

// De Solidity
const fromContract = (value) => ethers.formatUnits(value, 6);
```

---

### 3. Visualização de Dados

**R:** Gráficos diretos com ggplot  
**Solidity:** Eventos + análise off-chain

**Workflow:**
1. Smart contract emite eventos
2. Aplicação captura eventos
3. JavaScript/Python processa dados
4. Biblioteca de gráficos visualiza

---

## ✅ Validação

### Teste de Equivalência

Para validar que ambos os códigos produzem resultados equivalentes:

```javascript
// Dados de teste
const testData = {
    highwayDistance: 150,
    cityDistance: 80,
    ethanolPercent: 75,
    roadGasoline: 14.1,
    roadEthanol: 9.8,
    cityGasoline: 11.6,
    cityEthanol: 8.0,
    precoGasolina: 6.47,
    precoEtanol: 4.94,
    behaviorCautious: 60,
    behaviorNormal: 30,
    behaviorAggressive: 10
};

// Executar no R
// Executar no Solidity
// Comparar resultados (com margem de erro < 0.01%)
```

---

## 📝 Notas Finais

1. **Precisão**: A escala 1e6 mantém 6 casas decimais de precisão
2. **Overflow**: Cuidado com valores muito grandes (usar SafeMath se necessário)
3. **Gas**: Operações de divisão são mais caras que multiplicação
4. **Validação**: Sempre validar inputs antes de calcular
5. **Eventos**: Essenciais para análise e debugging

---

**Documento criado para garantir fidelidade entre R e Solidity**  
**Versão**: 1.0  
**Data**: Outubro 2025