# Implementação 2: E1 + GPS + Differential Privacy

## 📋 Visão Geral

Esta implementação adiciona **coordenadas GPS** aos dados de viagens, protegidas por **Differential Privacy (DP)** através de ruído Laplace. É uma proof-of-concept para pesquisa acadêmica sobre privacidade em dados de mobilidade.

## 🎯 Objetivos

- Monetizar créditos de carbono (Fórmula E1)
- Proteger localização exata com DP
- Manter pseudônimos HD (herança da Implementação 1)
- Calcular distâncias GPS on-chain
- Analisar trade-off privacidade × utilidade

## 🏗️ Arquitetura

```
CSV Original (com GPS)
    ↓
apply_dp.py (opcional - análise)
    ↓
send_e1_gps_data.py (aplica DP inline)
    ↓
E1RegistryGPS.sol (blockchain)
    ↓
Resultados (GPS com DP + E1 calculado)
```

## 📁 Arquivos

### Contrato Solidity
- **E1RegistryGPS.sol**: Contrato com structs GPS e cálculo de distância

### Scripts Python
- **deploy_e1_gps.py**: Deploy do contrato
- **send_e1_gps_data.py**: Processa CSV, aplica DP, envia dados
- **apply_dp.py**: Aplica DP e salva CSV (opcional - para análise prévia)

### Dados
- **../dados_monetizacao_novas_emissões_etanol_original_gas_1720_v2.csv**: 33 viagens com GPS

## 🚀 Como Executar

### Pré-requisitos

```bash
# Certifique-se de que o Besu está rodando
# No diretório raiz do projeto:
cd ~/besu-starter-victor
./run.sh

# Ativar ambiente Python (se necessário)
source ../implementacao1/venv/bin/activate  # ou criar novo venv
pip install web3 eth-account pandas numpy py-solc-x
```

### Passo 1: Deploy do Contrato

```bash
cd ~/besu-starter-victor/contracts/privacy/implementacao2

python3 deploy_e1_gps.py
```

**Saída esperada:**
- Contrato compilado
- Endereço do contrato
- Arquivo `e1_gps_contract_address.json` criado

### Passo 2: Enviar Dados com DP

```bash
# Com Differential Privacy (epsilon = 1.0, padrão)
python3 send_e1_gps_data.py

# Ou com epsilon customizado
python3 send_e1_gps_data.py --epsilon 0.1  # Mais privacidade
python3 send_e1_gps_data.py --epsilon 10.0  # Menos privacidade

# Sem DP (apenas para teste - NÃO recomendado)
python3 send_e1_gps_data.py --no-dp
```

**O que acontece:**
1. Lê CSV com coordenadas GPS
2. Aplica ruído Laplace às coordenadas (DP)
3. Gera pseudônimo HD único por viagem
4. Envia para contrato E1RegistryGPS
5. Contrato calcula E1 e distância GPS
6. Salva resultados em `e1_gps_send_results.json`

### Passo 3: Analisar Resultados

```bash
# Ver resultados
cat e1_gps_send_results.json | python3 -m json.tool | less

# Ver estatísticas do contrato (pode usar script da implementacao1)
# ou consultar diretamente via web3
```

## 🔐 Differential Privacy

### O que é DP?

Differential Privacy garante matematicamente que a presença ou ausência de um indivíduo no dataset não pode ser inferida com certeza, adicionando ruído calibrado aos dados.

### Parâmetro Epsilon (ε)

| Epsilon | Privacidade | Ruído | Erro Aproximado |
|---------|-------------|-------|-----------------|
| 0.1 | Máxima | Alto | ±1-2 km |
| 1.0 | Moderada | Médio | ±100-200 m |
| 10.0 | Mínima | Baixo | ±10-20 m |

**Fórmula:**
```
noise ~ Laplace(0, sensitivity/ε)
privatized_value = original_value + noise
```

### Sensibilidade

- Para coordenadas GPS: sensitivity = 1.0 (1 grau)
- 1° de latitude ≈ 111 km
- 1° de longitude ≈ 111 km × cos(latitude)

## 📊 Análise de Privacidade (Opcional)

```bash
# Aplicar DP e salvar CSV para análise
python3 apply_dp.py --epsilon 1.0 --output dados_gps_dp_e1.csv

# Ver comparação entre original e DP
head -n 5 dados_gps_dp_e1.csv
```

