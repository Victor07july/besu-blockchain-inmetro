# Visualização de Trajetos com Privacidade Diferencial

## 📋 Nova funcionalidade

Agora o sistema guarda **todos os pontos intermediários** do trajeto (não apenas início e fim), permitindo visualizar a rota completa percorrida pelo veículo no mapa.

## 🔄 Fluxo de trabalho

### 1. Processar dados SUMO

```bash
python3 process_sumo_csv.py ../data/carro_1000.csv trips_sumo.csv 12.0
```

Isso vai gerar **2 arquivos**:
- `trips_sumo.csv` - Dados agregados para blockchain (igual antes)
- `trips_sumo_trajectories.json` - Trajetos completos para visualização (NOVO!)

### 2. Visualizar no mapa

```bash
# Instalar dependência (primeira vez)
pip install folium

# Criar mapa interativo
python3 visualize_trips.py trips_sumo_trajectories.json mapa.html
```

### 3. Abrir no navegador

```bash
# Abrir o arquivo HTML gerado
xdg-open mapa.html  # Linux
# ou simplesmente clique duplo no arquivo
```

## 🗺️ O que o mapa mostra

### Camadas (controláveis)
- 🔴 **Trajeto Original** - Rota real percorrida (linha vermelha conectando todos os pontos)
- 🔵 **Trajeto com DP** - Rota com privacidade diferencial (linha azul)
- 📏 **Linhas de Deslocamento** - Setas mostrando quanto cada ponto se moveu
- ℹ️ **Informações** - Cards com resumo da viagem (CO2, distância, valor E1)
- 📍 **Pontos Intermediários** - Marcadores em cada segmento (opcional)

### Marcadores
- 🔴 **Círculo vermelho** - Início da viagem (original)
- 🟠 **Círculo laranja** - Fim da viagem (original)
- 🔵 **Círculo azul** - Início da viagem (com DP)
- 🟦 **Círculo ciano** - Fim da viagem (com DP)

### Interatividade
- Clique nos marcadores/linhas para ver detalhes
- Use o controle de camadas para mostrar/ocultar elementos
- Ferramenta de medição para calcular distâncias
- Minimap no canto inferior esquerdo
- Fullscreen disponível

## 📊 Estatísticas mostradas

O script calcula automaticamente:
- **Deslocamento médio** de todos os pontos
- **Deslocamento máximo** encontrado
- **Total de pontos** processados
- Distribuição estatística (média, mediana, min, max, desvio)

## 🎯 Exemplo prático

```bash
# Processar 1000 linhas do SUMO (de 5 em 5 para ser mais rápido)
python3 process_sumo_csv.py ../data/carro_1000.csv trips.csv 12.0 5

# Visualizar apenas um veículo específico
python3 visualize_trips.py trips_trajectories.json mapa.html SUMO_carro_1000

# Visualizar todos os veículos
python3 visualize_trips.py trips_trajectories.json mapa_completo.html
```

## 🔐 Privacidade Diferencial aplicada

O sistema aplica:
1. **Ruído Laplaciano** (ε=0.5) em CADA ponto do trajeto
2. **Map Matching** para projetar em ruas reais (OSMnx)
3. **Cache** de malhas viárias para performance

Cada ponto é protegido individualmente, garantindo privacidade do trajeto completo!

## 📁 Arquivos gerados

| Arquivo | Propósito | Usado por |
|---------|-----------|-----------|
| `trips_sumo.csv` | Dados agregados | Blockchain (send_sumo_to_blockchain.py) |
| `trips_sumo_trajectories.json` | Trajetos completos | Visualização (visualize_trips.py) |
| `mapa.html` | Mapa interativo | Navegador web |

## 🚀 Dicas

- **Performance**: Use `ROW_STEP` > 1 para processar menos linhas (mais rápido)
- **Detalhes**: Ative a camada "Pontos Intermediários" para ver cada segmento
- **Comparação**: Deixe ambas as camadas (Original + DP) ativas para comparar lado a lado
- **Zoom**: O mapa se ajusta automaticamente para mostrar todos os trajetos

## 🔧 Troubleshooting

**"Linha reta ao invés de trajeto"**
- ✅ Resolvido! Agora usa todos os pontos intermediários

**"Mapa muito lento"**
- Use `ROW_STEP` maior (processar menos linhas)
- Desative camada "Pontos Intermediários"

**"OSMnx demorando muito"**
- Normal na primeira execução (baixando mapas)
- Execuções seguintes são rápidas (cache)
