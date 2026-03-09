# Diferenças entre Distâncias SUMO e Trajetórias GPS

## Resumo

Este documento explica por que há diferenças entre as três métricas de distância calculadas no sistema:
- `Distancia_SUMO_km`: Distância reportada pela simulação SUMO
- `Distancia_Trajeto_Original_km`: Distância calculada das coordenadas GPS originais
- `Distancia_Trajeto_com_Offset_km`: Distância calculada após aplicar offset determinístico

## 1. Como cada métrica é calculada

### 1.1 Distância SUMO (`Distancia_SUMO_km`)

**Origem:** Simulação SUMO
**Método:** Odômetro virtual que acumula a distância percorrida na rede viária simulada
**Características:**
- Segue exatamente as ruas definidas na rede SUMO
- Inclui todas as curvas, voltas e detalhes da geometria das ruas
- Representa a distância "real" que o veículo percorreria na vida real
- Valor acumulado (última linha do CSV possui o total)

**Exemplo:**
```
timestep,vehicle_id,distance
0,veh0,0.0
1,veh0,15.5
2,veh0,31.2
3,veh0,45.8    ← Distancia_SUMO_km = 45.8 metros = 0.0458 km
```

### 1.2 Distância Trajeto Original (`Distancia_Trajeto_Original_km`)

**Origem:** Coordenadas GPS originais da simulação  
**Método:** Roteamento OSMnx (seguindo ruas reais) ou Haversine (linha reta)  
**Configuração:** Controlado pelo parâmetro `use_routing` (padrão: True)

#### 📍 Método 1: Roteamento OSMnx (Recomendado - `use_routing=True`)

**Como funciona:**
- Para cada par de pontos consecutivos (A→B):
  1. Faz snap dos pontos para nós da rede viária OSM
  2. Calcula rota mais curta usando `ox.shortest_path()`
  3. Soma comprimento de todas as arestas (ruas) do caminho
- Se rota não for encontrada, usa Haversine como fallback

**Características:**
- ✅ Segue **curvas e voltas das ruas reais**
- ✅ **Mais próximo do SUMO** (que também simula na rede viária)
- ✅ **Ideal para cálculos de CO2** (distância precisa)
- ⏱️ Mais lento (~1-2 minutos para datasets pequenos)

**Exemplo:**
```python
# Pontos A e B
node_A = snap_to_nearest_node(G, lat1, lon1)
node_B = snap_to_nearest_node(G, lat2, lon2)

# Encontrar rota seguindo ruas
route = ox.shortest_path(G, node_A, node_B, weight='length')

# Somar distâncias das arestas
distance = sum(edge_data['length'] for edge in route) / 1000  # m → km
```

#### 📏 Método 2: Haversine Simples (`use_routing=False`)

**Como funciona:**
- Calcula distância em **linha reta** (great circle) entre pontos GPS
- Soma as distâncias entre todos os pares de pontos consecutivos

**Características:**
- ⚡ Muito rápido
- ❌ **NÃO** considera a geometria das ruas
- ❌ Pode "cortar caminho" em curvas longas se os pontos estiverem espaçados

**Fórmula de Haversine:**
```python
def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # Raio da Terra em km
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)² + cos(lat1) * cos(lat2) * sin(dlon/2)²
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    return R * c
```

**⚠️ Comparação:**
```
Rua com curva em S:
    A-----•-----•
          |     |
          •-----B

Roteamento OSMnx:  A → • → • → • → B  = 500m (segue rua)
Haversine:         A --------→ B      = 350m (corta caminho)
```

### 1.3 Distância Trajeto com Offset (`Distancia_Trajeto_com_Offset_km`)

**Origem:** Coordenadas GPS após aplicar offset determinístico + map matching  
**Método:** Roteamento OSMnx (padrão) ou Haversine  
**Configuração:** Controlado pelo parâmetro `use_routing` (padrão: True)

**Características:**
- Aplica offset (lat + 0.01°, lon + 0.01°) em cada ponto
- Usa `osmnx.nearest_edges()` ou `nearest_nodes()` para "snappar" à rede viária real (OpenStreetMap)
- Calcula distância seguindo ruas (roteamento) ou linha reta (Haversine) entre pontos "snapped"
- Usa o **mesmo método** que Distancia_Trajeto_Original (garante comparação justa)

