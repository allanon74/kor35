#!/usr/bin/env bash
set -euo pipefail

# Sync pull-only dei media dal nodo remoto (Master/Pi) verso lo stack WSL Pi-like.
# Richiede:
# - rsync locale
# - accesso SSH al nodo remoto
#
# Variabili supportate (env):
#   WSL_PI_REMOTE_SSH_USER   (default: pi)
#   WSL_PI_REMOTE_SSH_HOST   (required)
#   WSL_PI_REMOTE_SSH_PORT   (default: 22)
#   WSL_PI_REMOTE_MEDIA_DIR  (default: /home/pi/kor35-replica/media_data/)
#   WSL_PI_LOCAL_MEDIA_DIR   (default: <repo>/config/docker/nginx-docker/media_data/)
#
# Esempio:
#   WSL_PI_REMOTE_SSH_HOST=192.168.1.50 ./scripts/sync_media_pull_wsl_pi_like.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

REMOTE_USER="${WSL_PI_REMOTE_SSH_USER:-pi}"
REMOTE_HOST="${WSL_PI_REMOTE_SSH_HOST:-}"
REMOTE_PORT="${WSL_PI_REMOTE_SSH_PORT:-22}"
REMOTE_MEDIA_DIR="${WSL_PI_REMOTE_MEDIA_DIR:-/home/pi/kor35-replica/media_data/}"
LOCAL_MEDIA_DIR="${WSL_PI_LOCAL_MEDIA_DIR:-$ROOT_DIR/config/docker/nginx-docker/media_data/}"

if ! command -v rsync >/dev/null 2>&1; then
  echo "rsync non trovato. Installa rsync e riprova." >&2
  exit 1
fi

if [ -z "$REMOTE_HOST" ]; then
  echo "Variabile mancante: WSL_PI_REMOTE_SSH_HOST" >&2
  echo "Esempio: WSL_PI_REMOTE_SSH_HOST=192.168.1.50 $0" >&2
  exit 1
fi

if ! [[ "$REMOTE_PORT" =~ ^[0-9]+$ ]]; then
  echo "WSL_PI_REMOTE_SSH_PORT deve essere numerica." >&2
  exit 1
fi

mkdir -p "$LOCAL_MEDIA_DIR"

echo "Sync media pull-only:"
echo "  remoto: ${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_MEDIA_DIR}"
echo "  locale: ${LOCAL_MEDIA_DIR}"

rsync -avz --delete \
  -e "ssh -p ${REMOTE_PORT}" \
  "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_MEDIA_DIR}" \
  "${LOCAL_MEDIA_DIR}"

echo "Sync media completata."
