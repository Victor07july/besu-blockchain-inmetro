# Mass Benchmark - exemplos de uso

Este guia mostra exemplos de comandos para o script:
`contracts/privacy/implementacao_offset_zkp/scripts/mass_benchmark.py`

Use chaves e seed de exemplo apenas para testes locais. Nao use chaves reais em ambiente publico.

---

## Cenarios disponiveis

| Cenario | Descricao |
|---|---|
| `direct` | Envia tx com a chave real do usuario |
| `pseudonym` | Envia tx com chave pseudonima (indice HD incrementa a cada tx) |
| `direct_pseudonym` | Igual ao `pseudonym` (mesmo comportamento no codigo atual) |
| `oracle` | Fluxo completo via API do oraculo (processar + confirmar opcao) |
| `redeem` | Resgata saldo ZK usando a chave real do usuario |
| `redeem_pseudonym` | Resgata saldo ZK usando chave pseudonima (indice HD incrementa a cada tx) |

Edite a variavel `SCENARIOS` no script para escolher quais cenarios executar:

```python
SCENARIOS = ["oracle", "redeem"]
```

---

## Variaveis de ambiente

### Obrigatorias por cenario

| Variavel | Cenario |
|---|---|
| `BENCH_USER_PRIVATE_KEY` | `direct`, fallback do `redeem` |
| `BENCH_PSEUDONYM_PRIVATE_KEY` ou `BENCH_PSEUDONYM_SEED_FILE` | `pseudonym`, `direct_pseudonym`, `redeem_pseudonym` |
| `BENCH_PSEUDONYM_HD_INDEX` | `pseudonym`, `direct_pseudonym`, `redeem_pseudonym` (padrao: 0) |
| `BENCH_REDEEM_PRIVATE_KEY` | `redeem` (se nao definido, usa `BENCH_USER_PRIVATE_KEY`) |

### Comportamento do pseudonimo

| Configuracao | Comportamento |
|---|---|
| Apenas `BENCH_PSEUDONYM_PRIVATE_KEY` | Chave fixa para todas as txs, sem incremento |
| Apenas `BENCH_PSEUDONYM_SEED_FILE` | Deriva via HD wallet; indice incrementa a cada tx |
| Os dois definidos | `BENCH_PSEUDONYM_PRIVATE_KEY` tem prioridade; seed file e ignorado |

Quando usando seed file, o indice real usado em cada tx e:
```
indice_atual = BENCH_PSEUDONYM_HD_INDEX + (numero_da_tx - 1)
```

Exemplo com `BENCH_PSEUDONYM_HD_INDEX=0` e 3 txs:
- tx 1 → indice 0 → endereco A
- tx 2 → indice 1 → endereco B
- tx 3 → indice 2 → endereco C

### Opcionais

| Variavel | Descricao | Padrao |
|---|---|---|
| `BENCH_DEPLOYMENT_FILE` | Caminho do `deployment_info.json` | `implementacao_offset_zkp/deployment_info.json` |
| `BENCH_ORACLE_URL` | URL da API do oraculo | `http://127.0.0.1:5001` |
| `BENCH_MIN_VALUE_MICRO` | Minimo para oraculo quando monetizacao = 0 | `1` |
| `BENCH_DIRECT_MIN_VALUE_MICRO` | Minimo para envio direto quando monetizacao = 0 | `0` |
| `BENCH_GAS_LIMIT` | Gas limit por tx | `900000` |
| `BENCH_RECEIPT_TIMEOUT` | Timeout aguardando recibo (segundos) | `180` |
| `BENCH_REDEEM_LIMIT` | Limita quantidade de resgates (0 = sem limite) | `0` |

> `BENCH_ORACLE_OPTION_INDEX` existe no codigo mas nao e usado — o script escolhe automaticamente a opcao com maior valor.

---

## Variaveis de ambiente do oraculo

Para o oraculo (`scripts/oraculo.py`):

| Variavel | Descricao |
|---|---|
| `ORACLE_DEPLOYMENT_FILE` | Caminho do deployment |
| `ORACLE_PRIVATE_KEY` | Chave privada do oraculo |
| `ORACLE_ZKP_ENABLED` | Ativa ZKP (`0` ou `1`) |
| `ORACLE_ZKP_DIR` | Diretorio ZKP (opcional) |

---

## Colunas medidas por tx

| Coluna | Descricao |
|---|---|
| `tx_seconds` | Tempo ate o oraculo responder HTTP (`confirmar_opcao`) ou tempo total da tx |
| `tx_wait_seconds` | Tempo que o oraculo esperou a confirmacao da blockchain |
| `gas_used` | Gas consumido pela tx |
| `effective_gas_price` | Preco efetivo do gas |
| `tx_fee_wei` | Taxa total paga em wei |
| `oracle_process_seconds` | Tempo do `/processar_trajeto` (so cenario `oracle`) |
| `oracle_confirm_seconds` | Tempo do `/confirmar_opcao` (so cenario `oracle`) |
| `zk_proof_seconds` | Tempo de geracao da prova ZK (lado cliente, so cenario `redeem`/`redeem_pseudonym`) |
| `pseudonym_gen_seconds` | Tempo de derivacao do pseudonimo via HD wallet (so quando usando seed file) |
| `e1_original_micro` / `e1_after_micro` | Valor E1 antes e depois do offset (em micro-BRL) |
| `throughput_tps` | Txs bem-sucedidas / tempo total do cenario (metrica end-to-end conservadora) |

