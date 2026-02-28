Processamento GPS com Privacidade Diferencial (explicação do código)

Visão geral
- Arquivo: `contracts/privacy/implementacao3/scripts/process_gps_dp.py`.
- Objetivo: aplicar Privacidade Diferencial (mecanismo de Laplace) a coordenadas GPS, projetar (snap) os pontos ruidosos na malha viária OSM próxima (map-matching) e recalcular distância entre os pontos projetados. A saída é um CSV que mantém utilidade (pontos em vias trafegáveis) e protege a posição exata.

Fluxo do script (etapas principais)
- Leitura: o script carrega um CSV de entrada que deve conter, no mínimo, as colunas `start_location` e `end_location` no formato "lat, lon".
- GraphCache: para cada ponto o script baixa (e cacheia) o grafo viário com `osmnx.graph_from_point((lat, lon), dist=radius, network_type='drive')` — o `radius` é configurável via CLI.
- Ruído DP: utiliza `laplace_mechanism(value, epsilon, sensitivity)` (implementado com `numpy.random.laplace`) para aplicar ruído separadamente em latitude e longitude. `scale = sensitivity / epsilon`.
- Map-matching: com o grafo OSM (do ponto ruidoso) o script encontra a aresta/nó mais próximo (`ox.distance.nearest_edges` / `nearest_nodes`) e projeta o ponto ruidoso sobre a geometria da via usando `LineString.interpolate`.
- Recalcular métricas: calcula a distância entre os pontos snapped com `haversine_km` (resultado em km).
- Escrita: grava um CSV com uma linha por viagem processada contendo as informações originais, ruidosas e snapped.

Colunas geradas no CSV de saída
- `vin`: valor de `VIN` (se presente no CSV de entrada).
- `timestamp`: valor de `start_time` (se presente).
- `total_distance_original_km`: valor numérico da coluna `total_distance` do CSV de entrada (se presente).
- `start_lat`, `start_lon`: coordenadas originais de início (graus decimais).
- `end_lat`, `end_lon`: coordenadas originais de fim (graus decimais).
- `start_noisy_lat`, `start_noisy_lon`: coordenadas de início depois de aplicar o ruído Laplace (graus).
- `end_noisy_lat`, `end_noisy_lon`: coordenadas de fim depois de aplicar o ruído Laplace (graus).
- `start_snap_lat`, `start_snap_lon`: coordenadas de início após map-matching (projetadas na via mais próxima) (graus).
- `end_snap_lat`, `end_snap_lon`: coordenadas de fim após map-matching (graus).
- `gps_distance_snapped_km`: distância entre os pontos snapped, calculada por haversine (km).

Novas colunas e comportamento de proporção
- `original_highway_km`: valor extraído da entrada para a distância em rodovia (km), se presente.
- `original_city_km`: valor extraído da entrada para a distância em área urbana (km), se presente.
- `total_distance_snapped_km`: distância recomputada ao longo da malha viária entre os pontos snapped (km). O script tenta rota pelo grafo (`networkx`/`length`); se não conseguir, usa haversine entre os pontos snapped.
- `distance_diff_km`: diferença entre `total_distance_original_km` e `total_distance_snapped_km` (km).
- `route_distance_source`: indica a fonte usada para calcular `total_distance_snapped_km` — `Gs` (grafo do ponto inicial), `Ge` (grafo do ponto final) ou `haversine_fallback`.
- `highway_distance_snapped_km` e `city_distance_snapped_km`: distribuição da `total_distance_snapped_km` preservando a mesma proporção highway/city observada no CSV original. Se o CSV original não contiver o detalhamento, o script assume proporção 50%/50%.
- `highway_diff_km` e `city_diff_km`: diferenças entre os valores originais (`original_highway_km`, `original_city_km`) e os valores `*_snapped_km` correspondentes.

Como a proporção é preservada
- O script tenta ler valores de distância por tipo de via a partir de nomes comuns de colunas (`highway_distance`, `city_distance`, `highwayDistance`, `cityDistance`, etc.). Quando encontrados, calcula-se a razão:

	highway_ratio = original_highway / (original_highway + original_city)

	Em seguida, divide `total_distance_snapped_km` em:

	highway_distance_snapped_km = total_distance_snapped_km * highway_ratio
	city_distance_snapped_km = total_distance_snapped_km * (1 - highway_ratio)

	Se não houver breakdown original, a divisão usa 50%/50% por padrão.

Parâmetros de execução (CLI)
- `--input/-i`: arquivo CSV de entrada.
- `--output/-o`: arquivo CSV de saída (opcional).
- `--epsilon/-e`: parâmetro epsilon do mecanismo Laplace (padrão `0.5`). Menor epsilon => maior privacidade e deslocamento maior.
- `--radius/-r`: raio (metros) usado para baixar o grafo OSM ao redor de cada ponto (padrão `1000`).
- `--sensitivity/-s`: sensibilidade em graus (padrão `1e-5` ≈ 1.11 m).

Observações e recomendações
- O ruído é aplicado em graus decimais; se você precisa enviar os valores para o contrato Solidity (que usa inteiros ×1e6), converta multiplicando por `1e6` e arredonde antes do envio.
- `osmnx` faz downloads da API OSM (Internet requerida). Usar `--radius` grande para muitas viagens pode consumir tempo e memória; o `GraphCache` tenta reusar grafos próximos para reduzir downloads.
- Se uma linha tiver `start_location`/`end_location` mal formatadas, ela será ignorada (o script pula a linha). Recomendo validar o CSV antes.
- A implementação usa `numpy` para o ruído Laplace. Para garantias formais de bibliotecas de DP, substitua `laplace_mechanism` por `diffprivlib` ou `PyDP` conforme necessário.

Possíveis próximos passos (se desejar que eu faça)
- (A) Adaptar a saída para gerar lat/lon como inteiros ×1e6 prontos para enviar ao contrato.
- (B) Adicionar colunas de diagnóstico: deslocamento causado pelo ruído (m) e distância entre original→snapped.
- (C) Executar um teste local com `dados_monetizacao_novas_emissões_etanol_original_gas_1720_v2.csv` para gerar um CSV exemplo.

Exemplo de execução rápida
```bash
python process_gps_dp.py --input ../dados_monetizacao_novas_emissões_etanol_original_gas_1720_v2.csv --epsilon 0.5 --radius 1000
```

Arquivo de envio (template): `contracts/privacy/implementacao3/scripts/send_to_contract.py` — ajuste RPC, chave privada, endereço do contrato e ABI antes de usar.

Fim.
