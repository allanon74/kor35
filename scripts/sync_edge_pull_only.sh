#!/usr/bin/env bash
set -euo pipefail

# Loop di sincronizzazione pull-only dal Master al DB locale.
# Uso:
#   ./scripts/sync_edge_pull_only.sh
# Variabili opzionali:
#   SYNC_INTERVAL_SECONDS=60
#   PYTHON_BIN=python3

SYNC_INTERVAL_SECONDS="${SYNC_INTERVAL_SECONDS:-60}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

if ! [[ "$SYNC_INTERVAL_SECONDS" =~ ^[0-9]+$ ]]; then
  echo "SYNC_INTERVAL_SECONDS deve essere un intero positivo."
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

echo "Avvio sync pull-only ogni ${SYNC_INTERVAL_SECONDS}s (Ctrl+C per fermare)..."

while true; do
  echo ""
  echo "[$(date --iso-8601=seconds)] Eseguo pull dal Master..."
  if "$PYTHON_BIN" manage.py sync_edge_node --pull-only; then
    echo "[$(date --iso-8601=seconds)] Pull completato."
  else
    echo "[$(date --iso-8601=seconds)] Pull fallito (ritento al prossimo ciclo)." >&2
  fi
  sleep "$SYNC_INTERVAL_SECONDS"
done
