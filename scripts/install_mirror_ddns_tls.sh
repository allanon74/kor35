#!/usr/bin/env bash
set -euo pipefail

# Automazione TLS DDNS sul mirror Pi (kor35.ddns.net):
# - webroot ACME su nginx Docker
# - deploy hook certbot → certs_ddns + reload
# - timer systemd per rinnovo periodico
#
# Uso sul Pi (root):
#   sudo ./scripts/install_mirror_ddns_tls.sh
#   sudo ./scripts/install_mirror_ddns_tls.sh --force-renew

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
# shellcheck source=lib_mirror_pi.sh
source "$SCRIPT_DIR/lib_mirror_pi.sh"
# shellcheck source=lib_tls_certs.sh
source "$SCRIPT_DIR/lib_tls_certs.sh"

FORCE_RENEW=0

while [ $# -gt 0 ]; do
  case "$1" in
    --force-renew) FORCE_RENEW=1; shift ;;
    -h|--help)
      sed -n '1,14p' "$0"
      exit 0
      ;;
    *)
      mirror_pi_err "argomento non riconosciuto: $1"
      exit 1
      ;;
  esac
done

if [ "$(id -u)" -ne 0 ]; then
  mirror_pi_err "eseguire come root (sudo)"
  exit 1
fi

mirror_pi_load_config

if ! command -v certbot >/dev/null 2>&1; then
  mirror_pi_log "Installazione certbot..."
  apt-get update -qq
  DEBIAN_FRONTEND=noninteractive apt-get install -y certbot
fi

WEBROOT="${KOR35_REPO_PATH}/config/docker/nginx-docker/certbot_webroot"
mkdir -p "$WEBROOT/.well-known/acme-challenge"
chown -R "${KOR35_MIRROR_RUN_USER:-pi}:${KOR35_MIRROR_RUN_GROUP:-pi}" "$WEBROOT"

# ddns.conf con location ACME (se mancante)
ddns_dst="${KOR35_REPO_PATH}/config/docker/nginx-docker/nginx_conf/ddns.conf"
ddns_example="${KOR35_REPO_PATH}/config/docker/nginx-docker/nginx_conf/ddns.conf.example"
if [ ! -f "$ddns_dst" ] && [ -f "$ddns_example" ]; then
  cp "$ddns_example" "$ddns_dst"
  mirror_pi_log "Creato ddns.conf da example"
elif [ -f "$ddns_dst" ] && ! grep -q 'acme-challenge' "$ddns_dst"; then
  mirror_pi_warn "ddns.conf esiste ma manca location ACME — rigenera da ddns.conf.example"
fi

tls_install_deploy_hook \
  "${ROOT_DIR}/config/letsencrypt/deploy-hooks/kor35-mirror-ddns-nginx.sh" \
  "kor35-mirror-ddns-nginx.sh"

for unit in kor35-mirror-ddns-cert-renew.service kor35-mirror-ddns-cert-renew.timer; do
  src="${ROOT_DIR}/config/systemd/${unit}"
  dst="/etc/systemd/system/${unit}"
  if [ ! -f "$src" ]; then
    mirror_pi_err "unit mancante: $src"
    exit 1
  fi
  cp "$src" "$dst"
  sed -i "s|/home/pi/kor35-replica|${KOR35_REPO_PATH}|g" "$dst"
done

systemctl daemon-reload
systemctl enable --now kor35-mirror-ddns-cert-renew.timer

renew_args=()
if [ "$FORCE_RENEW" = "1" ]; then
  renew_args+=(--force)
fi
KOR35_REPO_PATH="${KOR35_REPO_PATH}" "${ROOT_DIR}/scripts/mirror_renew_ddns_tls.sh" "${renew_args[@]}"

mirror_pi_log "Automazione TLS DDNS installata."
echo ""
echo "Verifica:"
echo "  systemctl list-timers | grep kor35-mirror-ddns-cert-renew"
echo "  openssl x509 -in ${KOR35_REPO_PATH}/config/docker/nginx-docker/certs_ddns/fullchain.pem -noout -dates"
