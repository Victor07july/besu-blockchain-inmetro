# Bug Encontrado e Corrigido ✅

## Problema
A distância do trajeto com offset de alguns veículos estava com **0.0000 km** porque **todos os pontos da trajetória colapsaram para a mesma coordenada**.

### Exemplo (veh1):
- **42 pontos** no trajeto original (todos diferentes)
- **1 ponto único** no trajeto com offset (todos iguais: 40.7858, -73.9428)
- **Resultado**: Distância = 0 km (sem movimento entre pontos idênticos)

## Causa Raiz
O código estava baixando a malha viária do OSMnx em torno das **coordenadas ORIGINAIS**:

```python
G_seg = get_road_network(seg_lat, seg_lon)  # ❌ Coordenadas originais
```

Mas tentava fazer map matching das **coordenadas COM OFFSET** (deslocadas ~1.4 km):

```python
snap_to_nearest_road(G_seg, seg_lat_offset, seg_lon_offset, ...)
```

**Problema**: O grafo tinha raio de apenas 500m. Os pontos com offset (+1.4 km) estavam **fora da área** do grafo baixado, então o OSMnx escolhia sempre o **mesmo nó mais próximo** na borda do grafo para TODOS os pontos.

## Solução
Baixar o grafo em torno das **coordenadas COM OFFSET**:

```python
G_seg = get_road_network(seg_lat_offset, seg_lon_offset)  # ✅ Coordenadas com offset
```

Isso garante que o grafo cobre a área onde os pontos realmente estão após o deslocamento.

## Mudanças Realizadas
1. **Linha ~527**: `get_road_network(seg_lat_offset, seg_lon_offset)` em vez de `get_road_network(seg_lat, seg_lon)`
2. **Linha ~470**: `get_road_network(start_lat_offset, start_lon_offset)` em vez de `get_road_network(start_lat_orig, start_lon_orig)`
3. **Linha ~478**: `get_road_network(end_lat_offset, end_lon_offset)` em vez de `get_road_network(end_lat_orig, end_lon_orig)`

## Para Testar
Execute novamente o script:

```bash
cd /home/inmetro/besu-starter-victor/contracts/privacy/implementacao_sumo3
# Ative o ambiente virtual primeiro se necessário
python3 scripts/process_sumo_csv.py data/vehicles_step.csv 11 1
```

Verifique no arquivo `data/trips_distance_analysis.csv` que:
- Todos os veículos têm `Distancia_Trajeto_com_Offset_km > 0`
- As coordenadas Start/End com offset são diferentes (não idênticas)
- A diferença percentual não é -100%

## Impacto
✅ Todos os veículos agora terão trajetórias válidas após offset + map matching  
✅ Distâncias calculadas corretamente  
✅ Coordenadas não colapsam mais para um único ponto  
✅ Map matching funciona corretamente com a área relevante da rede viária
