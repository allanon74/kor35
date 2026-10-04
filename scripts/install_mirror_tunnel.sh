#!/usr/bin/env bash
set -euo pipefail

# Installa sul mirror Pi la galleria SSH verso la produzione (mirror.kor35.it).
#
# Uso sul Pi (root):
#   sudo ./scripts/install_mirror_tunnel.sh
#   sudo ./scripts/install_mirror_tunnel.sh --no-start
#
# La chiave privata resta in /etc/kor35/mirror-tunnel/ e non va nel git.
# La chiave pubblica va autorizzata sul server prod (make mirror-tunnel-pair).

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
# shellcheck source=lib_mirror_pi.sh
source "$SCRIPT_DIR/lib_mirror_pi.sh"

START_NOW=1
while [ $# -gt 0 ]; do
  case "$1" in
    --no-start) START_NOW=0; shift ;;
    -h|--help)
      sed -n '1,16p' "$0"
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

if ! command -v ssh >/dev/null 2>&1; then
  apt-get update -qq
  DEBIAN_FRONTEND=noninteractive apt-get install -y openssh-client
fi

install -d -m 0755 /etc/kor35/mirror-tunnel
KEY=/etc/kor35/mirror-tunnel/id_ed25519
if [ ! -f "$KEY" ]; then
  ssh-keygen -t ed25519 -N "" -C "kor35-mirror-tunnel" -f "$KEY"
  mirror_pi_log "Creata chiave ${KEY}"
else
  mirror_pi_log "Chiave già presente (${KEY}), non la rigenero"
fi
chmod 600 "$KEY"
chmod 644 "${KEY}.pub"

ENV_FILE=/etc/kor35/mirror-tunnel.env
if [ ! -f "$ENV_FILE" ]; then
  install -m 600 "$ROOT_DIR/config/mirror/mirror-tunnel.env.example" "$ENV_FILE"
fi
chmod 600 "$ENV_FILE"

# shellcheck disable=SC1090
source "$ENV_FILE"
HOST="${MIRROR_TUNNEL_SSH_HOST:-www.kor35.it}"
PORT="${MIRROR_TUNNEL_SSH_PORT:-22}"
ssh-keyscan -4 -p "$PORT" -H "$HOST" > /etc/kor35/mirror-tunnel/known_hosts 2>/dev/null \
  || mirror_pi_warn "ssh-keyscan di ${HOST} non riuscito: la galleria non partirà finché known_hosts non è compilato"
chmod 644 /etc/kor35/mirror-tunnel/known_hosts

unit_src="${ROOT_DIR}/config/systemd/kor35-mirror-tunnel.service"
unit_dst=/etc/systemd/system/kor35-mirror-tunnel.service
cp "$unit_src" "$unit_dst"
sed -i "s|/home/pi/kor35-replica|${KOR35_REPO_PATH}|g" "$unit_dst"
systemctl daemon-reload
systemctl enable kor35-mirror-tunnel.service

# CSRF: il container legge .env.mirror all'avvio. Non stampa il file.
mirror_env="${KOR35_REPO_PATH}/backend/.env.mirror"
origin="https://mirror.kor35.it"
env_changed=0
if [ -f "$mirror_env" ] && ! grep -q "$origin" "$mirror_env"; then
  if grep -q '^EXTRA_CSRF_TRUSTED_ORIGINS=' "$mirror_env"; then
    sed -i "s|^EXTRA_CSRF_TRUSTED_ORIGINS=\\(.*\\)|EXTRA_CSRF_TRUSTED_ORIGINS=${origin},\\1|" "$mirror_env"
  else
    printf '\nEXTRA_CSRF_TRUSTED_ORIGINS=%s\n' "$origin" >> "$mirror_env"
  fi
  if grep -q '^EXTRA_CORS_ALLOWED_ORIGINS=' "$mirror_env"; then
    sed -i "s|^EXTRA_CORS_ALLOWED_ORIGINS=\\(.*\\)|EXTRA_CORS_ALLOWED_ORIGINS=${origin},\\1|" "$mirror_env"
  fi
  env_changed=1
  mirror_pi_log "Aggiunto ${origin} a EXTRA_CSRF_TRUSTED_ORIGINS"
fi

if [ "$env_changed" = "1" ] && command -v docker >/dev/null 2>&1; then
  mirror_pi_log "Ricreo backend e daphne per leggere il nuovo CSRF"
  (
    cd "${KOR35_REPO_PATH}/config/docker"
    COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-kor35-replica}" \
      KOR35_BACKEND_ENV_FILE="${mirror_env}" \
      docker compose -f compose.base.yml -f compose.mirror.yml up -d --no-deps backend daphne
  )
fi

if [ "$START_NOW" = "1" ]; then
  systemctl restart kor35-mirror-tunnel.service \
    || mirror_pi_warn "galleria non partita (la chiave pubblica è già su prod?). journalctl -u kor35-mirror-tunnel.service -n 30"
fi

mirror_pi_log "Galleria mirror installata."
echo ""
echo "Chiave pubblica da autorizzare su prod come utente kor35-tunnel:"
cat "${KEY}.pub"
echo ""
echo "Verifica:"
echo "  systemctl is-active kor35-mirror-tunnel.service"
echo "  journalctl -u kor35-mirror-tunnel.service -n 40 --no-pager"
