#!/usr/bin/env bash
set -euo pipefail

# Riallineamento post-evento del mirror Pi:
# 1) full sync DB con diagnostica
# 2) push media locali -> master (senza delete)
# 3) pull media master -> locale (con delete lato locale)
#
# Uso:
#   ./scripts/mirror_resync_after_event.sh [--env mirror]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_PROFILE="mirror"

while [ $# -gt 0 ]; do
  case "$1" in
    --env)
      ENV_PROFILE="${2:-}"
      if [ -z "$ENV_PROFILE" ]; then
        echo "--env richiede un valore" >&2
        exit 1
      fi
      shift 2
      ;;
    *)
      echo "Argomento non riconosciuto: $1" >&2
      echo "Uso: $0 [--env mirror]" >&2
      exit 1
      ;;
  esac
done

if [ "$ENV_PROFILE" != "mirror" ]; then
  echo "Questo script e' pensato per il profilo mirror. Ricevuto: $ENV_PROFILE" >&2
  exit 1
fi

echo "[1/3] Sync DB full con diagnostica..."
make -C "$ROOT_DIR" sync-db-full-diagnose ENV="$ENV_PROFILE"

echo "[2/3] Push media locale -> master..."
make -C "$ROOT_DIR" sync-media-push

echo "[3/3] Pull media master -> locale..."
make -C "$ROOT_DIR" sync-media

echo "Riallineamento post-evento completato."
