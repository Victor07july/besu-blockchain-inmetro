# Mass Benchmark - exemplos de uso

Este guia mostra exemplos de comandos para o script:
contracts/privacy/implementacao_offset_zkp/scripts/mass_benchmark.py

Use chaves e seed de exemplo apenas para testes locais. Nao use chaves reais em ambiente publico.

## Variaveis de ambiente (script)

Obrigatorias por cenario:
- BENCH_USER_PRIVATE_KEY: chave privada para cenario direct
- BENCH_PSEUDONYM_PRIVATE_KEY ou BENCH_PSEUDONYM_SEED_FILE (+ BENCH_PSEUDONYM_HD_INDEX): para cenarios pseudonym/direct_pseudonym
- BENCH_REDEEM_PRIVATE_KEY (ou BENCH_USER_PRIVATE_KEY): para cenario redeem

Opcionais:
- BENCH_DEPLOYMENT_FILE: caminho do deployment_info.json
- BENCH_ORACLE_URL: URL do oraculo (padrao http://127.0.0.1:5001)
- BENCH_MIN_VALUE_MICRO: minimo para oraculo quando monetizacao = 0
- BENCH_DIRECT_MIN_VALUE_MICRO: minimo para envio direto quando monetizacao = 0
- BENCH_GAS_LIMIT: gas limit (padrao 900000)
- BENCH_RECEIPT_TIMEOUT: timeout do receipt (segundos, padrao 180)
- BENCH_REDEEM_LIMIT: limita quantidade de resgates no cenario redeem

Observacao:
- BENCH_ORACLE_OPTION_INDEX existe no codigo, mas o script escolhe a opcao com MAIOR valor automaticamente.

## Variaveis de ambiente (oraculo)

Para o oraculo (scripts/oraculo.py):
- ORACLE_DEPLOYMENT_FILE
- ORACLE_PRIVATE_KEY
- ORACLE_ZKP_ENABLED (0/1)
- ORACLE_ZKP_DIR (opcional)

## Exemplo: direct

Edite SCENARIOS no script para incluir "direct".

export BENCH_USER_PRIVATE_KEY=0xc87509a1c067bbde78beb793e6fa76530b6382a4c0241e5e4a9ec0a0f44dc0d3
export BENCH_DEPLOYMENT_FILE=/home/inmetro/besu-starter-victor/contracts/privacy/implementacao_offset_zkp/deployment_info.json

python3 /home/inmetro/besu-starter-victor/contracts/privacy/implementacao_offset_zkp/scripts/mass_benchmark.py

## Exemplo: pseudonym com private key

Edite SCENARIOS no script para incluir "pseudonym" ou "direct_pseudonym".

export BENCH_PSEUDONYM_PRIVATE_KEY=0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d
export BENCH_DEPLOYMENT_FILE=/home/inmetro/besu-starter-victor/contracts/privacy/implementacao_offset_zkp/deployment_info.json

python3 /home/inmetro/besu-starter-victor/contracts/privacy/implementacao_offset_zkp/scripts/mass_benchmark.py

## Exemplo: pseudonym com seed (mnemonic)

Crie um arquivo de seed (exemplo):

cat > /home/inmetro/seed.txt << 'EOF'
orange canvas mirror soccer island pencil hazard forum update orbit lemon asset
EOF

export BENCH_PSEUDONYM_SEED_FILE=/home/inmetro/seed.txt
export BENCH_PSEUDONYM_HD_INDEX=0
export BENCH_DEPLOYMENT_FILE=/home/inmetro/besu-starter-victor/contracts/privacy/implementacao_offset_zkp/deployment_info.json

python3 /home/inmetro/besu-starter-victor/contracts/privacy/implementacao_offset_zkp/scripts/mass_benchmark.py

## Exemplo: oracle/offset

Edite SCENARIOS no script para incluir "oracle".

export BENCH_ORACLE_URL=http://127.0.0.1:5001
export BENCH_MIN_VALUE_MICRO=1
export BENCH_DEPLOYMENT_FILE=/home/inmetro/besu-starter-victor/contracts/privacy/implementacao_offset_zkp/deployment_info.json

python3 /home/inmetro/besu-starter-victor/contracts/privacy/implementacao_offset_zkp/scripts/mass_benchmark.py

## Exemplo: oracle + redeem em massa

Edite SCENARIOS no script para incluir "oracle" e depois "redeem".
O redeem usa os poseidon_root gerados no mesmo run.

export BENCH_ORACLE_URL=http://127.0.0.1:5001
export BENCH_MIN_VALUE_MICRO=1
export BENCH_REDEEM_PRIVATE_KEY=0xc87509a1c067bbde78beb793e6fa76530b6382a4c0241e5e4a9ec0a0f44dc0d3
export BENCH_REDEEM_LIMIT=0
export BENCH_DEPLOYMENT_FILE=/home/inmetro/besu-starter-victor/contracts/privacy/implementacao_offset_zkp/deployment_info.json

python3 /home/inmetro/besu-starter-victor/contracts/privacy/implementacao_offset_zkp/scripts/mass_benchmark.py

## Resultados

Os CSVs sao gerados em:
- test/results/benchmark_results.csv
- test/results/benchmark_summary.csv

Cada linha inclui tempos, gas usado, status, e1 antes/depois e metricas agregadas.
