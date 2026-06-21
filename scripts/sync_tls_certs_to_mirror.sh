#!/usr/bin/env bash
set -euo pipefail

# Copia certificati TLS verso il mirror Pi + reload nginx.
#
# Modalità A — sul server prod (cert locali in config/docker/nginx-docker/certs/):
#   cd /srv/kor35 && make sync-certs-to-mirror ENV=prod
#
# Modalità B — da postazione dev (SSH a prod e mirror), relay prod → Pi:
#   make sync-certs-prod-to-mirror
#   ./scripts/sync_tls_certs_to_mirror.sh --from-prod
#
# Config opzionale: .env.sync-mirror-certs
#   Prod:  deploy@www.kor35.it:22
#   Mirror: pi@kor35.ddns.net:10022
#
# Opzioni:
#   --from-prod    scarica certs da prod poi invia al mirror (postazione dev)
#   --with-ddns    copia anche certs_ddns/ se presente in sorgente
#   --dry-run      anteprima rsync
#   --no-reload    salta nginx -s reload sul mirror

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

if [ -f "$ROOT_DIR/.env.sync-mirror-certs" ]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT_DIR/.env.sync-mirror-certs"
  set +a
fi

FROM_PROD=0
WITH_DDNS=0
DRY_RUN=0
DO_RELOAD=1

while [ $# -gt 0 ]; do
  case "$1" in
    --from-prod) FROM_PROD=1; shift ;;
    --with-ddns) WITH_DDNS=1; shift ;;
    --dry-run) DRY_RUN=1; shift ;;
    --no-reload) DO_RELOAD=0; shift ;;
    -h|--help)
      sed -n '1,35p' "$0"
      exit 0
      ;;
    *)
      echo "Argomento non riconosciuto: $1" >&2
      exit 1
      ;;
  esac
done

# --- Mirror (destinazione) ---
MIRROR_SSH_USER="${MIRROR_SSH_USER:-pi}"
MIRROR_SSH_HOST="${MIRROR_SSH_HOST:-kor35.ddns.net}"
MIRROR_SSH_PORT="${MIRROR_SSH_PORT:-10022}"
MIRROR_SSH_TARGET="${MIRROR_SSH_TARGET:-}"
MIRROR_SSH_IDENTITY="${MIRROR_SSH_IDENTITY:-}"
MIRROR_REPO_PATH="${MIRROR_REPO_PATH:-/home/pi/kor35-replica}"
MIRROR_COMPOSE_PROJECT_NAME="${MIRROR_COMPOSE_PROJECT_NAME:-kor35-replica}"

# --- Prod (sorgente, solo con --from-prod) ---
PROD_SSH_USER="${PROD_SSH_USER:-deploy}"
PROD_SSH_HOST="${PROD_SSH_HOST:-www.kor35.it}"
PROD_SSH_PORT="${PROD_SSH_PORT:-22}"
PROD_SSH_TARGET="${PROD_SSH_TARGET:-}"
PROD_SSH_IDENTITY="${PROD_SSH_IDENTITY:-}"
PROD_REPO_PATH="${PROD_REPO_PATH:-/srv/kor35}"

NGINX_REL="config/docker/nginx-docker"
REMOTE_CERTS="${MIRROR_REPO_PATH}/${NGINX_REL}/certs"
REMOTE_DDNS="${MIRROR_REPO_PATH}/${NGINX_REL}/certs_ddns"
PROD_CERTS="${PROD_REPO_PATH}/${NGINX_REL}/certs"
PROD_DDNS="${PROD_REPO_PATH}/${NGINX_REL}/certs_ddns"

STAGING_DIR="${ROOT_DIR}/.runtime-state/certs-sync-staging"
LOCAL_NGINX_DIR="${KOR35_NGINX_TLS_SOURCE_DIR:-$ROOT_DIR/$NGINX_REL}"
LOCAL_CERTS="${LOCAL_NGINX_DIR}/certs"
LOCAL_DDNS="${LOCAL_NGINX_DIR}/certs_ddns"

if ! command -v rsync >/dev/null 2>&1; then
  echo "rsync non trovato." >&2
  exit 1
fi

