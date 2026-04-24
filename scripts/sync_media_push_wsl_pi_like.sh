#!/usr/bin/env bash
set -euo pipefail

# Sync push-only dei media dal nodo locale (Pi/WSL) verso il nodo remoto (Master).
# Richiede:
# - rsync locale
# - accesso SSH al nodo remoto
#
# Variabili supportate (env):
#   WSL_PI_REMOTE_SSH_USER     (default: pi)
#   WSL_PI_REMOTE_SSH_HOST     (required se non in .env.sync-media)
#   WSL_PI_REMOTE_SSH_PORT     (default: 22)
#   WSL_PI_REMOTE_SSH_IDENTITY (opzionale: path chiave privata, es. ~/.ssh/kor35-actions)
#   WSL_PI_REMOTE_MEDIA_DIR    (default: /home/pi/kor35-replica/media_data/)
#   WSL_PI_LOCAL_MEDIA_DIR     (default: <repo>/config/docker/nginx-docker/media_data/)
#
# File opzionale in root repo: .env.sync-media (non committare segreti) con le stesse variabili.
#
# Nota sicurezza:
# - push senza --delete per evitare cancellazioni involontarie sul master.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

if [ -f "$ROOT_DIR/.env.sync-media" ]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT_DIR/.env.sync-media"
  set +a
fi

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
  echo "Esempio: WSL_PI_REMOTE_SSH_HOST=www.kor35.it $0" >&2
  exit 1
fi

if ! [[ "$REMOTE_PORT" =~ ^[0-9]+$ ]]; then
  echo "WSL_PI_REMOTE_SSH_PORT deve essere numerica." >&2
  exit 1
fi

if [ ! -d "$LOCAL_MEDIA_DIR" ]; then
  echo "Directory media locale non trovata: $LOCAL_MEDIA_DIR" >&2
  exit 1
fi

SSH_CMD=(ssh -p "${REMOTE_PORT}")
if [ -n "${WSL_PI_REMOTE_SSH_IDENTITY:-}" ]; then
  IDENTITY_EXPANDED="${WSL_PI_REMOTE_SSH_IDENTITY/#\~/$HOME}"
  if [ ! -r "$IDENTITY_EXPANDED" ]; then
    echo "Chiave SSH non leggibile (permessi o path): ${IDENTITY_EXPANDED}" >&2
    echo "Suggerimento: chmod 600 sulla chiave privata; il file deve essere leggibile dall'utente che lancia rsync." >&2
    exit 1
  fi
  SSH_CMD+=(-o IdentitiesOnly=yes -i "$IDENTITY_EXPANDED")
fi
RSYNC_SSH="$(printf '%q ' "${SSH_CMD[@]}")"

echo "Sync media push-only:"
echo "  locale: ${LOCAL_MEDIA_DIR}"
echo "  remoto: ${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_MEDIA_DIR}"
if [ -n "${WSL_PI_REMOTE_SSH_IDENTITY:-}" ]; then
  echo "  identity: ${WSL_PI_REMOTE_SSH_IDENTITY/#\~/$HOME}"
fi

rsync -avz \
  -e "$RSYNC_SSH" \
  "${LOCAL_MEDIA_DIR}" \
  "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_MEDIA_DIR}"

echo "Sync media push completata."
