# 🗺️ Map Matching no process_obd_euclidean.py

## O que mudou?

Agora o script **garante que as coordenadas protegidas estejam em vias trafegáveis**!

### Antes (sem map matching):
```
Coordenada original → + Ruído → Pode cair no mar/prédios ❌
```

### Agora (com map matching):
```
Coordenada original → + Ruído → Snap to road → Via trafegável ✅
```

---

## 🚀 Como usar

### 1. Instalar dependências

```bash
pip install osmnx networkx scikit-learn
```

Ou:
```bash
pip install -r requirements.txt
```

### 2. Executar com map matching (padrão)

```bash
python3 process_obd_euclidean.py ../data/OBDLink.csv trips.csv VEHICLE_001 0.5 12.0
```

O map matching está **ATIVADO por padrão**.

---

## ⚙️ Configuração

No topo do script `process_obd_euclidean.py`:

```python
# Map matching
ENABLE_MAP_MATCHING = True   # True: Aplicar snap to road | False: Apenas ruído
SEARCH_RADIUS = 1000         # Raio de busca da malha viária (metros)
```

### Desabilitar map matching

Se você não quiser usar map matching (mais rápido, mas menos preciso):

```python
ENABLE_MAP_MATCHING = False
```

### Ajustar raio de busca

Para áreas com poucas ruas, aumente o raio:

```python
SEARCH_RADIUS = 2000  # 2km
```

---

## 📊 Saída do CSV

Novas colunas adicionadas:

| Coluna | Descrição |
|--------|-----------|
| `start_map_matched` | `True` se snap to road funcionou no início |
| `end_map_matched` | `True` se snap to road funcionou no fim |

---

## 🔍 Como verificar se funcionou?

No output do script, procure:

```
🗺️  Map matching: ATIVADO (raio 1000m)

...

   🔐 PRIVACIDADE DIFERENCIAL (ε=0.5):
   📍 Start Original:  (-5.843199, -35.197724)
   🔒 Start Protegido: (-5.842891, -35.197156) ✓ MAP MATCHED
   📏 Deslocamento:    87.3 metros
```

O **`✓ MAP MATCHED`** indica que a coordenada foi projetada para uma via válida.

Se aparecer **`⚠ SEM MAP MATCHING`**, significa que:
- Não há malha viária disponível naquela região
- osmnx não está instalado
- Map matching está desabilitado

---

## 🐛 Troubleshooting

### "osmnx não instalado"

```bash
pip install osmnx networkx scikit-learn
```

### "Erro ao baixar grafo"

**Causa:** Área sem dados do OpenStreetMap ou sem conexão internet.

**Solução:**
1. Verificar conexão com internet
2. Aumentar `SEARCH_RADIUS`
3. Testar em área urbana conhecida

### Coordenadas ainda caem em locais inválidos

Se `start_map_matched = False`, o snap to road falhou. Possíveis causas:
- Coordenada original em área sem ruas (meio do campo, mar)
- Raio de busca muito pequeno
- Erro no download do grafo

**Solução:** Aumentar `SEARCH_RADIUS` ou verificar coordenadas originais.

---

## 🎯 Comparação de Desempenho

| Modo | Tempo por viagem | Precisão geográfica |
|------|------------------|---------------------|
| Sem map matching | ~0.1s | ⚠️ Baixa (pode cair em qualquer lugar) |
| Com map matching | ~2-5s | ✅ Alta (sempre em via válida) |

**Recomendação:** Use map matching em produção para garantir dados válidos.

---

## 💡 Dicas

1. **Cache automático:** Grafos são salvos em memória. Coordenadas próximas reutilizam o mesmo grafo.

2. **Processamento em lote:** Se processar muitas viagens na mesma região, o cache torna o map matching muito mais rápido.

3. **Epsilon vs Map Matching:** 
   - Epsilon baixo (0.1-0.3) = mais privacidade, mais deslocamento
   - Map matching sempre garante resultado em via válida

---

**Victor | 2026-03-02**