**Transformações aplicadas:**
```
1. Offset determinístico:
   lat_offset = lat_original + 0.01°
   lon_offset = lon_original + 0.01°

2. Clipping ao raio máximo (se necessário):
   Se distância_offset > 2.0 km:
       scale = 2.0 / distância_offset
       offset_final = offset_original * scale

3. Map matching (OSMnx):
   (lat_snap, lon_snap) = snap_to_nearest_road(lat_offset, lon_offset)

4. Cálculo Haversine:
   distancia_total = Σ haversine(ponto[i], ponto[i+1])
```

## 2. Por que as distâncias são diferentes?

### 2.1 SUMO vs Trajeto Original

#### Com Roteamento OSMnx (`use_routing=True` - Padrão)

**Comportamento esperado:**
- ✅ Distâncias **muito próximas** entre SUMO e Trajeto Original
- ✅ Ambos seguem a rede viária real
- ✅ Pequenas diferenças (< 20%) são normais devido a:
  - Diferentes algoritmos de roteamento
  - Rede SUMO vs rede OpenStreetMap (podem ter pequenas diferenças de geometria)
  - Pontos de início/fim podem "snappar" para locais ligeiramente diferentes

**Exemplo esperado:**
```
SUMO:             0.39 km (simulação na rede SUMO)
Trajeto Original: 0.42 km (roteamento OSMnx na rede OSM)
Diferença:        7.7% (aceitável)
```

#### Com Haversine (`use_routing=False`)

**Caso A: Trajeto Original MENOR que SUMO**
- Acontece quando os pontos GPS estão espaçados
- Haversine "corta caminho" nas curvas

**Exemplo visual:**
```
Rua com curva:
    A----•----•----B
         \____/
         
SUMO:      A → • → • → B  (segue a curva) = 100m
Haversine: A -----→ B     (linha reta)   = 80m
Roteamento: A → • → • → B (segue a curva) = 102m (próximo do SUMO)
```

**Caso B: Trajeto Original MAIOR que SUMO** (menos comum com Haversine)
- Pode acontecer se houver pontos GPS muito próximos criando "micro-zigue-zagues"
- Erro de amostragem ou interpolação

### 2.2 Trajeto Original vs Trajeto com Offset

**Fatores que causam diferença:**

1. **Map matching move os pontos**
   - Pontos são "snapped" para a rua mais próxima
   - Se offset move pontos para área sem ruas, OSMnx escolhe o nó/edge mais próximo
   - Pode criar pequenos "saltos" entre pontos

2. **Offset altera a geometria**
   - Offset de 0.01° ≈ 1.4 km
   - Pontos movem para uma região diferente
   - A rede viária nessa região pode ter geometria diferente

3. **Possível colapso de trajetória** (BUG que foi corrigido)
   - Se o grafo OSMnx for baixado nas coordenadas erradas
   - Todos os pontos "snappam" para o mesmo nó
   - Resultado: Distancia_Trajeto_com_Offset_km = 0.0 km
   - **✅ Corrigido:** Agora o grafo é baixado nas coordenadas offset corretas

## 3. Exemplo Prático

### Exemplo com Haversine (modo legado - `use_routing=False`)

```csv
VIN,Distancia_SUMO_km,Distancia_Trajeto_Original_km,Distancia_Trajeto_com_Offset_km
SUMO_veh0,0.3921,1.2373,1.3782
```

**Análise:**
- **SUMO = 0.39 km**: Distância real percorrida na simulação
- **Original = 1.24 km**: Haversine entre pontos GPS originais (3.15x maior!)
- **Offset = 1.38 km**: Haversine após offset + map matching (1.11x maior que Original)

**Por que Original é 3x maior que SUMO?**
- Haversine corta caminho mas ainda pode ser maior devido a:
  - Pontos GPS amostrados em locais que criam zigue-zague
  - Possível erro na conversão de unidades do SUMO (metros → km)
  - Amostragem irregular dos pontos GPS

**Por que Offset é maior que Original?**
- Map matching pode ter movido pontos para ruas diferentes
- Offset de 1.4 km alterou significativamente a localização

### Exemplo com Roteamento OSMnx (recomendado - `use_routing=True`)

```csv
VIN,Distancia_SUMO_km,Distancia_Trajeto_Original_km,Distancia_Trajeto_com_Offset_km
SUMO_veh0,0.3921,0.4256,0.4512
```

**Análise:**
- **SUMO = 0.39 km**: Distância real percorrida na simulação
- **Original = 0.43 km**: Roteamento OSMnx na rede OSM (8.5% maior)
- **Offset = 0.45 km**: Roteamento OSMnx após offset (6.0% maior que Original)

