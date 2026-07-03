#!/usr/bin/env bash
set -euo pipefail

# Automazione TLS produzione:
# - webroot per certbot (nginx Docker tiene la porta 80)
# - deploy hook: copia cert → nginx-docker/certs + reload + push mirror
# - timer systemd: sync periodico verso mirror Pi
#
# Uso sul server prod (root):
#   sudo ./scripts/install_prod_tls_automation.sh
#   sudo ./scripts/install_prod_tls_automation.sh --no-mirror-sync

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
# shellcheck source=lib_tls_certs.sh
source "$SCRIPT_DIR/lib_tls_certs.sh"

REPO_PATH="${KOR35_REPO_PATH:-$ROOT_DIR}"
RUN_USER="${KOR35_PROD_TLS_USER:-deploy}"
DOMAIN="${KOR35_PROD_TLS_DOMAIN:-www.kor35.it}"
WEBROOT="${REPO_PATH}/config/docker/nginx-docker/certbot_webroot"
INSTALL_MIRROR_SYNC=1

while [ $# -gt 0 ]; do
  case "$1" in
    --no-mirror-sync) INSTALL_MIRROR_SYNC=0; shift ;;
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

if [ "$(id -u)" -ne 0 ]; then
  echo "Eseguire come root (sudo)." >&2
  exit 1
fi

if ! command -v certbot >/dev/null 2>&1; then
  echo "certbot non trovato. Installare: snap install certbot --classic (o apt)." >&2
  exit 1
fi

mkdir -p "$WEBROOT/.well-known/acme-challenge"
chown -R "${RUN_USER}:${RUN_USER}" "$WEBROOT"

tls_install_deploy_hook \
  "${ROOT_DIR}/config/letsencrypt/deploy-hooks/kor35-prod-docker-nginx.sh" \
  "kor35-prod-docker-nginx.sh" \
  "deploy"

tls_install_deploy_hook \
  "${ROOT_DIR}/config/letsencrypt/deploy-hooks/kor35-prod-start-frontend.sh" \
  "kor35-prod-start-frontend.sh" \
  "post"

RENEWAL_CONF="/etc/letsencrypt/renewal/${DOMAIN}.conf"
if [ -f "$RENEWAL_CONF" ]; then
  if grep -q '^authenticator = standalone' "$RENEWAL_CONF"; then
    echo "Migrazione certbot da standalone a webroot (${DOMAIN})..."
    if certbot reconfigure \
      --cert-name "$DOMAIN" \
      --webroot -w "$WEBROOT" \
      --non-interactive 2>/dev/null \
      && certbot renew --dry-run --cert-name "$DOMAIN" >/dev/null 2>&1; then
      echo "certbot webroot OK."
    else
      echo "Webroot non disponibile (es. kor35.it non punta al server) — fallback pre/post hook standalone."
      install -m 0755 "${ROOT_DIR}/config/letsencrypt/deploy-hooks/kor35-prod-stop-frontend.sh" \
        /etc/letsencrypt/renewal-hooks/pre/kor35-stop-frontend.sh
      install -m 0755 "${ROOT_DIR}/config/letsencrypt/deploy-hooks/kor35-prod-start-frontend.sh" \
        /etc/letsencrypt/renewal-hooks/post/kor35-prod-start-frontend.sh
    fi
  fi
else
  echo "WARN: ${RENEWAL_CONF} assente — salto migrazione webroot." >&2
fi

"${ROOT_DIR}/scripts/refresh_prod_docker_tls.sh"

if [ "$INSTALL_MIRROR_SYNC" = "1" ]; then
  for unit in kor35-prod-cert-sync-mirror.service kor35-prod-cert-sync-mirror.timer; do
    src="${ROOT_DIR}/config/systemd/${unit}"
    dst="/etc/systemd/system/${unit}"
    if [ ! -f "$src" ]; then
      echo "Unit mancante: $src" >&2
      exit 1
    fi
    cp "$src" "$dst"
    sed -i "s|/srv/kor35|${REPO_PATH}|g" "$dst"
    sed -i "s|^User=.*$|User=${RUN_USER}|g" "$dst"
    sed -i "s|^Group=.*$|Group=${RUN_USER}|g" "$dst"
  done
  systemctl daemon-reload
  systemctl enable --now kor35-prod-cert-sync-mirror.timer
  echo "Timer mirror sync: kor35-prod-cert-sync-mirror.timer"

  echo ""
  echo "Verifica SSH deploy → mirror (necessario per sync automatico):"
  MIRROR_ID="${HOME}/.ssh/id_docker"
  [ -r "/home/${RUN_USER}/.ssh/id_docker" ] && MIRROR_ID="/home/${RUN_USER}/.ssh/id_docker"
  if sudo -u "$RUN_USER" ssh -o BatchMode=yes -o ConnectTimeout=15 \
    -p 10022 -i "$MIRROR_ID" -o IdentitiesOnly=yes \
    "pi@kor35.ddns.net" hostname 2>/dev/null; then
    echo "  SSH mirror OK."
  else
    echo "  WARN: SSH verso mirror fallita." >&2
    echo "  Aggiungi la pubkey di ${RUN_USER} in ~pi/.ssh/authorized_keys sul Pi:" >&2
    echo "    cat ~${RUN_USER}/.ssh/id_docker.pub | ssh -p 10022 pi@kor35.ddns.net 'mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys'" >&2
  fi
fi

echo ""
echo "Verifica:"
echo "  sudo certbot renew --dry-run"
echo "  openssl x509 -in ${REPO_PATH}/config/docker/nginx-docker/certs/fullchain.pem -noout -dates"
if [ "$INSTALL_MIRROR_SYNC" = "1" ]; then
  echo "  systemctl list-timers | grep kor35-prod-cert-sync-mirror"
fi
