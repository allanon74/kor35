#!/usr/bin/env bash
# Deploy hook certbot (mirror Pi): copia cert LE → nginx-docker/certs_ddns + reload Docker.
set -euo pipefail

REPO_PATH="${KOR35_REPO_PATH:-/home/pi/kor35-replica}"
DOMAIN="${KOR35_MIRROR_DDNS_DOMAIN:-kor35.ddns.net}"
RUN_USER="${KOR35_MIRROR_TLS_USER:-pi}"
DOCKER_DIR="${REPO_PATH}/config/docker"
CERT_DEST="${REPO_PATH}/config/docker/nginx-docker/certs_ddns"
LE_LIVE="/etc/letsencrypt/live/${DOMAIN}"

if [ ! -d "$LE_LIVE" ]; then
  echo "Hook mirror: live dir assente (${LE_LIVE}), skip." >&2
  exit 0
fi

install -d -m 0750 -o "$RUN_USER" -g "$RUN_USER" "$CERT_DEST"
install -m 0644 -o "$RUN_USER" -g "$RUN_USER" "${LE_LIVE}/fullchain.pem" "${CERT_DEST}/fullchain.pem"
install -m 0600 -o "$RUN_USER" -g "$RUN_USER" "${LE_LIVE}/privkey.pem" "${CERT_DEST}/privkey.pem"

sudo -u "$RUN_USER" env \
  COMPOSE_PROJECT_NAME=kor35-replica \
  KOR35_BACKEND_ENV_FILE="${REPO_PATH}/backend/.env.mirror" \
  KOR35_TLS_COMPOSE_ENV=mirror \
  "${REPO_PATH}/scripts/mirror_renew_ddns_tls.sh" --reload-only