expand_identity() {
  local id="${1:-}"
  if [ -z "$id" ] && [ -f "${HOME}/.ssh/id_docker" ]; then
    id="${HOME}/.ssh/id_docker"
  fi
  if [ -z "$id" ] && [ -f "${HOME}/.ssh/id_rsa" ]; then
    id="${HOME}/.ssh/id_rsa"
  fi
  if [ -n "$id" ]; then
    id="${id/#\~/$HOME}"
  fi
  echo "$id"
}

# Host canonici: deploy@www.kor35.it (prod) e pi@kor35.ddns.net (mirror).
# PROD_SSH_TARGET / MIRROR_SSH_TARGET solo override avanzato (es. alias ~/.ssh/config con proxy).
resolve_endpoint() {
  local explicit_target="$1"
  local default_user="$2"
  local default_host="$3"
  if [ -n "$explicit_target" ]; then
    echo "$explicit_target"
  else
    echo "${default_user}@${default_host}"
  fi
}

# Ritorna 0 se il target è un alias SSH (kor35-prod), 1 se user@host
is_ssh_alias() {
  [[ "$1" != *"@"* ]]
}

build_ssh_cmd() {
  local target="$1"
  local port="$2"
  local identity
  identity="$(expand_identity "$3")"
  local -a cmd
  cmd=(ssh -o BatchMode=yes -o ConnectTimeout=30 -o StrictHostKeyChecking=accept-new)
  if [ -f "${HOME}/.ssh/known_hosts" ]; then
    cmd+=(-o "UserKnownHostsFile=${HOME}/.ssh/known_hosts")
  fi
  if ! is_ssh_alias "$target"; then
    cmd+=(-p "$port")
  fi
  if [ -n "$identity" ] && [ -r "$identity" ]; then
    cmd+=(-i "$identity" -o IdentitiesOnly=yes)
  fi
  printf '%q ' "${cmd[@]}"
}

build_ssh_array() {
  local target="$1"
  local port="$2"
  local identity
  identity="$(expand_identity "$3")"
  SSH_ARR=(ssh -o BatchMode=yes -o ConnectTimeout=30 -o StrictHostKeyChecking=accept-new)
  if [ -f "${HOME}/.ssh/known_hosts" ]; then
    SSH_ARR+=(-o "UserKnownHostsFile=${HOME}/.ssh/known_hosts")
  fi
  if ! is_ssh_alias "$target"; then
    SSH_ARR+=(-p "$port")
  fi
  if [ -n "$identity" ] && [ -r "$identity" ]; then
    SSH_ARR+=(-i "$identity" -o IdentitiesOnly=yes)
  fi
}

MIRROR_TARGET="$(resolve_endpoint "$MIRROR_SSH_TARGET" "$MIRROR_SSH_USER" "$MIRROR_SSH_HOST")"
PROD_TARGET="$(resolve_endpoint "$PROD_SSH_TARGET" "$PROD_SSH_USER" "$PROD_SSH_HOST")"

RSYNC_EXTRA=()
if [ "$DRY_RUN" = "1" ]; then
  RSYNC_EXTRA+=(--dry-run)
fi

verify_certs_dir() {
  local dir="$1"
  local label="$2"
  if [ ! -f "${dir}/fullchain.pem" ] || [ ! -f "${dir}/privkey.pem" ]; then
    echo "Certificati mancanti in ${dir}/ (${label})." >&2
    return 1
  fi
  return 0
}

