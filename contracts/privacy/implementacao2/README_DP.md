# Implementação 2: E1 + GPS + Differential Privacy

## 🎯 Objetivo

Proof-of-concept que adiciona dados de localização GPS (sensíveis) protegidos por Differential Privacy, mantendo os pseudônimos HD da Implementação 1.

## 🔐 Differential Privacy (DP)

### O que é?

Técnica matemática que adiciona ruído controlado aos dados para proteger privacidade individual enquanto mantém utilidade estatística.

### Como funciona?

Adiciona ruído Laplace às coordenadas GPS:

```python
noise = np.random.laplace(loc=0, scale=sensitivity/epsilon)
private_coordinate = original + noise
```

### Parâmetro Epsilon (ε)

Controla o trade-off privacidade × precisão:

- **ε = 0.1**: Máxima privacidade (±1-2 km de erro)
- **ε = 1.0**: Privacidade moderada (±100-200 m)
- **ε = 10.0**: Privacidade mínima (±10-20 m)

**Menor ε = Mais privacidade, mas menos precisão**

## 📍 Dados GPS

### Dados sensíveis adicionados:

- `start_location` (latitude, longitude): Onde a viagem começou
- `end_location` (latitude, longitude): Onde terminou

### Riscos sem DP:

- Revelar onde a pessoa mora (start)
- Revelar onde trabalha (end)
- Padrões de deslocamento diário
- Inferir rotinas e hábitos

### Com DP aplicado:

- Coordenadas originais nunca expostas
- Impossível determinar localização exata
- Mantém utilidade para análises agregadas

## 🔄 Workflow

```
1. CSV original com GPS
   ↓
2. apply_dp.py (epsilon=1.0)
   → Adiciona ruído Laplace
   → Gera CSV privatizado
   ↓
3. send_e1_gps_data.py
   → Gera pseudônimo HD
   → Envia dados + GPS privatizado
   ↓
4. E1RegistryGPS.sol
   → Armazena dados com DP
   → Calcula E1 + fator mobilidade
```

## 📊 Scripts

### apply_dp.py

Aplica Differential Privacy às coordenadas GPS.

**Uso:**
```bash
python3 apply_dp.py --epsilon 1.0 --input ../dados.csv --output dados_dp.csv
```

**Parâmetros:**
- `--epsilon`: Nível de privacidade (default: 1.0)
- `--input`: CSV de entrada
- `--output`: CSV de saída com DP

### send_e1_gps_data.py

Envia dados com GPS privatizado para blockchain.

**Características:**
- Usa pseudônimos HD (mesma lógica da Implementação 1)
- Lê CSV com coordenadas já privatizadas
- Converte lat/lon para inteiros × 1e6
- Envia ao contrato E1RegistryGPS

### deploy_e1_gps.py

Deploy do contrato E1RegistryGPS.

Similar ao deploy_e1_v2.py da Implementação 1.

## 📝 Contrato E1RegistryGPS.sol

Estende E1Registry.sol adicionando:

```solidity
struct GPSLocation {
    int256 latitude;   // × 1e6
    int256 longitude;  // × 1e6
}

struct TripGPSParams {
    // Campos da Implementação 1
    string vin;
    uint256 timestamp;
    // ... outros campos ...
    
    // Novos campos GPS (com DP)
    GPSLocation startLocation;
    GPSLocation endLocation;
}
```

**Funções adicionais:**
- `registerTripGPS(TripGPSParams)`: Registra viagem com GPS
- `getTripGPS(uint256)`: Retorna viagem incluindo coordenadas
- `calculateMobilityFactor()`: Fator baseado em distância GPS

## 🧪 Teste de Epsilon

Para testar diferentes níveis de privacidade:

```bash
# Máxima privacidade (muito ruído)
python3 apply_dp.py --epsilon 0.1

# Privacidade moderada (recomendado)
python3 apply_dp.py --epsilon 1.0

# Privacidade mínima (pouco ruído)
python3 apply_dp.py --epsilon 10.0
```

Compare os resultados para entender o trade-off.

## ⚖️ Trade-offs

### Vantagens DP:
- ✅ Garantia matemática de privacidade
- ✅ Não precisa de infraestrutura complexa
- ✅ Mantém utilidade para análises agregadas
- ✅ Simples de implementar

### Limitações DP:
- ⚠️ Reduz precisão individual
- ⚠️ Epsilon precisa ser bem calibrado
- ⚠️ Não impede todos os ataques de inferência

## 🚀 Próximos Passos (Fase 3)

**Adicionar Zero-Knowledge Proofs:**
- Provar distância sem revelar coordenadas
- DP protege dados armazenados
- ZKP protege dados durante verificação
- Máxima privacidade end-to-end

## 📚 Referências

- Dwork, C., & Roth, A. (2014). The Algorithmic Foundations of Differential Privacy
- Google Differential Privacy Library: https://github.com/google/differential-privacy
- Laplace Mechanism: Fundamental building block de DP
