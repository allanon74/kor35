#!/usr/bin/env bash
# Deploy hook certbot: certificato mirror.kor35.it → nginx Docker prod.
set -euo pipefail

if [ -n "${RENEWED_DOMAINS:-}" ] && ! printf '%s\n' "$RENEWED_DOMAINS" | grep -q 'mirror.kor35.it'; then
  exit 0
fi

REPO_PATH="${KOR35_REPO_PATH:-/srv/kor35}"
DOMAIN="mirror.kor35.it"
RUN_USER="${KOR35_PROD_TLS_USER:-deploy}"
LE_LIVE="/etc/letsencrypt/live/${DOMAIN}"
CERT_DEST="${REPO_PATH}/config/docker/nginx-docker/certs_mirror"
DOCKER_DIR="${REPO_PATH}/config/docker"

if [ ! -d "$LE_LIVE" ]; then
  echo "Hook mirror.kor35.it: certificato assente, skip." >&2
  exit 0
fi

install -d -m 0750 -o "$RUN_USER" -g "$RUN_USER" "$CERT_DEST"
install -m 0644 -o "$RUN_USER" -g "$RUN_USER" "${LE_LIVE}/fullchain.pem" "${CERT_DEST}/fullchain.pem"
install -m 0600 -o "$RUN_USER" -g "$RUN_USER" "${LE_LIVE}/privkey.pem" "${CERT_DEST}/privkey.pem"

if docker ps --format '{{.Names}}' | grep -qx 'kor35_prod_frontend'; then
  docker exec kor35_prod_frontend nginx -t
  docker exec kor35_prod_frontend nginx -s reload
fi

echo "Certificato ${DOMAIN} copiato in ${CERT_DEST} e nginx ricaricato."
