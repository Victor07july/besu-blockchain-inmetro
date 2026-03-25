# Oracle de Privacidade por Offset

## Objetivo

O script [contracts/privacy/implementacao_offset/scripts/oraculo.py](contracts/privacy/implementacao_offset/scripts/oraculo.py) executa um fluxo de anonimização de trajetorias por offset aleatorio, buscando aproximar uma diferenca percentual de distancia definida pelo usuario.

Resumo do que ele faz:
1. Le um CSV de trajetoria com pandas.
2. Detecta automaticamente colunas de veiculo, tempo e coordenadas.
3. Monta a trajetoria original por veiculo.
4. Gera varias tentativas de offset aleatorio.
5. Opcionalmente aplica map matching (snap to road).
6. Mede a diferenca percentual de distancia para cada tentativa.
7. Escolhe a melhor tentativa (mais proxima do alvo solicitado).
8. Gera hash SHA-256 auditavel da trajetoria original.
9. Salva JSON/CSV de resultados.
10. Opcionalmente envia para blockchain com modulo separado.

## Fluxo de decisao por limite de erro

O oracle agora possui controle de tolerancia para o alvo de privacidade:

- Parametro: `--max-target-error-percent`
- Valor padrao: `5.0`

Depois de processar as tentativas, o script calcula `error_to_target_percent` para cada veiculo. Se o melhor resultado de algum veiculo ficar acima do limite:

1. O oracle exibe um aviso detalhado com:
	 - alvo pedido,
	 - melhor diferenca encontrada,
	 - erro para o alvo,
	 - offset mais proximo encontrado.
2. Pergunta no terminal: `Deseja continuar mesmo assim? [s/N]:`
3. Se responder `s`/`sim`, continua e salva saídas.
4. Se responder `n` ou Enter, aborta a execucao sem salvar resultados finais.

## Dependencias

Obrigatorias:
- `pandas`

Opcionais para map matching:
- `osmnx`
- `shapely`

Para envio on-chain:
- `web3`
- `eth-account`

## Uso rapido

Diretorio:

```bash
cd contracts/privacy/implementacao_offset/scripts
```

Execucao basica:

```bash
python3 oraculo.py \
	../../implementacao_sumo3_multi/data/vehicles_step_sim_1.csv \
	--target-privacy-percent 15
```

Com mais tentativas e raio customizado:

```bash
python3 oraculo.py \
	../../implementacao_sumo3_multi/data/vehicles_step_sim_1.csv \
	--target-privacy-percent 20 \
	--attempts 300 \
	--max-radius-km 3.0 \
	--output-dir ../data/oraculo_offset
```

Com limite de erro mais estrito (2%):

```bash
python3 oraculo.py \
	../../implementacao_sumo3_multi/data/vehicles_step_sim_1.csv \
	--target-privacy-percent 20 \
	--max-target-error-percent 2
```

Com map matching:

```bash
python3 oraculo.py \
	../../implementacao_sumo3_multi/data/vehicles_step_sim_1.csv \
	--target-privacy-percent 15 \
	--enable-map-matching \
	--search-radius-m 1500
```

Com seed para reproducibilidade:

```bash
python3 oraculo.py \
	../../implementacao_sumo3_multi/data/vehicles_step_sim_1.csv \
	--target-privacy-percent 15 \
	--seed 42
```

## Argumentos CLI

Obrigatorio:
- `input_csv`: caminho do CSV de entrada.
- `--target-privacy-percent`: alvo de diferenca percentual absoluta entre distancia privada e original.

Processamento:
- `--attempts` (default: `100`): numero de tentativas de offset por veiculo.
- `--max-radius-km` (default: `2.0`): raio maximo para gerar offset aleatorio.
- `--vehicle-id` (default: `None`): processa apenas um veiculo especifico.
- `--seed` (default: `None`): seed aleatoria.

Map matching:
- `--enable-map-matching`: ativa snap para malha viaria (se dependencias existirem).
- `--search-radius-m` (default: `1500`): raio de busca do grafo viario.

Controle de qualidade do alvo:
- `--max-target-error-percent` (default: `5.0`): erro maximo tolerado entre o alvo e a melhor tentativa antes de solicitar confirmacao do usuario.

Saida:
- `--output-dir` (default: `../data/oraculo_offset`): pasta de saida.

