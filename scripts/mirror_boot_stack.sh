#!/usr/bin/env bash
set -euo pipefail

# Avvio stack mirror al boot — funziona anche senza internet (solo LAN / hotspot).
#
# Uso manuale sul Pi:
#   ./scripts/mirror_boot_stack.sh
#   KOR35_REPO_PATH=/home/pi/kor35-replica ./scripts/mirror_boot_stack.sh
#
# Installazione systemd: config/systemd/kor35-mirror-stack.service

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

REPO_PATH="${KOR35_REPO_PATH:-/home/pi/kor35-replica}"
COMPOSE_DIR="${REPO_PATH}/config/docker"
COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-kor35-replica}"
KOR35_BACKEND_ENV_FILE="${KOR35_BACKEND_ENV_FILE:-${REPO_PATH}/backend/.env.mirror}"
HEALTH_URL="${KOR35_MIRROR_HEALTH_URL:-http://127.0.0.1/api/healthz/}"
MAX_WAIT_SEC="${KOR35_MIRROR_BOOT_WAIT_SEC:-300}"

log() {
  echo "[mirror_boot_stack] $*"
}

if [ ! -f "${KOR35_BACKEND_ENV_FILE}" ]; then
  log "ERRORE: env mancante: ${KOR35_BACKEND_ENV_FILE}" >&2
  exit 1
fi

if [ ! -f "${COMPOSE_DIR}/compose.base.yml" ] || [ ! -f "${COMPOSE_DIR}/compose.mirror.yml" ]; then
  log "ERRORE: compose mirror non trovato in ${COMPOSE_DIR}" >&2
  exit 1
fi

export COMPOSE_PROJECT_NAME
export KOR35_BACKEND_ENV_FILE

cd "${COMPOSE_DIR}"

log "Avvio stack (no build, offline-safe)..."
docker compose -f compose.base.yml -f compose.mirror.yml up -d --no-build

# Dopo reboot il container nginx può restare Up con bind mount vuoti → connection reset.
if ! docker compose -f compose.base.yml -f compose.mirror.yml exec -T frontend \
  test -s /etc/nginx/conf.d/default.conf >/dev/null 2>&1; then
  log "Frontend senza config nginx: force-recreate..."
  docker compose -f compose.base.yml -f compose.mirror.yml up -d --force-recreate frontend
fi

log "Attendo healthcheck locale (${HEALTH_URL}, max ${MAX_WAIT_SEC}s)..."
deadline=$((SECONDS + MAX_WAIT_SEC))
while [ "${SECONDS}" -lt "${deadline}" ]; do
  if curl -fsS "${HEALTH_URL}" >/dev/null 2>&1; then
    log "Stack pronto."
    exit 0
  fi
  sleep 5
done

log "ATTENZIONE: timeout attesa healthz. Controlla: docker compose ps && docker compose logs backend --tail 80" >&2
exit 1