**Por que as diferenças são pequenas?**
- ✅ Ambos seguem redes viárias reais
- ✅ Algoritmos de roteamento similares (shortest path)
- ✅ Pequenas diferenças são devido a:
  - Geometria ligeiramente diferente entre rede SUMO e OSM
  - Pontos de snap podem variar alguns metros

**Por que Offset é ligeiramente maior?**
- Offset move pontos ~1.4 km
- Rede viária na região offset pode ter geometria ligeiramente diferente
- Diferença de 6% é normal e aceitável

## 4. O que é esperado vs problemático

### ✅ Comportamento Normal

#### Com Roteamento OSMnx (`use_routing=True` - Recomendado)
- **Diferenças de 5-20%** entre SUMO e Trajeto Original: NORMAL
- **Original próximo do SUMO (±15%)**: ESPERADO (ambos seguem ruas)
- **Offset próximo de Original (±10%)**: ESPERADO (mesma metodologia)
- **Diferenca_Distancia_Percentual < 20%**: IDEAL para cálculos de CO2
- **Fallbacks para Haversine ocasionais**: ACEITÁVEL (< 10% dos segmentos)

#### Com Haversine (`use_routing=False`)
- **Diferenças de 10-50%** entre SUMO e Trajeto Original: NORMAL
- **Original ligeiramente menor que SUMO**: ESPERADO (corta curvas)
- **Offset próximo de Original (±20%)**: ESPERADO (mesma metodologia)
- **Diferenca_Distancia_Percentual < 30%**: ACEITÁVEL (mas menos preciso para CO2)

### ❌ Sinais de Problema

- **Distancia_Trajeto_com_Offset_km = 0.0**: BUG crítico (trajetória colapsada)
- **Start_Lat_com_Offset == End_Lat_com_Offset**: Todos pontos no mesmo lugar
- **Diferença > 500%**: Algo muito errado na conversão ou cálculo
- **Offset muito menor que Original** (ex: 0.1 km vs 5 km): Map matching falhou

### 🔍 Como Validar

Execute o script de validação:
```bash
python3 scripts/test_fix_validation.py
```

**O script verifica:**
1. Nenhum veículo tem distância 0.0 km
2. Coordenadas start ≠ end para todos os veículos
3. Trajetórias não colapsadas (múltiplos pontos únicos)
4. Estatísticas gerais das distâncias

## 5. Fatores de Conversão

**Graus → Quilômetros:**
- 1° latitude ≈ 111.32 km (constante)
- 1° longitude ≈ 111.32 × cos(latitude) km (varia com a latitude)

**Exemplo em Nova York (lat ≈ 40.77°):**
- 0.01° latitude ≈ 1.11 km
- 0.01° longitude ≈ 0.84 km
- Distância total do offset ≈ √(1.11² + 0.84²) ≈ 1.40 km

## 6. Recomendações

### Para Análise de Dados

1. **Use SUMO como referência** quando disponível (mais preciso)
2. **Trajeto Original** é útil para validação cruzada
3. **Trajeto Offset** é o valor privado que será registrado no blockchain

### Para Detecção de Problemas

1. Sempre execute `test_fix_validation.py` após processar dados
2. Verifique se `Diferenca_Distancia_Percentual` é razoável (< 50%)
3. Inspecione visualmente os mapas HTML se houver discrepâncias grandes
4. Compare alguns trajetos com Google Maps para validação manual

### Para Ajuste de Parâmetros

Se as diferenças forem muito grandes:
- **Reduzir offset** (ex: 0.005° ao invés de 0.01°)
- **Aumentar raio do grafo OSMnx** em `get_road_network()` (padrão: 1500m)
- **Mudar método de snap**: `nearest_edges` vs `nearest_nodes`

## 7. Histórico de Bugs Corrigidos

### Bug 1: Distâncias SUMO multiplicadas
**Sintoma:** Distancia_SUMO_km era 5-18x maior que o esperado
**Causa:** `group['distance'].sum()` somava valores acumulados
**Solução:** Usar `group['distance'].iloc[-1]` (último valor = total acumulado)

### Bug 2: Trajetória colapsada (distância 0 km)
**Sintoma:** 60% dos veículos tinham Distancia_Trajeto_com_Offset_km = 0.0
**Causa:** `get_road_network(lat_original, lon_original)` baixava grafo no lugar errado
**Solução:** Usar `get_road_network(lat_offset, lon_offset)` para cobrir área correta

---

**Última atualização:** 2026-03-08  
**Implementação:** implementacao_sumo3/scripts/process_sumo_csv.py
