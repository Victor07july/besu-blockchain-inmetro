# Comparação entre os Scripts de Processamento SUMO

## Scripts

| Script | Arquivo |
|--------|---------|
| **Routing** | `process_sumo_csv_osmnx.py` |
| **Haversine** | `process_sumo_csv_osmnx _harversine.py` |

---

## Diferença principal: Como calcula a distância do trajeto

### Routing (`process_sumo_csv_osmnx.py`)

Usa `calculate_trajectory_distance_with_routing()`:

```
trajectory_points_offset (SEM snap)
         ↓
   filter_close_points()     (remove pontos < 10m)
         ↓
   ox.nearest_nodes()        (snap para nó mais próximo)
         ↓
   ox.shortest_path()        (rota mais curta entre nós)
         ↓
   Soma comprimento das arestas
```

### Haversine (`process_sumo_csv_osmnx _harversine.py`)

Usa `calculate_trajectory_distance()`:

```
trajectory_points_priv (COM snap)
         ↓
   Haversine entre pontos consecutivos  (linha reta no globo)
         ↓
   Soma das distâncias
```

---

## Comparação detalhada

| Aspecto | Routing | Haversine |
|---------|---------|-----------|
| **Função de distância** | `calculate_trajectory_distance_with_routing()` | `calculate_trajectory_distance()` |
| **Pontos usados no cálculo** | `trajectory_points_offset` (SEM snap) | `trajectory_points_priv` (COM snap) |
| **Segue ruas** | Sim (OSMnx routing) | Não (linha reta) |
| **API OpenStreetMap** | Sim (para routing) | Sim (apenas para map matching) |
| **Filtro de pontos próximos** | Sim (< 10m removidos) | Não |
| **Consistência pontos/distância** | Pontos armazenados != pontos do cálculo | Pontos armazenados = pontos do cálculo |
| **Risco de atalhos** | Alto (routing encontra caminhos mais curtos) | Nenhum |
| **Velocidade** | Lento (routing por segmento) | Rápido (só matemática) |
| **Resultado típico** | ~211m (-46% vs SUMO) | ~1237m (depende do map matching) |

---

## Fluxo completo dos pontos

Ambos os scripts mantêm **três arrays** ao longo do processamento:

```
GPS Original
    |
    +-> trajectory_points_orig      (sem offset, sem snap)
    |
    v
Aplicar Offset (+x graus, +y graus)
    |
    +-> trajectory_points_offset    (com offset, SEM snap)
    |         |
    |         +-> ROUTING usa este array
    |
    v
Map Matching (snap to road)
    |
    +-> trajectory_points_priv      (com offset, COM snap)
              |
              +-> HAVERSINE usa este array
```

---

## Quando usar cada um

### Use Routing quando:
- Quer simular distância como GPS real faria (seguindo ruas)
- Comparar com distância SUMO (que também segue ruas)
- Cuidado: pode gerar atalhos artificiais

### Use Haversine quando:
- Quer consistência entre pontos armazenados e distância calculada
- Prioriza velocidade de processamento
- Não precisa que a distância siga o traçado exato das ruas

---

## Problema identificado com Routing

O routing OSMnx pode encontrar **atalhos** (caminhos mais curtos via ruas paralelas), resultando em distâncias menores que o trajeto real:

```
Trajeto real SUMO:
A ===>===>===>===> B  (392m seguindo rua especifica)

Routing OSMnx:
A ===>===+
         |  <- Atalho por rua paralela!
         +======> B  (211m)
```

Resultado observado:
- SUMO: 392m
- Routing: 211m (-46%)
- Haversine: varia conforme map matching

Isso faz a distância parecer menor que a realidade, prejudicando o calculo de CO2.
