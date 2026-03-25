# Map Matching: Por que a API encontra o mesmo nó para pontos diferentes?

## Como OSMnx representa as ruas

A rede viária não é contínua — é um **grafo de nós e arestas discretos**:

```
Rua real (contínua):
════════════════════════════════════

OSMnx (nós discretos):
═══N1═══════N2═══════N3═══════N4═══
   ↑         ↑         ↑         ↑
  Nó        Nó        Nó        Nó
```

Os nós só existem em:
- Cruzamentos de ruas
- Curvas acentuadas
- Início/fim de rua

## O problema: colapso de nós

O GPS do SUMO gera muitos pontos (um por segundo). A rede viária tem muito menos nós:

```
GPS points (muitos, a cada 1 segundo):
• • • • • • • • • • • • • •   (40 pontos em 400m)

OSMnx nodes (poucos, apenas cruzamentos):
═══N1═══════════════════N2═══
   ↑                    ↑
  100m                 300m
  (só 2 nós nesse trecho!)
```

Quando se usa `ox.nearest_nodes()`, cada ponto GPS busca o **nó mais próximo**:

```
P1  → N1  (mais próximo)
P2  → N1  (ainda mais próximo que N2)
P3  → N1  ← DUPLICATA!
P4  → N1  ← DUPLICATA!
P5  → N2  (agora N2 ficou mais próximo)
P6  → N2  ← DUPLICATA!
```

Resultado: vários pontos colapsam para o mesmo nó → distância calculada = 0 km.

## A solução: `nearest_edges` com projeção geométrica

Em vez de buscar o **nó** mais próximo, projeta o ponto na **aresta** (linha da rua) mais próxima:

```python
# RUIM: snap para nó (poucos, criam duplicatas)
node = ox.nearest_nodes(G, lon, lat)

# MELHOR: snap para ARESTA (projeta na geometria da rua)
u, v, key = ox.distance.nearest_edges(G, X=lon, Y=lat)
projected_point = edge_geom.interpolate(edge_geom.project(point))
```

Resultado: cada ponto é projetado em uma posição **única ao longo da rua**:

```
GPS points:  • • • • • • • • • •
             ↓ ↓ ↓ ↓ ↓ ↓ ↓ ↓ ↓ ↓
Rua:        ═P1═P2═P3═P4═P5═P6══  ✅ Posições únicas!
```

## Algoritmo de busca por ponto único (fallback)

Mesmo com `nearest_edges`, em casos raros dois pontos podem colapsar para a mesma posição projetada. Para isso, o script implementa uma busca iterativa:

1. **Detecta duplicata**: verifica se o ponto já existe no conjunto
2. **Busca em 8 direções** com raio crescente (5.5m, 11m, 16.5m... até ~110m):
   - Norte, Sul, Leste, Oeste, NE, SE, NW, SW
3. **Re-snap**: para cada ponto tentado, aplica `snap_to_nearest_road()` de volta para a rua
4. **Aceita** o primeiro ponto que resultar em posição única

```
Antes:  P1 P2 P3 P3 P4 P3 P5   ← Duplicatas!
Depois: P1 P2 P3 P3' P4 P3'' P5  ← Cada um em posição única na rua ✅
```

## Impacto no cálculo de distância

Este script usa **dual array**:

| Array | Map Matching | Uso |
|-------|-------------|-----|
| `trajectory_points_orig` | ❌ Não | Pontos GPS originais |
| `trajectory_points_offset` | ❌ Não | Pontos com offset (geometria preservada) |
| `trajectory_points_priv` | ✅ Sim | Pontos armazenados (blockchain/CSV) |

A distância é calculada com **Haversine** sobre `trajectory_points_priv` (COM snap), garantindo que:
- Distância calculada = distância dos pontos armazenados (**consistência**)
- Sem atalhos artificiais do routing OSMnx