Blockchain (opcional):
- `--send-onchain`: habilita envio para contrato.
- `--deployment-file` (default: `../deployment_info.json`): arquivo com endereco/ABI.
- `--private-key`: chave privada para assinar transacoes.
- `--method-name` (default: `registerOracleResult`): metodo do contrato.
- `--method-arg`: argumento do metodo (literal ou caminho JSON no formato `$.campo.subcampo`).

## Deteccao de colunas de entrada

O script tenta detectar automaticamente as colunas:

- Veiculo: `vehicle_id`, `veh_id`, `vehicle`, `id`, `vin`
- Tempo: `time`, `timestamp`, `start_time`, `step`
- Fim do segmento: `end_time`
- Latitude: `lat`, `latitude`, `start_lat`
- Longitude: `lon`, `lng`, `longitude`, `start_lon`
- Final do segmento: `end_lat`, `end_lon`
- Distancia acumulada SUMO: `distance`, `total_distance_km`

Observacoes:
- Se nao houver identificador de veiculo, o script usa `veh0`.
- Se nao houver latitude/longitude detectaveis, a execucao falha.
- Ordenacao de linhas usa sort estavel por tempo (`mergesort`) com desempate por ordem original.

## Como a melhor tentativa e escolhida

Para cada tentativa:
1. Gera offset aleatorio uniforme no disco de raio `max_radius_km`.
2. Aplica offset nos pontos da trajetoria.
3. Opcionalmente aplica map matching.
4. Calcula distancia original e privada por haversine.
5. Calcula:
	 - `diff_percent = ((private - original) / original) * 100`
	 - `abs_diff_percent = abs(diff_percent)`
	 - `error_to_target_percent = abs(abs_diff_percent - target_percent)`

A melhor tentativa e a de menor `error_to_target_percent`.

## Saidas geradas

No diretorio definido por `--output-dir`:

1. `oraculo_resultados.json`
- Estrutura completa por veiculo.
- Inclui todas as tentativas em `attempts`.
- Inclui hash de auditoria (`audit.original_hash_sha256`).

2. `oraculo_resumo.csv`
- Uma linha por veiculo com a melhor tentativa.
- CSV com `sep=';'` e `decimal=','`.

3. `oraculo_trajectories.json`
- Formato compativel com visualizacao de trajetos.
- Campos principais: `trajectory_original`, `trajectory_private`, `vin`, `run_id`.

4. `oraculo_distance_analysis.csv`
- Analise de distancias e alvo de privacidade.
- CSV com `sep=';'` e `decimal=','`.

## Campos relevantes de auditoria e analise

- `audit.original_hash_sha256`: hash canonico da trajetoria original.
- `privacy.target_percent`: alvo solicitado.
- `privacy.best_diff_percent`: melhor diferenca assinada (%).
- `privacy.best_abs_diff_percent`: melhor diferenca absoluta (%).
- `privacy.error_to_target_percent`: erro da melhor tentativa para o alvo.
- `distance.sumo_km`: baseline SUMO quando disponivel.
- `distance.original_km` / `distance.private_km`: distancias calculadas por haversine.

## Envio para blockchain

Exemplo:

```bash
python3 oraculo.py \
	../../implementacao_sumo3_multi/data/vehicles_step_sim_1.csv \
	--target-privacy-percent 15 \
	--send-onchain \
	--deployment-file ../deployment_info.json \
	--private-key 0xSUA_CHAVE \
	--method-name registerOracleResult \
	--method-arg $.vehicle_id \
	--method-arg $.audit.original_hash_sha256 \
	--method-arg $.trajectory.private_json
```

Regras:
- `--private-key` e obrigatorio quando `--send-onchain` estiver ativo.
- `--method-arg` precisa ser informado ao menos uma vez quando `--send-onchain` estiver ativo.

## Mensagens de erro comuns

- `Nao foi possivel identificar colunas de latitude/longitude no CSV`
	- Ajuste os nomes das colunas ou normalize o CSV.

- `Nenhum dado encontrado apos filtros`
	- Verifique `--vehicle-id` e conteudo do CSV.

- Aviso de map matching indisponivel
	- Instale `osmnx` e `shapely`, ou rode sem `--enable-map-matching`.

- Cancelamento por limite de erro-alvo
	- Ocorre quando usuario responde nao na confirmacao interativa.

## Boas praticas

- Comece com `--attempts` entre 100 e 300 para equilibrio entre qualidade e tempo.
- Use `--seed` em experimentos comparativos para reproducibilidade.
- Ajuste `--max-target-error-percent` conforme rigor exigido (menor valor = criterio mais estrito).
- Mantenha os arquivos de saida e o hash de auditoria para rastreabilidade.
