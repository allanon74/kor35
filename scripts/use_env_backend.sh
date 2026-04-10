#!/usr/bin/env bash
set -euo pipefail

# Copia un template env backend in backend/.env.<profilo>
# e aggiorna backend/.env come link/copia per tooling locale.
#
# Uso:
#   ./scripts/use_env_backend.sh --env dev-home
#   ./scripts/use_env_backend.sh --env prod

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_DIR="$ROOT_DIR/config/env"
BACKEND_DIR="$ROOT_DIR/backend"

ENV_PROFILE=""
while [ $# -gt 0 ]; do
  case "$1" in
    --env)
      ENV_PROFILE="${2:-}"
      shift 2
      ;;
    *)
      echo "Argomento non riconosciuto: $1" >&2
      exit 1
      ;;
  esac
done

if [ -z "$ENV_PROFILE" ]; then
  echo "Uso: $0 --env <dev-home|dev-office|mirror|prod>" >&2
  exit 1
fi

SRC="$ENV_DIR/backend.${ENV_PROFILE}.env.example"
DST_PROFILE="$BACKEND_DIR/.env.${ENV_PROFILE}"
DST_DEFAULT="$BACKEND_DIR/.env"

if [ ! -f "$SRC" ]; then
  echo "Template non trovato: $SRC" >&2
  exit 1
fi

if [ ! -f "$DST_PROFILE" ]; then
  cp "$SRC" "$DST_PROFILE"
  echo "Creato: $DST_PROFILE"
else
  echo "Esiste già: $DST_PROFILE (lascio invariato)"
fi

cp "$DST_PROFILE" "$DST_DEFAULT"
echo "Aggiornato: $DST_DEFAULT -> contenuto di .env.${ENV_PROFILE}"
