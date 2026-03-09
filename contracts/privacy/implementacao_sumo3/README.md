# 🚗 Implementação SUMO v3 - Offset Determinístico

## 📌 Visão Geral

Esta versão implementa **offset determinístico** para privacidade de localização, substituindo a privacidade diferencial probabilística da v2.

### 🆚 Diferenças da v2:

| Característica | Implementação v2 | Implementação v3 |
|---------------|------------------|------------------|
| **Método** | Privacidade Diferencial (Laplace) | Offset Determinístico |
| **Aleatoriedade** | Sim (ruído probabilístico) | Não (deslocamento fixo) |
| **Reversibilidade** | Não (ruído não pode ser removido) | Sim (aplicar offset inverso) |
| **Consistência** | Diferentes em cada execução | Sempre igual com mesma chave |
| **Chave** | Epsilon (ε) | Offset (x, y) |
| **Limitação** | Não tem limite superior | Raio máximo com clipping |

## 🔑 Conceitos-Chave

### Offset Determinístico
```python
lat_encrypted = lat_original + offset_x
lon_encrypted = lon_original + offset_y
```

- **offset_x**: Deslocamento em graus de latitude (1° ≈ 111 km)
- **offset_y**: Deslocamento em graus de longitude (varia com latitude)
- **Chave simétrica**: Para reverter, basta aplicar offset negativo

### Clipping de Raio

Se o deslocamento ultrapassar o raio máximo, é **reduzido proporcionalmente**:

```python
Se distância(offset_x, offset_y) > max_radius_km:
    scale = max_radius_km / distância
    offset_x_final = offset_x * scale
    offset_y_final = offset_y * scale
```

**Vantagens**:
- Preserva a **direção** do deslocamento
- Garante limite de privacidade
- Sempre respeita raio máximo

### Map Matching

Após o offset, as coordenadas são projetadas para a via trafegável mais próxima (snap to road).

## 📂 Estrutura

```
implementacao_sumo3/
├── scripts/
│   ├── process_sumo_csv.py    # Processamento com offset determinístico
│   └── visualize_trips.py     # Visualização (igual v2)
├── data/                       # Saída de arquivos processados
└── README.md                   # Este arquivo
```

## 🚀 Como Usar

### 1. Processar dados SUMO

```bash
cd scripts/

# Uso básico (offset padrão: 0.01°, raio: 2km, roteamento: True)
python3 process_sumo_csv.py ../data/carro_1000.csv

# Personalizar offset e usar roteamento OSMnx (padrão)
python3 process_sumo_csv.py ../data/carro_1000.csv ../data/trips.csv 12.0 1 0.02 0.02 3.0 True
#                           input                output            cons step  x    y   raio  routing

# Desabilitar roteamento (mais rápido, menos preciso)
python3 process_sumo_csv.py ../data/carro_1000.csv ../data/trips.csv 12.0 1 0.02 0.02 3.0 False
```

**Parâmetros**:
- `offset_x`: Deslocamento latitude (graus). Ex: 0.01 ≈ 1.1 km
- `offset_y`: Deslocamento longitude (graus). Ex: 0.01 ≈ 1.0 km (varia)
- `max_radius_km`: Raio máximo em km. Ex: 2.0
- `use_routing`: True = calcula distâncias seguindo ruas (📍 **recomendado para CO2**), False = Haversine simples

### Cálculo de Distâncias: Roteamento vs Haversine

A implementação oferece dois métodos para calcular distâncias de trajetórias:

#### 🗺️ Roteamento OSMnx (Padrão - `use_routing=True`)

**Como funciona:**
- Para cada par de pontos consecutivos, encontra a **rota mais curta seguindo as ruas reais**
- Usa `ox.shortest_path()` do OSMnx para calcular caminho na rede viária
- Soma o comprimento de todas as arestas (ruas) do percurso

**Vantagens:**
- ✅ **Distâncias realistas** (segue curvas e voltas das ruas)
- ✅ **Mais próximo do SUMO** (que também simula na rede viária)
- ✅ **Melhor para cálculos de CO2** (distância precisa = emissão precisa)
- ✅ Fallback automático para Haversine se rota não for encontrada

**Desvantagens:**
- ⏱️ Mais lento (1-2 minutos vs 10 segundos para datasets pequenos)
- 💾 Baixa grafos OSMnx da região (usa cache para otimizar)

**Exemplo de output:**
```
🗺️ Cálculo de distância: Roteamento OSMnx (segue ruas)
🗺️ veh0: Roteamento - Original: 38/39 (fallback: 1), Offset: 40/40 (fallback: 0)
```

#### 📏 Haversine Simples (`use_routing=False`)

**Como funciona:**
- Calcula distância **em linha reta** (great circle) entre pontos consecutivos
- Usa fórmula de Haversine (geodésica)