---

## Exemplos

### direct

```bash
export BENCH_USER_PRIVATE_KEY=0xc87509a1c067bbde78beb793e6fa76530b6382a4c0241e5e4a9ec0a0f44dc0d3
export BENCH_DEPLOYMENT_FILE=/home/inmetro/besu-starter-victor/contracts/privacy/implementacao_offset_zkp/deployment_info.json

# SCENARIOS = ["direct"]
python3 /home/inmetro/besu-starter-victor/contracts/privacy/implementacao_offset_zkp/scripts/mass_benchmark.py
```

---

### pseudonym com chave privada direta

```bash
export BENCH_PSEUDONYM_PRIVATE_KEY=0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d
export BENCH_DEPLOYMENT_FILE=/home/inmetro/besu-starter-victor/contracts/privacy/implementacao_offset_zkp/deployment_info.json

# SCENARIOS = ["pseudonym"]
python3 /home/inmetro/besu-starter-victor/contracts/privacy/implementacao_offset_zkp/scripts/mass_benchmark.py
```

> Chave fixa — o mesmo pseudonimo e usado em todas as txs.

---

### pseudonym com seed (indice incrementado a cada tx)

Crie o arquivo de seed:

```bash
cat > /home/inmetro/seed.txt << 'EOF'
orange canvas mirror soccer island pencil hazard forum update orbit lemon asset
EOF
```

```bash
export BENCH_PSEUDONYM_SEED_FILE=/home/inmetro/seed.txt
export BENCH_PSEUDONYM_HD_INDEX=0
export BENCH_DEPLOYMENT_FILE=/home/inmetro/besu-starter-victor/contracts/privacy/implementacao_offset_zkp/deployment_info.json

# SCENARIOS = ["pseudonym"]
python3 /home/inmetro/besu-starter-victor/contracts/privacy/implementacao_offset_zkp/scripts/mass_benchmark.py
```

> Pseudonimo diferente a cada tx — indice comeca em 0 e incrementa automaticamente.

---

### oracle + redeem (carteira real)

```bash
export BENCH_ORACLE_URL=http://127.0.0.1:5001
export BENCH_MIN_VALUE_MICRO=1
export BENCH_REDEEM_PRIVATE_KEY=0xc87509a1c067bbde78beb793e6fa76530b6382a4c0241e5e4a9ec0a0f44dc0d3
export BENCH_DEPLOYMENT_FILE=/home/inmetro/besu-starter-victor/contracts/privacy/implementacao_offset_zkp/deployment_info.json

# SCENARIOS = ["oracle", "redeem"]
python3 /home/inmetro/besu-starter-victor/contracts/privacy/implementacao_offset_zkp/scripts/mass_benchmark.py
```

> O oracle roda primeiro (todos os CSVs), depois o redeem consome a fila gerada.

---

### oracle + redeem_pseudonym (pseudonimo diferente a cada resgate)

```bash
export BENCH_ORACLE_URL=http://127.0.0.1:5001
export BENCH_MIN_VALUE_MICRO=1
export BENCH_PSEUDONYM_SEED_FILE=/home/inmetro/seed.txt
export BENCH_PSEUDONYM_HD_INDEX=0
export BENCH_DEPLOYMENT_FILE=/home/inmetro/besu-starter-victor/contracts/privacy/implementacao_offset_zkp/deployment_info.json

# SCENARIOS = ["oracle", "redeem_pseudonym"]
python3 /home/inmetro/besu-starter-victor/contracts/privacy/implementacao_offset_zkp/scripts/mass_benchmark.py
```

> Cada resgate usa um pseudonimo derivado de um indice HD diferente.

---

### Aviso: redeem e redeem_pseudonym nao podem ser usados juntos

Cada `poseidonRoot` so pode ser resgatado uma vez. Se incluir `redeem` e `redeem_pseudonym` no mesmo `SCENARIOS`, o segundo cenario falhara para todos os itens pois ja foram resgatados pelo primeiro.

Para comparar os dois cenarios, execute em execucoes separadas:

```bash
# Execucao 1: gera mints e resgata com carteira real
# SCENARIOS = ["oracle", "redeem"]

# Execucao 2: gera novos mints e resgata com pseudonimo
# SCENARIOS = ["oracle", "redeem_pseudonym"]
```

---

## Interrupcao

Se cancelar com `Ctrl+C`, o script salva automaticamente um summary parcial com todas as txs concluidas ate o momento. A tx que estava em execucao no momento do cancelamento nao e incluida. O cenario aparece com o sufixo `_interrupted` no CSV.

---

## Resultados

Os CSVs sao gerados em:
- `test/results/benchmark_results.csv` — todas as linhas (tx + summary)
- `test/results/benchmark_summary.csv` — apenas os resumos por cenario