pull_certs_from_prod() {
  echo "=== Pull certificati da produzione ==="
  echo "  prod: ${PROD_TARGET} (${PROD_CERTS}/)"
  build_ssh_array "$PROD_TARGET" "$PROD_SSH_PORT" "$PROD_SSH_IDENTITY"
  local rsync_ssh
  rsync_ssh="$(build_ssh_cmd "$PROD_TARGET" "$PROD_SSH_PORT" "$PROD_SSH_IDENTITY")"

  mkdir -p "${STAGING_DIR}/certs"
  rsync -avz "${RSYNC_EXTRA[@]}" \
    -e "$rsync_ssh" \
    "${PROD_TARGET}:${PROD_CERTS}/" \
    "${STAGING_DIR}/certs/"

  verify_certs_dir "${STAGING_DIR}/certs" "staging prod"

  if [ "$WITH_DDNS" = "1" ]; then
    mkdir -p "${STAGING_DIR}/certs_ddns"
    if rsync -avz "${RSYNC_EXTRA[@]}" -e "$rsync_ssh" \
      "${PROD_TARGET}:${PROD_DDNS}/" "${STAGING_DIR}/certs_ddns/" 2>/dev/null \
      && verify_certs_dir "${STAGING_DIR}/certs_ddns" "staging prod ddns" 2>/dev/null; then
      echo "  certs_ddns: copiati da prod"
    else
      echo "SKIP certs_ddns da prod (cartella assente o incompleta su prod)." >&2
      rm -rf "${STAGING_DIR}/certs_ddns"
    fi
  fi

  SOURCE_CERTS="${STAGING_DIR}/certs"
  SOURCE_DDNS="${STAGING_DIR}/certs_ddns"
}

resolve_local_source() {
  if [ "$FROM_PROD" = "1" ]; then
    pull_certs_from_prod
    return
  fi
  SOURCE_CERTS="${LOCAL_CERTS}"
  SOURCE_DDNS="${LOCAL_DDNS}"
  if ! verify_certs_dir "$SOURCE_CERTS" "locale"; then
    echo "Suggerimento: da postazione dev usa  make sync-certs-prod-to-mirror  oppure  --from-prod" >&2
    exit 1
  fi
}

push_certs_to_mirror() {
  echo "=== Push certificati → mirror ==="
  echo "  sorgente:  ${SOURCE_CERTS}/"
  echo "  mirror:    ${MIRROR_TARGET}:${REMOTE_CERTS}/"

  build_ssh_array "$MIRROR_TARGET" "$MIRROR_SSH_PORT" "$MIRROR_SSH_IDENTITY"
  local rsync_ssh
  rsync_ssh="$(build_ssh_cmd "$MIRROR_TARGET" "$MIRROR_SSH_PORT" "$MIRROR_SSH_IDENTITY")"

  "${SSH_ARR[@]}" "$MIRROR_TARGET" "mkdir -p '${REMOTE_CERTS}'"

  rsync -avz "${RSYNC_EXTRA[@]}" \
    -e "$rsync_ssh" \
    "${SOURCE_CERTS}/" \
    "${MIRROR_TARGET}:${REMOTE_CERTS}/"

  if [ "$WITH_DDNS" = "1" ] && [ -d "${SOURCE_DDNS}" ] \
    && [ -f "${SOURCE_DDNS}/fullchain.pem" ] && [ -f "${SOURCE_DDNS}/privkey.pem" ]; then
    echo "  certs_ddns → ${REMOTE_DDNS}/"
    "${SSH_ARR[@]}" "$MIRROR_TARGET" "mkdir -p '${REMOTE_DDNS}'"
    rsync -avz "${RSYNC_EXTRA[@]}" \
      -e "$rsync_ssh" \
      "${SOURCE_DDNS}/" \
      "${MIRROR_TARGET}:${REMOTE_DDNS}/"
  elif [ "$WITH_DDNS" = "1" ]; then
    echo "SKIP certs_ddns: non presenti in sorgente." >&2
  fi
}

reload_mirror_nginx() {
  if [ "$DO_RELOAD" != "1" ] || [ "$DRY_RUN" = "1" ]; then
    echo "Reload nginx saltato."
    return 0
  fi
  echo "Reload nginx sul mirror..."
  "${SSH_ARR[@]}" "$MIRROR_TARGET" bash -s <<REMOTE
set -euo pipefail
cd "${MIRROR_REPO_PATH}/config/docker"
export COMPOSE_PROJECT_NAME="${MIRROR_COMPOSE_PROJECT_NAME}"
export KOR35_BACKEND_ENV_FILE="${MIRROR_REPO_PATH}/backend/.env.mirror"
docker compose -f compose.base.yml -f compose.mirror.yml exec -T frontend nginx -s reload
echo "nginx reload OK"
REMOTE
}

resolve_local_source
push_certs_to_mirror
reload_mirror_nginx

echo "Sync certificati completata."
