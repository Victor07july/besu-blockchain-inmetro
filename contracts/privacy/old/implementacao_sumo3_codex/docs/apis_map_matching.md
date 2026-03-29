# Comparação de APIs de Map Matching

## O problema com OSMnx `nearest_nodes`

OSMnx representa ruas como grafos com nós discretos (apenas em cruzamentos e curvas).
Quando muitos pontos GPS estão próximos, todos colapsam para o mesmo nó → distância = 0 km.

Solução adotada: usar `nearest_edges` com projeção geométrica (ver [map_matching.md](map_matching.md)).

---

## APIs disponíveis

### OSMnx (atual)
- **Custo**: Gratuito
- **Offline**: ✅ Sim
- **Map matching**: `nearest_edges` com projeção na geometria da aresta
- **Problema de nós**: Resolvido com `nearest_edges` + algoritmo de busca iterativa
- **Qualidade dos dados**: OpenStreetMap (colaborativo)
- **Complexidade de setup**: Baixa (`pip install osmnx`)

### Google Maps Roads API (`snapToRoads`)
- **Custo**: $10 / 1000 pontos
- **Offline**: ❌ Não
- **Map matching**: Geometria contínua, posição única garantida por ponto
- **Problema de nós**: ✅ Não existe — usa geometria contínua, não nós discretos
- **Interpolação automática**: ✅ Sim (parâmetro `interpolate=True`)
- **Qualidade dos dados**: Google (profissional, alta precisão)
- **Complexidade de setup**: Baixa (requer chave de API)

```python
# Exemplo de uso
response = requests.get(
    "https://roads.googleapis.com/v1/snapToRoads",
    params={
        "path": "40.7756,-73.9605|40.7754,-73.9604|...",
        "interpolate": True,
        "key": API_KEY
    }
)
```

### HERE Maps Routing API
- **Custo**: Pago (tier gratuito: 250k req/mês)
- **Offline**: ❌ Não
- **Map matching**: Dedicado para trajetórias GPS longas
- **Problema de nós**: ✅ Não existe
- **Complexidade de setup**: Baixa (requer chave de API)

### Mapbox Map Matching API
- **Custo**: Pago (tier gratuito: 300 req/mês)
- **Offline**: ❌ Não
- **Map matching**: Alta qualidade, retorna geometria suave
- **Problema de nós**: ✅ Não existe
- **Complexidade de setup**: Baixa (requer chave de API)

### OSRM (Open Source Routing Machine)
- **Custo**: Gratuito
- **Offline**: ✅ Sim (servidor próprio)
- **Map matching**: API dedicada de alta qualidade
- **Problema de nós**: ✅ Não existe
- **Complexidade de setup**: Alta (~50GB RAM para dados globais)

### Valhalla
- **Custo**: Gratuito
- **Offline**: ✅ Sim (servidor próprio)
- **Map matching**: Alta qualidade (origem Mapbox)
- **Problema de nós**: ✅ Não existe
- **Complexidade de setup**: Alta (requer servidor próprio)

---

## Tabela comparativa

| API | Custo | Offline | Duplicate Points | Qualidade | Setup |
|-----|-------|---------|-----------------|-----------|-------|
| **OSMnx** (atual) | Gratuito | ✅ | Possível (mitigado) | OSM | Baixo |
| **Google Roads** | $10/1k pts | ❌ | ✅ Nunca | Alta | Baixo |
| **HERE Maps** | Free tier | ❌ | ✅ Nunca | Alta | Baixo |
| **Mapbox** | Free tier | ❌ | ✅ Nunce | Alta | Baixo |
| **OSRM local** | Gratuito | ✅ | ✅ Nunca | OSM | Alto |
| **Valhalla local** | Gratuito | ✅ | ✅ Nunca | OSM | Alto |

---

## Recomendação para este projeto

**OSMnx com `nearest_edges`** é suficiente para fins acadêmicos com dados simulados (SUMO):
- Gratuito e offline
- Problema de duplicatas resolvido com algoritmo iterativo
- Dados OSM adequados para Nova York (área bem mapeada)

Google Roads seria a melhor opção em produção real, mas o custo não se justifica para simulações acadêmicas.
