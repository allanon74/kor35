#!/usr/bin/env bash
set -euo pipefail

# Copia certificati Let's Encrypt (www.kor35.it) nella cartella usata da nginx Docker.
#
# Uso sul server prod:
#   sudo ./scripts/refresh_prod_docker_tls.sh
#   sudo ./scripts/refresh_prod_docker_tls.sh --sync-mirror
#   ./scripts/refresh_prod_docker_tls.sh --reload-only   # solo nginx reload (da deploy hook)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
# shellcheck source=lib_tls_certs.sh
source "$SCRIPT_DIR/lib_tls_certs.sh"

REPO_PATH="${KOR35_REPO_PATH:-$ROOT_DIR}"
DOMAIN="${KOR35_PROD_TLS_DOMAIN:-www.kor35.it}"
RUN_USER="${KOR35_PROD_TLS_USER:-deploy}"
DOCKER_DIR="${REPO_PATH}/config/docker"
CERT_DEST="${REPO_PATH}/config/docker/nginx-docker/certs"
LE_LIVE="/etc/letsencrypt/live/${DOMAIN}"

SYNC_MIRROR=0
RELOAD_ONLY=0

while [ $# -gt 0 ]; do
  case "$1" in
    --sync-mirror) SYNC_MIRROR=1; shift ;;
    --reload-only) RELOAD_ONLY=1; shift ;;
    -h|--help)
      sed -n '1,12p' "$0"
      exit 0
      ;;
    *)
      echo "Argomento non riconosciuto: $1" >&2
      exit 1
      ;;
  esac
done

reload_prod_nginx() {
  export KOR35_TLS_COMPOSE_ENV=prod
  (
    cd "$DOCKER_DIR"
    env COMPOSE_PROJECT_NAME=kor35-prod \
      KOR35_BACKEND_ENV_FILE="${REPO_PATH}/backend/.env.prod" \
      docker compose -f compose.base.yml -f compose.prod.yml exec -T frontend nginx -s reload
  )
}

if [ "$RELOAD_ONLY" = "1" ]; then
  reload_prod_nginx
  exit 0
fi

if [ "$(id -u)" -ne 0 ]; then
  echo "Eseguire come root (sudo) per leggere /etc/letsencrypt." >&2
  exit 1
fi

if [ ! -d "$LE_LIVE" ]; then
  echo "Certificato LE non trovato: ${LE_LIVE}" >&2
  exit 1
fi

tls_copy_le_live_to_dir "$LE_LIVE" "$CERT_DEST" "${RUN_USER}:${RUN_USER}"
echo "Certificati aggiornati in ${CERT_DEST}/"
openssl x509 -in "${CERT_DEST}/fullchain.pem" -noout -subject -dates

reload_prod_nginx
echo "nginx reload OK (prod)."

if [ "$SYNC_MIRROR" = "1" ]; then
  sudo -u "$RUN_USER" env \
    KOR35_NGINX_TLS_SOURCE_DIR="${REPO_PATH}/config/docker/nginx-docker" \
    "${REPO_PATH}/scripts/sync_tls_certs_to_mirror.sh"
fi
