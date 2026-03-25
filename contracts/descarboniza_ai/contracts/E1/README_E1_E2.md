# Contrato CarbonCreditNFT_E1_E2_Calculator

## 📋 Visão Geral

Este contrato implementa dois tipos de cálculos para viagens ecológicas, baseados no código Python original:

1. **E1**: Cálculo de emissões de CO2 e valor monetário baseado no mercado europeu de carbono
2. **E2**: Cálculo de custo energético equivalente

## 🔬 Cálculo E1 - Meta de Emissão CO2

### Objetivo
Calcula a meta de emissões de CO2 para uma viagem, compara com as emissões reais e monetiza a diferença (economia).

### Fórmula Python Original
```python
# Constantes
EMISSAO_GASOLINA = 1.720  # kg CO2/L
EMISSAO_ETANOL = 1.510    # kg CO2/L

# Cálculo
parte_1 = dist_highway * (1/road_gasoline) * (p_gas/100) * EMISSAO_GASOLINA * 1000
        + dist_highway * (1/road_ethanol) * (p_etanol/100) * EMISSAO_ETANOL * 1000

parte_2 = dist_city * (1/city_gasoline) * (p_gas/100) * EMISSAO_GASOLINA * 1000
        + dist_city * (1/city_ethanol) * (p_etanol/100) * EMISSAO_ETANOL * 1000

Meta_CO2 = parte_1 + parte_2  # gramas
Diff = Meta_CO2 - co2_real    # economia em gramas
e1 = Diff * Real_price / 1_000_000  # valor em BRL
```

### Estrutura de Entrada (E1CalculationParams)
```solidity
struct E1CalculationParams {
    uint256 highwayDistance;    // Distância rodovia (km * 1e6)
    uint256 cityDistance;       // Distância cidade (km * 1e6)
    uint256 ethanolPercent;     // % etanol no tanque (* 1e6, 0-100)
    uint256 roadGasoline;       // Consumo estrada gasolina (km/L * 1e6)
    uint256 roadEthanol;        // Consumo estrada etanol (km/L * 1e6)
    uint256 cityGasoline;       // Consumo cidade gasolina (km/L * 1e6)
    uint256 cityEthanol;        // Consumo cidade etanol (km/L * 1e6)
    uint256 realCO2Emissions;   // Emissões reais (gramas * 1e6)
    uint256 carbonPricePerTon;  // Preço carbono (BRL/tonelada * 1e6)
}
```

### Estrutura de Saída (E1CalculationResult)
```solidity
struct E1CalculationResult {
    uint256 tanqueGasoline;     // % gasolina no tanque
    uint256 parte1;             // Emissões estrada (gramas * 1e6)
    uint256 parte2;             // Emissões cidade (gramas * 1e6)
    uint256 metaCO2;            // Meta total CO2 (gramas * 1e6)
    uint256 diff;               // Economia CO2 (gramas * 1e6)
    uint256 e1Value;            // Valor monetário (BRL * 1e6)
    uint256 totalDistance;      // Distância total
}
```

### Exemplo de Uso E1
```solidity
// Preparar parâmetros
E1CalculationParams memory params = E1CalculationParams({
    highwayDistance: 50 * 1e6,      // 50 km
    cityDistance: 30 * 1e6,         // 30 km
    ethanolPercent: 27 * 1e6,       // 27% etanol
    roadGasoline: 14 * 1e6,         // 14 km/L gasolina (estrada)
    roadEthanol: 10 * 1e6,          // 10 km/L etanol (estrada)
    cityGasoline: 12 * 1e6,         // 12 km/L gasolina (cidade)
    cityEthanol: 8 * 1e6,           // 8 km/L etanol (cidade)
    realCO2Emissions: 8500 * 1e6,   // 8500g emissões reais
    carbonPricePerTon: 414 * 1e6    // R$ 414 por tonelada CO2
});

// Calcular e criar NFT
(uint256 tokenId, uint256 e1Value) = contract.calculateE1AndTokenize(
    params,
    condutorAddress
);

// Consultar detalhes
E1CalculationResult memory result = contract.getE1CalculationDetails(tokenId);
```

### Conversões de Escala E1
Todos os valores usam escala `* 1e6` para precisão de 6 casas decimais:

- **Distâncias**: `50 km` → `50 * 1e6` (50.000000 km)
- **Percentuais**: `27%` → `27 * 1e6` (27.000000%)
- **Consumo**: `14 km/L` → `14 * 1e6` (14.000000 km/L)
- **Emissões**: `8500g` → `8500 * 1e6` (8500.000000g)
- **Preço**: `R$ 414/ton` → `414 * 1e6` (414.000000 BRL/ton)

