#!/usr/bin/env bash
set -euo pipefail

# Rinnova (o installa) il certificato TLS per kor35.ddns.net sul mirror Pi.
#
# Uso sul Pi:
#   sudo ./scripts/mirror_renew_ddns_tls.sh
#   sudo ./scripts/mirror_renew_ddns_tls.sh --force
#   ./scripts/mirror_renew_ddns_tls.sh --reload-only

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
# shellcheck source=lib_tls_certs.sh
source "$SCRIPT_DIR/lib_tls_certs.sh"

REPO_PATH="${KOR35_REPO_PATH:-$ROOT_DIR}"
DOMAIN="${KOR35_MIRROR_DDNS_DOMAIN:-kor35.ddns.net}"
RUN_USER="${KOR35_MIRROR_TLS_USER:-pi}"
WEBROOT="${REPO_PATH}/config/docker/nginx-docker/certbot_webroot"
CERT_DEST="${REPO_PATH}/config/docker/nginx-docker/certs_ddns"
LE_LIVE="/etc/letsencrypt/live/${DOMAIN}"
DOCKER_DIR="${REPO_PATH}/config/docker"

FORCE_RENEW=0
RELOAD_ONLY=0

while [ $# -gt 0 ]; do
  case "$1" in
    --force) FORCE_RENEW=1; shift ;;
    --reload-only) RELOAD_ONLY=1; shift ;;
    -h|--help)
      sed -n '1,14p' "$0"
      exit 0
      ;;
    *)
      echo "Argomento non riconosciuto: $1" >&2
      exit 1
      ;;
  esac
done

reload_mirror_nginx() {
  export KOR35_TLS_COMPOSE_ENV=mirror
  (
    cd "$DOCKER_DIR"
    env COMPOSE_PROJECT_NAME=kor35-replica \
      KOR35_BACKEND_ENV_FILE="${REPO_PATH}/backend/.env.mirror" \
      docker compose -f compose.base.yml -f compose.mirror.yml exec -T frontend nginx -s reload
  )
}

deploy_le_to_ddns_dir() {
  if [ ! -d "$LE_LIVE" ]; then
    echo "Certificato LE non trovato: ${LE_LIVE}" >&2
    return 1
  fi
  if [ "$(id -u)" -eq 0 ]; then
    tls_copy_le_live_to_dir "$LE_LIVE" "$CERT_DEST" "${RUN_USER}:${RUN_USER}"
  else
    tls_copy_le_live_to_dir "$LE_LIVE" "$CERT_DEST"
  fi
  echo "Certificati DDNS aggiornati in ${CERT_DEST}/"
  openssl x509 -in "${CERT_DEST}/fullchain.pem" -noout -subject -dates
}

if [ "$RELOAD_ONLY" = "1" ]; then
  reload_mirror_nginx
  echo "nginx reload OK (mirror)."
  exit 0
fi

if [ "$(id -u)" -ne 0 ]; then
  echo "Eseguire come root (sudo) per certbot." >&2
  exit 1
fi

mkdir -p "$WEBROOT/.well-known/acme-challenge"
chown -R "${RUN_USER}:${RUN_USER}" "$WEBROOT"

if ! command -v certbot >/dev/null 2>&1; then
  echo "certbot non installato. Esegui: sudo ./scripts/install_mirror_ddns_tls.sh" >&2
  exit 1
fi

RENEWAL_CONF="/etc/letsencrypt/renewal/${DOMAIN}.conf"
if [ -f "$RENEWAL_CONF" ] && grep -q '^authenticator = standalone' "$RENEWAL_CONF"; then
  echo "Migrazione certbot DDNS da standalone a webroot..."
  certbot reconfigure --cert-name "$DOMAIN" --webroot -w "$WEBROOT" --non-interactive
fi

if [ ! -d "$LE_LIVE" ]; then
  echo "Prima emissione certificato per ${DOMAIN}..."
  certbot certonly \
    --non-interactive \
    --agree-tos \
    --register-unsafely-without-email \
    --webroot -w "$WEBROOT" \
    -d "$DOMAIN" \
    --cert-name "$DOMAIN"
elif [ "$FORCE_RENEW" = "1" ]; then
  certbot certonly \
    --webroot -w "$WEBROOT" \
    -d "$DOMAIN" \
    --cert-name "$DOMAIN" \
    --force-renewal \
    --non-interactive
else
  certbot renew --cert-name "$DOMAIN"
fi

deploy_le_to_ddns_dir
reload_mirror_nginx
echo "Rinnovo TLS DDNS completato."
