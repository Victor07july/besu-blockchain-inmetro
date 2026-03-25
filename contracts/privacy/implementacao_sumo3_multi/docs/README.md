# implementacao_sumo4

Guia de execução do processamento SUMO com offset e análise de distância/pontos.

## Arquivo principal

- Script: ../scripts/process_sumo_csv_osmnx _harversine.py

Observação: o nome do arquivo contém espaço antes de _harversine.py.

## O que o script faz

- Seleciona o veículo alvo assim:
	- usa `veh0` se existir no CSV,
	- senão usa o primeiro `vehicle_id` disponível,
	- opcionalmente permite fixar um `vehicle_id` via CLI.
- Gera offset aleatório dentro de um raio máximo (max_radius_km).
- Aplica map matching (quando habilitado).
- Calcula e salva:
	- distância do trajeto original e com offset,
	- diferença de distância absoluta e percentual,
	- número de pontos do trajeto original e com offset,
	- diferença de pontos absoluta e percentual.
- Executa N vezes (num_runs), gerando um offset novo a cada execução.

## Uso

python3 "../scripts/process_sumo_csv_osmnx _harversine.py" <input.csv> [output.csv] [consumo_fabricante] [row_step] [max_radius_km] [num_runs] [vehicle_id]

### Modo lote paralelo (diretório)

python3 "../scripts/process_sumo_csv_osmnx _harversine.py" <input_dir> [output_dir] [consumo_fabricante] [row_step] [max_radius_km] [num_runs] [vehicle_id]

### Parâmetros

- input.csv: arquivo de entrada (obrigatório)
- output.csv: CSV consolidado de saída (opcional)
- consumo_fabricante: km/l (padrão 12.0)
- row_step: processa 1 a cada N linhas (padrão 1)
- max_radius_km: raio máximo do offset aleatório (padrão 2.0)
- num_runs: quantidade de execuções com offset aleatório (padrão 100)
- vehicle_id: ID do veículo alvo (opcional)
	- se não informar, o script faz auto-detect (`veh0` ou primeiro disponível)

No modo lote, o script usa automaticamente 1 worker por CSV de entrada.

## Exemplos práticos

### 1) Rodar apenas 1 vez

python3 "../scripts/process_sumo_csv_osmnx _harversine.py" ../data/vehicles_step.csv ../data/trips_once.csv 12.0 1 2.0 1

### 2) Rodar com offset aleatório 100 vezes

python3 "../scripts/process_sumo_csv_osmnx _harversine.py" ../data/vehicles_step.csv ../data/trips_100.csv 12.0 1 2.0 100

### 3) Rodar com offset aleatório 1000 vezes

python3 "../scripts/process_sumo_csv_osmnx _harversine.py" ../data/vehicles_step.csv ../data/trips_1000.csv 12.0 1 2.0 1000

### 4) Rodar forçando um vehicle_id específico (ex.: carro_1000)

python3 "../scripts/process_sumo_csv_osmnx _harversine.py" ../data/vehicles_step_sim_1.csv ../data/offset_force/sim_1.csv 12.0 1 2.0 100 carro_1000

### 5) Processar todos os CSVs da pasta data, 100 vezes cada, com workers

python3 "../scripts/process_sumo_csv_osmnx _harversine.py" ../data ../data/offset_batch_results 12.0 1 2.0 100 carro_1000

Esse comando:

- encontra automaticamente os CSVs de entrada na pasta;
- cria tarefas no formato arquivo x execução (ex.: 10 x 100 = 1000 tarefas);
- processa em paralelo com 1 worker por CSV;
- salva os resultados por arquivo e por execução.

## E se eu quiser offset fixo?

No estado atual, não existe argumento de linha de comando para passar offset_x e offset_y fixos.

Você tem duas opções:

- Opção A (mais simples): rodar com num_runs=1.
	- Vai gerar 1 offset aleatório e executar uma vez.

- Opção B (fixo de verdade): editar o script para retornar um par fixo em generate_random_offset(...).
	- Exemplo de ideia: retornar sempre o mesmo offset_x e offset_y.
	- Útil para comparar rodadas com exatamente o mesmo deslocamento.

## Arquivos gerados

Se output.csv for ../data/trips_sumo_processed.csv, o script também gera:

- ../data/trips_sumo_processed_trajectories.json
- ../data/trips_sumo_processed_distance_analysis.csv

No modo lote paralelo (input_dir), o script gera:

- ../data/offset_batch_results/<nome_do_csv>/run_001.csv
- ../data/offset_batch_results/<nome_do_csv>/run_002.csv
- ...
- ../data/offset_batch_results/all_runs_consolidated.csv
- ../data/offset_batch_results/all_runs_trajectories.json
- ../data/offset_batch_results/all_runs_distance_analysis.csv

## Dicas rápidas

- Para debug rápido: use num_runs=1 e row_step maior.
- Para experimento estatístico: use num_runs alto (100, 500, 1000).
- Se aparecer CSV sem `veh0`, não precisa editar script: use `vehicle_id` no comando ou deixe auto-detect.
- Se quiser manter o comportamento atual de não descartar pontos, deixe FORCE_UNIQUE_POINTS conforme sua configuração atual.