### Constantes E1 no Contrato
```solidity
uint256 EMISSAO_GASOLINA = 1720 * 1e6; // 1.720 kg/L = 1720 g/L
uint256 EMISSAO_ETANOL = 1510 * 1e6;   // 1.510 kg/L = 1510 g/L
```

## ⚡ Cálculo E2 - Custo Energético

### Objetivo
Converte consumo de combustível em custo energético equivalente (kWh) e aplica bônus de comportamento.

### Fórmula Python Original
```python
# Constantes
MJ_kWh = 0.2778                    # Conversão MJ para kWh
gasoline_MJ = 29.5                 # MJ por litro gasolina
etanol_MJ = 21.3                   # MJ por litro etanol
preco_tarifa = 0.774               # R$/kWh

# Conversões
convert_gasoline = MJ_kWh * gasoline_MJ * preco_tarifa * (tanque_gas/100)
convert_etanol = MJ_kWh * etanol_MJ * preco_tarifa * (ethanol/100)

# Custos
valores_estrada = ((convert_gas/road_gas) + (convert_eth/road_eth)) * highway_dist
valores_cidade = ((convert_gas/city_gas) + (convert_eth/city_eth)) * city_dist

# Bônus comportamento
prop_bonus = (cautious/100)*0.05 + (normal/100)*0.02 + (aggressive/100)*0.005

# E2 Final
e2 = prop_bonus * (valores_estrada + valores_cidade)
```

### Estrutura de Entrada (CalculationParams)
```solidity
struct CalculationParams {
    uint256 highwayDistance;    // Distância rodovia (km * 1e6)
    uint256 cityDistance;       // Distância cidade (km * 1e6)
    uint256 ethanolPercent;     // % etanol (* 1e6)
    uint256 roadGasoline;       // Consumo estrada gasolina (km/L * 1e6)
    uint256 roadEthanol;        // Consumo estrada etanol (km/L * 1e6)
    uint256 cityGasoline;       // Consumo cidade gasolina (km/L * 1e6)
    uint256 cityEthanol;        // Consumo cidade etanol (km/L * 1e6)
    uint256 precoGasolina;      // Preço gasolina (BRL/L * 1e6) [não usado]
    uint256 precoEtanol;        // Preço etanol (BRL/L * 1e6) [não usado]
    uint256 behaviorCautious;   // % comportamento cauteloso (* 1e6)
    uint256 behaviorNormal;     // % comportamento normal (* 1e6)
    uint256 behaviorAggressive; // % comportamento agressivo (* 1e6)
}
```

### Estrutura de Saída (CalculationResult)
```solidity
struct CalculationResult {
    uint256 tanqueGasoline;     // % gasolina
    uint256 dtEstradaGasolina;  // Custo estrada gasolina
    uint256 dtEstradaEtanol;    // Custo estrada etanol
    uint256 dfEstrada;          // Custo total estrada
    uint256 dtCidadeGasolina;   // Custo cidade gasolina
    uint256 dtCidadeEtanol;     // Custo cidade etanol
    uint256 dfCidade;           // Custo total cidade
    uint256 propBonus;          // Multiplicador bônus
    uint256 e2Final;            // E2 final (R$ * 1e6)
    uint256 totalDistance;      // Distância total
}
```

### Exemplo de Uso E2
```solidity
// Preparar parâmetros
CalculationParams memory params = CalculationParams({
    highwayDistance: 50 * 1e6,
    cityDistance: 30 * 1e6,
    ethanolPercent: 27 * 1e6,
    roadGasoline: 14 * 1e6,
    roadEthanol: 10 * 1e6,
    cityGasoline: 12 * 1e6,
    cityEthanol: 8 * 1e6,
    precoGasolina: 0,  // Não usado no cálculo
    precoEtanol: 0,    // Não usado no cálculo
    behaviorCautious: 60 * 1e6,   // 60% cauteloso
    behaviorNormal: 30 * 1e6,     // 30% normal
    behaviorAggressive: 10 * 1e6  // 10% agressivo
});

// Calcular e criar NFT
(uint256 tokenId, uint256 e2Value) = contract.calculateE2AndTokenize(
    params,
    condutorAddress
);

// Consultar detalhes
CalculationResult memory result = contract.getE2CalculationDetails(tokenId);
```

### Constantes E2 no Contrato
```solidity
// Pré-calculadas para otimização:
uint256 convertGasoline = 6.339906 * (tanque_gas/100)  // MJ_kWh * gasoline_MJ * tarifa
uint256 convertEtanol = 4.579794 * (ethanol/100)       // MJ_kWh * etanol_MJ * tarifa
```

