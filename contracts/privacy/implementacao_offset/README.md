## Implementacao Offset - Oraculo de Privacidade

Este modulo executa o fluxo de oraculo confiavel para privacidade:

1. Le trajetorias com pandas
2. Gera varias tentativas de offset aleatorio
3. Calcula a diferenca percentual de distancia para cada tentativa
4. Escolhe a melhor tentativa (mais proxima do alvo informado)
5. Gera hash SHA-256 da trajetoria original para auditoria futura
6. Salva trajetoria privada e metadados
7. Opcional: envia resultado para blockchain por um modulo separado

### Arquivos

- `scripts/oraculo.py`: logica principal do oraculo (com pandas)
- `scripts/blockchain_sender.py`: envio on-chain desacoplado

### Dependencias

Obrigatorias:

- `pandas`
- `web3`
- `eth-account`

Opcionais (map matching):

- `osmnx`
- `shapely`

### Exemplo de execucao (somente oraculo)

```bash
cd contracts/privacy/implementacao_offset/scripts
python3 oraculo.py \
	../../implementacao_sumo3_multi/data/vehicles_step_sim_1.csv \
	--target-privacy-percent 15 \
	--attempts 100 \
	--max-radius-km 2.0 \
	--output-dir ../data/oraculo_offset
```

### Exemplo com map matching

```bash
python3 oraculo.py \
	../../implementacao_sumo3_multi/data/vehicles_step_sim_1.csv \
	--target-privacy-percent 15 \
	--attempts 100 \
	--max-radius-km 2.0 \
	--enable-map-matching \
	--search-radius-m 1500
```

### Exemplo com envio para blockchain

Use `--method-arg` para mapear argumentos do metodo do contrato.

Argumento literal: `--method-arg texto_fixo`

Argumento vindo do resultado JSON: `--method-arg $.audit.original_hash_sha256`

```bash
python3 oraculo.py \
	../../implementacao_sumo3_multi/data/vehicles_step_sim_1.csv \
	--target-privacy-percent 15 \
	--attempts 100 \
	--send-onchain \
	--deployment-file ../deployment_info.json \
	--private-key 0xSUA_CHAVE \
	--method-name registerOracleResult \
	--method-arg $.vehicle_id \
	--method-arg $.audit.original_hash_sha256 \
	--method-arg $.trajectory.private_json
```

### Saidas

- `oraculo_resultados.json`: estrutura completa por veiculo, incluindo tentativas
- `oraculo_resumo.csv`: resumo da melhor tentativa por veiculo
- `oraculo_trajectories.json`: trajetos no formato compativel com `visualize_trips.py`
- `oraculo_distance_analysis.csv`: analise de diferenca de distancia (original vs offset)

Observacao de comparacao SUMO:
- O oraculo agora tenta extrair distancia acumulada SUMO de forma robusta (`max` numerico) quando a coluna `distance` existir no CSV.
- Quando disponivel, os arquivos de saida incluem comparacoes:
	- `Distancia_SUMO_km`

