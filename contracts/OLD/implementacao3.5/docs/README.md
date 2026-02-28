# 🔒 Privacidade Diferencial para Coordenadas GPS com Map Matching

Sistema completo de proteção de privacidade para coordenadas GPS de veículos, garantindo que os dados protegidos permaneçam em vias trafegáveis antes do envio para blockchain (Hyperledger Besu).

## 📋 Índice

1. [Visão Geral](#visão-geral)
2. [Arquitetura](#arquitetura)
3. [Instalação](#instalação)
4. [Uso Rápido](#uso-rápido)
5. [Detalhamento das Etapas](#detalhamento-das-etapas)
6. [Configuração](#configuração)
7. [Exemplos](#exemplos)
8. [Troubleshooting](#troubleshooting)

---

## 🎯 Visão Geral

Este sistema implementa **Privacidade Diferencial (DP)** em coordenadas GPS com **Map Matching**, garantindo que:

- ✅ As coordenadas originais dos veículos são protegidas matematicamente
- ✅ O ruído aplicado é calibrado pelo parâmetro ε (epsilon)
- ✅ As coordenadas protegidas permanecem em vias trafegáveis (não caem em prédios, rios, etc.)
- ✅ Os dados mantêm utilidade para análises e monetização
- ✅ Integração direta com contratos Solidity no Hyperledger Besu

### Arquivos Principais

```
implementacao3.5/
├── differential_privacy_gps.py    # Pipeline completo de DP + Map Matching
├── send_to_blockchain.py          # Envio para o contrato via Web3.py
├── install_dependencies.sh        # Script de instalação
├── requirements.txt               # Dependências Python
├── E1RegistryGPS.sol             # Contrato Solidity
├── deploy_e1_gps.py              # Deploy do contrato
└── README.md                      # Esta documentação
```

---

## 🏗️ Arquitetura

### Pipeline de Processamento

```
┌─────────────────┐
│  CSV Original   │  Coordenadas GPS reais
│  (start/end)    │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│  ETAPA 1: Preparação do Ambiente                            │
│  • Download da malha viária (OSMnx)                         │
│  • Raio de busca: 1km ao redor do ponto                     │
│  • Cache de grafos para reutilização                        │
└────────┬────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│  ETAPA 2: Aplicação de Ruído Estatístico                    │
│  • Mecanismo de Laplace (diffprivlib ou PyDP)               │
│  • Parâmetro ε (epsilon) configurável                       │
│  • Ruído independente em lat/lon                            │
│  • Resultado: coordenada "ruidosa"                          │
└────────┬────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│  ETAPA 3: Map Matching (Snap to Road)                       │
│  • Busca do nó/aresta mais próximo no grafo                 │
│  • Projeção da coordenada ruidosa para via trafegável       │
│  • Resultado: coordenada protegida + válida                 │
└────────┬────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│  ETAPA 4: Validação e Exportação                            │
│  • Cálculo de deslocamento (distância original → protegida) │
│  • Métricas de utilidade (velocidade, distância)            │
│  • Exportação para CSV com coordenadas protegidas           │
└────────┬────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────┐
│  Blockchain     │  Envio via Web3.py para Hyperledger Besu
│  (Besu + Web3)  │
└─────────────────┘
```

---

## 🚀 Instalação

### Pré-requisitos

- **Python 3.8+**
- **pip3**
- **Hyperledger Besu** rodando localmente ou remotamente

### Instalação Automática

```bash
cd /home/victor/besu-starter-victor/contracts/privacy/implementacao3.5

# Executar script de instalação
./install_dependencies.sh
```

O script irá:
1. ✅ Criar ambiente virtual Python
2. ✅ Instalar todas as dependências do `requirements.txt`
3. ✅ Verificar instalação dos pacotes críticos
4. ✅ Instalar compilador Solidity 0.8.19

### Instalação Manual

```bash
# Criar ambiente virtual
python3 -m venv venv
source venv/bin/activate

# Instalar dependências
pip install -r requirements.txt

# Instalar Solidity compiler
python3 -c "from solcx import install_solc; install_solc('0.8.19')"
```

### Dependências Principais

| Pacote | Função |
|--------|--------|
| `pandas` | Manipulação de dados |
| `osmnx` | Download de malhas viárias do OpenStreetMap |
| `networkx` | Manipulação de grafos (redes viárias) |
| `diffprivlib` | Privacidade diferencial (IBM) |
| `web3` | Interação com blockchain Ethereum/Besu |
| `py-solc-x` | Compilador Solidity |

---

## ⚡ Uso Rápido

### 1. Processar CSV com Privacidade Diferencial

```bash
# Ativar ambiente virtual
source venv/bin/activate

# Processar dados (exemplo com 10 primeiras linhas)
python3 differential_privacy_gps.py \
    dados_monetizacao_novas_emissões_etanol_original_gas_1720_v2.csv \
    0.5 \
    10
```

**Parâmetros:**
- `arquivo.csv`: CSV de entrada com colunas `start_location` e `end_location`
- `0.5`: Valor de epsilon (ε) - quanto menor, mais privado
- `10`: Número de linhas a processar (opcional, omitir para processar todas)

**Saída:**
- Arquivo `dados_..._private.csv` com colunas adicionais:
  - `start_lat_private`, `start_lon_private`
  - `end_lat_private`, `end_lon_private`
  - `start_displacement_m`, `end_displacement_m`
  - `gps_distance_private_km`
  - `dp_epsilon`, `dp_processed`

### 2. Deploy do Contrato (se necessário)

```bash
python3 deploy_e1_gps.py
```

**Saída:**
- Arquivo `e1_gps_contract_address.json` com:
  - Endereço do contrato
  - ABI
  - Configurações de conexão

### 3. Enviar Dados para Blockchain

```bash
python3 send_to_blockchain.py \
    dados_monetizacao_novas_emissões_etanol_original_gas_1720_v2_private.csv \
    e1_gps_contract_address.json
```

**Saída:**
- Transações enviadas ao Besu
- Arquivo `dados_..._blockchain_results.csv` com hashes das transações

---

## 🔬 Detalhamento das Etapas

### ETAPA 1: Preparação do Ambiente e Extração do Contexto Geográfico

**Objetivo:** Obter a malha viária ao redor da coordenada original.

```python
# Exemplo de código
from differential_privacy_gps import DifferentialPrivacyGPS

dp = DifferentialPrivacyGPS(epsilon=0.5, search_radius=1000)
G = dp.get_road_network(lat=-5.8431, lon=-35.1976)
```

**Detalhes:**
- Utiliza biblioteca **osmnx** para baixar dados do OpenStreetMap
- `network_type='drive'`: Apenas vias trafegáveis por veículos
- Raio padrão: **1 km** (configurável)
- **Cache local** evita downloads repetidos da mesma região

**Trade-offs:**
- ✅ Raio maior = mais opções de projeção, melhor map matching
- ❌ Raio maior = download mais lento, maior uso de memória

### ETAPA 2: Geração e Aplicação do Ruído Estatístico

**Objetivo:** Proteger a coordenada exata com ruído calibrado.

```python
# Aplicar ruído Laplaciano
lat_noisy, lon_noisy = dp.add_differential_privacy(lat=-5.8431, lon=-35.1976)
```

**Mecanismo de Laplace:**

$$
\text{Noise} \sim \text{Lap}\left(\frac{\Delta f}{\varepsilon}\right)
$$

Onde:
- $\Delta f$ = sensibilidade (0.001° ≈ 111 metros)
- $\varepsilon$ = parâmetro de privacidade

**Valores típicos de ε:**

| ε | Privacidade | Deslocamento Típico |
|---|------------|---------------------|
| 0.1 | Muito alta | ~1.1 km |
| 0.5 | Alta | ~220 m |
| 1.0 | Moderada | ~110 m |
| 2.0 | Baixa | ~55 m |

**Bibliotecas suportadas:**
1. **diffprivlib** (IBM) - recomendado
2. **PyDP** (Google)
3. Implementação manual (fallback)

### ETAPA 3: Map Matching (Processamento de Vínculo)

**Objetivo:** "Puxar" a coordenada ruidosa para a via trafegável mais próxima.

```python
# Snap para via
lat_snapped, lon_snapped, node_id = dp.snap_to_nearest_road(
    G, lat_noisy, lon_noisy
)
```

**Algoritmo:**
1. Busca do **nó mais próximo** no grafo usando distância euclidiana
2. Retorna coordenadas exatas do nó na via
3. Garante que o ponto está sempre em uma rua válida

**Vantagens:**
- ✅ Mantém coerência geográfica
- ✅ Dados úteis para contratos inteligentes
- ✅ Não expõe localização exata

### ETAPA 4: Validação e Exportação

**Métricas calculadas:**

1. **Deslocamento (displacement):** Distância entre ponto original e protegido
   ```python
   displacement_m = haversine(lat_orig, lon_orig, lat_private, lon_private)
   ```

2. **Distância da viagem (protegida):**
   ```python
   trip_distance = haversine(start_private, end_private)
   ```

3. **Taxa de sucesso:** Porcentagem de viagens processadas sem erros

---

## ⚙️ Configuração

### Parâmetros do Script de DP

Editar diretamente em `differential_privacy_gps.py`:

```python
# Privacidade
EPSILON = 0.5  # Menor = mais privado

# Geografia
SEARCH_RADIUS = 1000  # Metros - raio de busca da malha viária
```

### Configuração do Blockchain

Criar arquivo `e1_gps_contract_address.json`:

```json
{
  "rpc_url": "http://localhost:8545",
  "contract_address": "0x...",
  "oracle_private_key": "0x...",
  "contract_abi": [...]
}
```

**Segurança:** ⚠️ **NUNCA** commitar chaves privadas no Git!

---

## 📊 Exemplos

### Exemplo 1: Processar Amostra para Teste

```bash
# Processar apenas 5 viagens com epsilon = 0.3
python3 differential_privacy_gps.py \
    dados_monetizacao_novas_emissões_etanol_original_gas_1720_v2.csv \
    0.3 \
    5
```

**Saída esperada:**
```
======================================================================
🔒 PROCESSAMENTO DE PRIVACIDADE DIFERENCIAL GPS
======================================================================
📄 Arquivo de entrada: dados_monetizacao_novas_emissões_etanol_original_gas_1720_v2.csv
📄 Arquivo de saída: dados_monetizacao_novas_emissões_etanol_original_gas_1720_v2_private.csv
🔐 Epsilon (ε): 0.3
📏 Raio de busca: 1000m
======================================================================

📊 Carregando dados...
   Processando amostra: 5 viagens

🔄 Iniciando processamento...
----------------------------------------------------------------------

[1/5] VIN: 93XATGK1WSCR19187

🚗 Processando viagem:
   Origem: (-5.843199, -35.197724)
   Destino: (-5.843128, -35.197571)

📍 Processando coordenada de início...
🗺️  Baixando malha viária ao redor de (-5.843199, -35.197724)...
✓ Grafo carregado: 245 nós, 512 arestas

📍 Processando coordenada de destino...

✓ Viagem processada:
   Deslocamento início: 187.3m
   Deslocamento fim: 142.8m
   Distância viagem (privada): 5.921km
...
```

### Exemplo 2: Pipeline Completo

```bash
# 1. Instalar dependências
./install_dependencies.sh

# 2. Processar dados
source venv/bin/activate
python3 differential_privacy_gps.py dados.csv 0.5 100

# 3. Deploy do contrato (primeira vez)
python3 deploy_e1_gps.py

# 4. Enviar para blockchain
python3 send_to_blockchain.py dados_private.csv e1_gps_contract_address.json
```

### Exemplo 3: Análise de Privacidade

```python
import pandas as pd

# Carregar dados processados
df = pd.read_csv('dados_private.csv')

# Estatísticas de deslocamento
print(f"Deslocamento médio: {df['start_displacement_m'].mean():.1f}m")
print(f"Deslocamento máximo: {df['start_displacement_m'].max():.1f}m")
print(f"Deslocamento mínimo: {df['start_displacement_m'].min():.1f}m")

# Visualizar distribuição
import matplotlib.pyplot as plt
df['start_displacement_m'].hist(bins=30)
plt.xlabel('Deslocamento (metros)')
plt.ylabel('Frequência')
plt.title(f'Distribuição de Deslocamento (ε={df["dp_epsilon"].iloc[0]})')
plt.show()
```

---

## 🐛 Troubleshooting

### Erro: "Não foi possível conectar ao nó Besu"

**Solução:**
```bash
# Verificar se Besu está rodando
curl -X POST --data '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}' \
  http://localhost:8545

# Iniciar Besu (se necessário)
cd /home/victor/besu-starter-victor
./run.sh
```

### Erro: "osmnx.errors.InsufficientResponseError"

**Causa:** Área sem dados do OpenStreetMap ou raio muito pequeno.

**Solução:**
```python
# Aumentar raio de busca
dp = DifferentialPrivacyGPS(epsilon=0.5, search_radius=2000)
```

### Erro: "No module named 'diffprivlib'"

**Solução:**
```bash
source venv/bin/activate
pip install diffprivlib
```

### Coordenadas com deslocamento muito grande

**Causa:** Epsilon muito baixo.

**Solução:** Aumentar epsilon (menos privacidade, menos ruído):
```bash
python3 differential_privacy_gps.py dados.csv 1.0
```

### Transações falhando no blockchain

**Verificar:**
1. Saldo suficiente na conta oracle
2. Gas price adequado
3. Nonce correto
4. Contrato deployado corretamente

```bash
# Verificar saldo
curl -X POST --data '{"jsonrpc":"2.0","method":"eth_getBalance","params":["0x...", "latest"],"id":1}' \
  http://localhost:8545
```

---

## 📚 Referências

### Privacidade Diferencial
- Dwork, C., & Roth, A. (2014). *The Algorithmic Foundations of Differential Privacy*
- [diffprivlib Documentation](https://diffprivlib.readthedocs.io/)
- [Google's Differential Privacy Library](https://github.com/google/differential-privacy)

### Map Matching e OSM
- [OSMnx Documentation](https://osmnx.readthedocs.io/)
- Boeing, G. (2017). *OSMnx: New methods for acquiring, constructing, analyzing, and visualizing complex street networks*

### Blockchain
- [Web3.py Documentation](https://web3py.readthedocs.io/)
- [Hyperledger Besu Documentation](https://besu.hyperledger.org/)

---

## 📝 Licença

MIT License - Sinta-se livre para usar e modificar.

---

## 👤 Autor

**Victor**  
Data: 2026-02-09  
Implementação: 3.5 - Privacidade Diferencial GPS com Map Matching

---

## 🤝 Contribuindo

Sugestões e melhorias são bem-vindas! Áreas para contribuição:

1. **Otimização de performance:** Cache mais eficiente de grafos
2. **Algoritmos alternativos:** Gaussian mechanism, Exponential mechanism
3. **Visualização:** Dashboard interativo de privacidade
4. **Métricas avançadas:** Análise de utilidade vs privacidade

---

**🎯 Próximos Passos Recomendados:**

1. ✅ Executar `install_dependencies.sh`
2. ✅ Processar amostra pequena (5-10 viagens) para teste
3. ✅ Analisar métricas de deslocamento
4. ✅ Ajustar epsilon conforme necessidade
5. ✅ Processar dataset completo
6. ✅ Deploy do contrato no Besu
7. ✅ Enviar dados protegidos para blockchain