## 🎯 Funções Principais

### E1 - Emissões CO2
```solidity
// Criar NFT com cálculo E1
function calculateE1AndTokenize(
    E1CalculationParams memory params,
    address recipient
) external returns (uint256 tokenId, uint256 e1Value);

// Simular sem criar NFT
function simulateE1Calculation(
    E1CalculationParams memory params
) external pure returns (E1CalculationResult memory);

// Consultar NFT existente
function getE1CalculationDetails(
    uint256 tokenId
) external view returns (E1CalculationResult memory);
```

### E2 - Custo Energético
```solidity
// Criar NFT com cálculo E2
function calculateE2AndTokenize(
    CalculationParams memory params,
    address recipient
) external returns (uint256 tokenId, uint256 e2Value);

// Simular sem criar NFT
function simulateE2Calculation(
    CalculationParams memory params
) external pure returns (CalculationResult memory);

// Consultar NFT existente
function getE2CalculationDetails(
    uint256 tokenId
) external view returns (CalculationResult memory);
```

## 📊 Eventos Emitidos

### E1
```solidity
event E1Calculated(
    address indexed user,
    uint256 indexed tokenId,
    uint256 metaCO2,
    uint256 diff,
    uint256 e1Value,
    uint256 timestamp
);

event E1DetailedCalculation(
    uint256 indexed tokenId,
    uint256 parte1,
    uint256 parte2,
    uint256 metaCO2,
    uint256 realCO2
);
```

### E2
```solidity
event E2Calculated(
    address indexed user,
    uint256 indexed tokenId,
    uint256 e2Value,
    uint256 totalDistance,
    uint256 timestamp
);

event E2DetailedCalculation(
    uint256 indexed tokenId,
    uint256 dfEstrada,
    uint256 dfCidade,
    uint256 propBonus,
    uint256 tanqueGasoline
);
```

## 🔒 Controle de Acesso

- Apenas endereços autorizados podem criar NFTs (`calculateE1AndTokenize` e `calculateE2AndTokenize`)
- O owner pode autorizar/desautorizar endereços via `setAuthorized(address, bool)`
- Funções de simulação são `pure` e podem ser chamadas por qualquer um

## 💡 Casos de Uso

### 1. Calcular valor de crédito de carbono (E1)
```solidity
// App registra viagem com dados reais
E1CalculationParams memory params = prepareE1Params(tripData);
(uint256 tokenId, uint256 value) = contract.calculateE1AndTokenize(params, driver);
// Driver recebe NFT representando economia de CO2 monetizada
```

### 2. Calcular economia energética (E2)
```solidity
// App avalia eficiência energética com comportamento
CalculationParams memory params = prepareE2Params(tripData);
(uint256 tokenId, uint256 value) = contract.calculateE2AndTokenize(params, driver);
// Driver recebe NFT representando economia energética
```

### 3. Simulação antes de criar NFT
```solidity
// Preview do valor antes de confirmar
E1CalculationResult memory preview = contract.simulateE1Calculation(params);
if (preview.e1Value > minimumValue) {
    // Prosseguir com criação do NFT
    contract.calculateE1AndTokenize(params, driver);
}
```

## 🧮 Tabela de Conversão de Escala

| Valor Real | Valor no Contrato | Conversão |
|------------|-------------------|-----------|
| 50 km | `50 * 1e6` | `50000000` |
| 27% | `27 * 1e6` | `27000000` |
| 14.5 km/L | `14.5 * 1e6` | `14500000` |
| 8500 g | `8500 * 1e6` | `8500000000` |
| R$ 414.50 | `414.5 * 1e6` | `414500000` |

Para converter de volta:
```solidity
uint256 realValue = contractValue / 1e6;
// Exemplo: 50000000 / 1e6 = 50 km
```

## ⚠️ Observações Importantes

1. **Escala**: Todos os valores usam escala `1e6` (6 casas decimais)
2. **Preço Carbono**: Deve ser passado em BRL por tonelada (Real_price do Python)
3. **Emissões Reais**: Devem vir de sensores/cálculos externos
4. **Gas Optimization**: Funções `pure` para simulação não gastam gas
5. **NFTs Únicos**: Cada cálculo gera um NFT único com dados imutáveis

## 🔗 Compatibilidade

- ✅ ERC-721 compliant
- ✅ ERC-721 Enumerable
- ✅ Reentrancy Guard
- ✅ Ownable (OpenZeppelin)
- ✅ Solidity ^0.8.19
