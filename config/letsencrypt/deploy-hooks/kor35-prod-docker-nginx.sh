#!/usr/bin/env bash
# Deploy hook certbot (prod): copia cert LE → nginx-docker/certs + reload Docker.
set -euo pipefail

REPO_PATH="${KOR35_REPO_PATH:-/srv/kor35}"
DOMAIN="${KOR35_PROD_TLS_DOMAIN:-www.kor35.it}"
RUN_USER="${KOR35_PROD_TLS_USER:-deploy}"
DOCKER_DIR="${REPO_PATH}/config/docker"
CERT_DEST="${REPO_PATH}/config/docker/nginx-docker/certs"
LE_LIVE="/etc/letsencrypt/live/${DOMAIN}"

if [ ! -d "$LE_LIVE" ]; then
  echo "Hook prod: live dir assente (${LE_LIVE}), skip." >&2
  exit 0
fi

install -d -m 0750 -o "$RUN_USER" -g "$RUN_USER" "$CERT_DEST"
install -m 0644 -o "$RUN_USER" -g "$RUN_USER" "${LE_LIVE}/fullchain.pem" "${CERT_DEST}/fullchain.pem"
install -m 0600 -o "$RUN_USER" -g "$RUN_USER" "${LE_LIVE}/privkey.pem" "${CERT_DEST}/privkey.pem"

(
  cd "$DOCKER_DIR"
  env COMPOSE_PROJECT_NAME=kor35-prod \
    KOR35_BACKEND_ENV_FILE="${REPO_PATH}/backend/.env.prod" \
    docker compose -f compose.base.yml -f compose.prod.yml up -d frontend
)

sudo -u "$RUN_USER" env \
  COMPOSE_PROJECT_NAME=kor35-prod \
  KOR35_BACKEND_ENV_FILE="${REPO_PATH}/backend/.env.prod" \
  KOR35_TLS_COMPOSE_ENV=prod \
  "${REPO_PATH}/scripts/refresh_prod_docker_tls.sh" --reload-only

# Best-effort: push verso mirror se SSH configurato.
if sudo -u "$RUN_USER" test -x "${REPO_PATH}/scripts/sync_tls_certs_to_mirror.sh"; then
  sudo -u "$RUN_USER" env \
    KOR35_NGINX_TLS_SOURCE_DIR="${REPO_PATH}/config/docker/nginx-docker" \
    "${REPO_PATH}/scripts/sync_tls_certs_to_mirror.sh" \
    || echo "WARN: sync certificati verso mirror fallita (non bloccante)." >&2
fi