**Vantagens:**
- ⚡ Muito rápido
- 📦 Não precisa baixar grafos OSMnx

**Desvantagens:**
- ❌ "Corta caminho" nas curvas das ruas
- ❌ Distâncias podem diferir significativamente do SUMO
- ❌ CO2 calculado pode ser impreciso

**Quando usar cada método:**
- **Roteamento (True)**: Análise de CO2, monetização de créditos, produção
- **Haversine (False)**: Testes rápidos, desenvolvimento, quando velocidade é crítica

### 2. Visualizar trajetos

```bash
# Gera um HTML para cada veículo em ../data/
python3 visualize_trips.py ../data/trips_sumo_processed_trajectories.json
```

**Saída**: Um arquivo HTML por veículo (`trip_SUMO_veh0.html`, etc.)

## 📊 Exemplo de Saída

```
🚗 PROCESSAMENTO SUMO → E1 REGISTRY (OFFSET DETERMINÍSTICO)
======================================================================
📄 Entrada: ../data/carro_1000.csv
🔑 Offset X (latitude): 0.01° (1.11 km)
🔑 Offset Y (longitude): 0.01° (varia com latitude)
⭕ Raio máximo: 2.0 km
📏 Distância do offset (aprox): 1.57 km

🚙 Veículo: SUMO_veh0
   Modelo: passenger
   🔑 OFFSET DETERMINÍSTICO (x=0.01°, y=0.01°, max=2.0km):
   📍 Start Original:  (-22.908123, -43.196789)
   🔒 Start Protegido: (-22.898123, -43.186789) ✓ 1.57 km | ✓ MAP MATCHED
   📏 Deslocamento final: 1572.3 metros
```

**Se offset ultrapassar raio**:
```
   🔒 Start Protegido: (-22.900000, -43.188000) ⚠️ CLIPPED 3.45→2.00 km | ✓ MAP MATCHED
```

## ⚠️ Avisos de Clipping

O sistema automaticamente avisa quando offsets são reduzidos:

```
⭕ CLIPPING DE RAIO:
   Offsets aplicados: 1,250
   Offsets reduzidos (clipped): 87 (7.0%)
   ⚠️ AVISO: 87 pontos ultrapassaram o raio de 2.0 km e foram ajustados
```

## 🔐 Reversibilidade

Para recuperar coordenadas originais (em teoria):

```python
# Criptografar
lat_encrypted = lat_original + offset_x
lon_encrypted = lon_original + offset_y

# Descriptografar
lat_recovered = lat_encrypted - offset_x
lon_recovered = lon_encrypted - offset_y
```

**Limitação**: Se map matching foi aplicado, não é perfeitamente reversível (erro de alguns metros).

## 🆔 Diferenças Técnicas

### Configurações (vs. v2)

```python
# V2 (Privacidade Diferencial)
EPSILON = 0.5
SENSITIVITY = 0.0001

# V3 (Offset Determinístico)
OFFSET_X = 0.01
OFFSET_Y = 0.01
MAX_RADIUS_KM = 2.0
```

### Funções Principais

- `calculate_offset_distance()`: Calcula distância do deslocamento
- `clip_offset_to_radius()`: Limita offset ao raio máximo
- `apply_deterministic_offset()`: Aplica offset com clipping

## 📈 Casos de Uso

**Use v3 quando**:
- ✅ Precisar de offset **consistente** entre execuções
- ✅ Precisar **reverter** o deslocamento futuramente
- ✅ Quiser controlar **direção** do deslocamento
- ✅ Precisar de **limite garantido** de privacidade

**Use v2 quando**:
- ✅ Precisar de **máxima privacidade** (aleatoriedade)
- ✅ Proteção contra ataques de **inferência**
- ✅ Conformidade com **DP-guarantee** formal

## 🔧 Configurações Recomendadas

### Alta Privacidade
```bash
python3 process_sumo_csv.py input.csv output.csv 12.0 1 0.02 0.02 2.0
# Offset: ~2.2 km, Raio máximo: 2 km
```

### Média Privacidade
```bash
python3 process_sumo_csv.py input.csv output.csv 12.0 1 0.01 0.01 2.0
# Offset: ~1.5 km, Raio máximo: 2 km (padrão)
```

### Baixa Privacidade
```bash
python3 process_sumo_csv.py input.csv output.csv 12.0 1 0.005 0.005 1.0
# Offset: ~0.7 km, Raio máximo: 1 km
```

## 📝 Notas

- Map matching garante que pontos sempre caem em vias trafegáveis
- Clipping preserva a direção, apenas reduz magnitude
- Offset é aplicado a **todos os pontos** do trajeto
- JSON de saída é compatível com visualize_trips.py da v2

## 🔗 Links Relacionados

- **Implementação v2**: `../implementacao_sumo/` (Privacidade Diferencial)
- **Implementação Original**: `../implementacao_obdcontract3/` (Qualidade + DP)