## 🧪 Experimentos Sugeridos

### 1. Comparar diferentes epsilons

```bash
# Epsilon baixo (mais privacidade)
python3 send_e1_gps_data.py --epsilon 0.1
mv e1_gps_send_results.json results_epsilon_0.1.json

# Epsilon médio
python3 send_e1_gps_data.py --epsilon 1.0
mv e1_gps_send_results.json results_epsilon_1.0.json

# Epsilon alto (menos privacidade)
python3 send_e1_gps_data.py --epsilon 10.0
mv e1_gps_send_results.json results_epsilon_10.0.json
```

### 2. Analisar utilidade dos dados

Compare:
- Distância GPS calculada pelo contrato vs distância real
- Valores E1 (não afetados pelo DP das coordenadas)
- Erro de localização introduzido pelo DP

### 3. Visualizar no mapa (futuro)

- Plotar coordenadas originais vs DP
- Verificar se DP mantém padrões gerais mas protege localização exata

## 🔑 Diferenças da Implementação 1

| Aspecto | Implementação 1 | Implementação 2 |
|---------|----------------|----------------|
| GPS | ❌ Não | ✅ Sim |
| Differential Privacy | ❌ Não | ✅ Sim |
| Pseudônimos HD | ✅ Sim | ✅ Sim |
| Cálculo E1 | ✅ On-chain | ✅ On-chain |
| Distância GPS | ❌ Não | ✅ On-chain |
| Uso | Produção | Pesquisa/PoC |
| Complexidade | Simples | Avançado |
| Custo Gas | Menor | Maior |

## ⚠️ Limitações

### Proof-of-Concept

- Não auditado para produção
- Cálculo de distância GPS simplificado (não usa Haversine completo)
- DP aplicado independentemente a cada coordenada (pode melhorar)

### Privacidade

- DP protege coordenadas, mas padrões podem revelar informações
- Pseudônimos podem ser linkados se VIN for exposto
- Requer análise de composição para múltiplas queries

### Performance

- Mais gas que Implementação 1 (devido a GPS)
- Estruturas maiores (GPSLocation)

## 🔬 Trabalhos Futuros

### Fase 3: DP + ZKP

- Zero-Knowledge Proofs para provar distância sem revelar coordenadas
- DP apenas como backup
- Máxima privacidade + verificabilidade

### Melhorias DP

- Geometric noise para coordenadas (mais apropriado que Laplace)
- DP diferencial por região (sensibilidade variável)
- Composição de privacidade entre viagens

### Melhorias Contrato

- Haversine completo (requer biblioteca math)
- Validação de coordenadas (lat: -90 a 90, lon: -180 a 180)
- Pagamento automatizado por distância GPS

## 📚 Referências

### Differential Privacy
- Dwork & Roth (2014): "The Algorithmic Foundations of Differential Privacy"
- Andrés et al. (2013): "Geo-indistinguishability: differential privacy for location-based systems"

### Blockchain + Privacy
- Zyskind et al. (2015): "Decentralizing Privacy: Using Blockchain to Protect Personal Data"
- Kosba et al. (2016): "Hawk: The Blockchain Model of Cryptography and Privacy-Preserving Smart Contracts"

## 💡 Dicas

1. **Comece com epsilon = 1.0** para balancear privacidade e utilidade
2. **Compare resultados** entre diferentes epsilons
3. **Analise o CSV gerado** por apply_dp.py antes de enviar
4. **Documente seus experimentos** para papers futuros
5. **Considere ZKP** para privacidade máxima (Fase 3)

## 🐛 Troubleshooting

### "Não conectado ao Besu"
```bash
# Verificar se Besu está rodando
curl http://localhost:8545 -X POST -H "Content-Type: application/json" --data '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}'
```

### "Erro de compilação do contrato"
```bash
# Instalar solc correto
pip install py-solc-x
python3 -c "from solcx import install_solc; install_solc('0.8.0')"
```

### "Gas insuficiente"
- Aumente o gas limit em `deploy_e1_gps.py` (linha do build_transaction)

## 📞 Suporte

Para dúvidas sobre esta implementação, consulte:
- [CONTEXTO_PROJETO.md](../CONTEXTO_PROJETO.md) - Visão geral
- [../implementacao1/](../implementacao1/) - Implementação base

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
