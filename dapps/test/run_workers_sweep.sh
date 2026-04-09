#!/usr/bin/env bash
set -euo pipefail

# Executa benchmarks sequenciais variando NumWorkers em um arquivo Go de teste.
# Exemplo:
#   ./dapps/test/run_workers_sweep.sh dapps/test/test_e1/send_e1.go
#
# Variaveis opcionais:
#   WORKERS="2 4 8 16 32 64 128 256 512 1024"
#   CONTINUE_ON_ERROR=1

TARGET_GO_FILE="${1:-test_e1/send_e1.go}"
CONST_NAME="NumWorkers"
WORKERS_LIST="${WORKERS:-2 4 8 16 32 64 128 256 512 1024}"
CONTINUE_ON_ERROR="${CONTINUE_ON_ERROR:-0}"

if [[ ! -f "$TARGET_GO_FILE" ]]; then
  echo "Arquivo nao encontrado: $TARGET_GO_FILE" >&2
  exit 1
fi

RUN_DIR="$(dirname "$TARGET_GO_FILE")"
GO_FILE="$(basename "$TARGET_GO_FILE")"
RESULTS_DIR="$RUN_DIR/results_sweep"
mkdir -p "$RESULTS_DIR"

# Backup/restaura o arquivo para nao deixar alteracoes permanentes.
BACKUP_FILE="$(mktemp)"
cp "$TARGET_GO_FILE" "$BACKUP_FILE"
restore_original() {
  cp "$BACKUP_FILE" "$TARGET_GO_FILE"
  rm -f "$BACKUP_FILE"
}
trap restore_original EXIT

set_workers_value() {
  local workers="$1"

  # Substitui a linha da constante nWorkers mantendo o comentario padrao.
  sed -i -E "s/^([[:space:]]*)${CONST_NAME}[[:space:]]*=.*/\1${CONST_NAME}     = ${workers} \/\/ Numero de workers paralelos/" "$TARGET_GO_FILE"

  if ! grep -qE "^[[:space:]]*${CONST_NAME}[[:space:]]*=[[:space:]]*${workers}[[:space:]]" "$TARGET_GO_FILE"; then
    echo "Falha ao atualizar ${CONST_NAME} para ${workers} em $TARGET_GO_FILE" >&2
    exit 1
  fi
}

echo "============================================================"
echo "Sweep de workers"
echo "Arquivo: $TARGET_GO_FILE"
echo "Valores: $WORKERS_LIST"
echo "Resultados em: $RESULTS_DIR"
echo "============================================================"

for workers in $WORKERS_LIST; do
  echo
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Iniciando com ${workers} workers"

  set_workers_value "$workers"

  log_file="$RESULTS_DIR/run_${workers}w_$(date '+%Y%m%d_%H%M%S').log"

  start_ts="$(date +%s)"
  set +e
  (
    cd "$RUN_DIR"
    go run "$GO_FILE"
  ) 2>&1 | tee "$log_file"
  run_status=${PIPESTATUS[0]}
  set -e
  end_ts="$(date +%s)"

  duration=$((end_ts - start_ts))
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Finalizado ${workers} workers | status=${run_status} | duracao=${duration}s"
  echo "Log: $log_file"

  if [[ "$run_status" -ne 0 && "$CONTINUE_ON_ERROR" != "1" ]]; then
    echo "Execucao interrompida por erro. Use CONTINUE_ON_ERROR=1 para continuar mesmo com falha." >&2
    exit "$run_status"
  fi
done

echo
echo "Sweep concluido com sucesso."
