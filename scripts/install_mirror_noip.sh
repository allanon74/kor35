#!/usr/bin/env bash
set -euo pipefail

# Installa sul mirror Pi il client No-IP (timer + aggiornamento al cambio rete).
#
# Uso sul Pi (root):
#   sudo ./scripts/install_mirror_noip.sh
#   sudo NOIP_USERNAME='email@example.com' NOIP_PASSWORD='...' ./scripts/install_mirror_noip.sh
#
# Le credenziali restano in /etc/kor35/noip.env (chmod 600). Non finiscono nel git.
# Dopo l'installazione disattivare il DUC No-IP sul PC Windows.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
# shellcheck source=lib_mirror_pi.sh
source "$SCRIPT_DIR/lib_mirror_pi.sh"

WRITE_CREDENTIALS=0
if [ -n "${NOIP_USERNAME:-}" ] && [ -n "${NOIP_PASSWORD:-}" ]; then
  WRITE_CREDENTIALS=1
fi

while [ $# -gt 0 ]; do
  case "$1" in
    --write-credentials) WRITE_CREDENTIALS=1; shift ;;
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

apt_packages=(curl miniupnpc)
missing=()
for pkg in "${apt_packages[@]}"; do
  dpkg -s "$pkg" >/dev/null 2>&1 || missing+=("$pkg")
done
if [ "${#missing[@]}" -gt 0 ]; then
  mirror_pi_log "Installazione pacchetti: ${missing[*]}"
  apt-get update -qq
  DEBIAN_FRONTEND=noninteractive apt-get install -y "${missing[@]}"
fi

mkdir -p /etc/kor35 /var/lib/kor35 /etc/NetworkManager/dispatcher.d

ENV_FILE="/etc/kor35/noip.env"
if [ "$WRITE_CREDENTIALS" = "1" ]; then
  if [ -z "${NOIP_USERNAME:-}" ] || [ -z "${NOIP_PASSWORD:-}" ]; then
    mirror_pi_err "--write-credentials richiede NOIP_USERNAME e NOIP_PASSWORD nell'ambiente"
    exit 1
  fi
  umask 077
  {
    echo "# Generato da install_mirror_noip.sh — non committare"
    printf 'NOIP_USERNAME=%q\n' "$NOIP_USERNAME"
    printf 'NOIP_PASSWORD=%q\n' "$NOIP_PASSWORD"
    printf 'NOIP_HOSTNAME=%q\n' "${NOIP_HOSTNAME:-kor35.ddns.net}"
    printf 'NOIP_UPNP=%q\n' "${NOIP_UPNP:-1}"
    printf 'NOIP_REFRESH_SEC=%q\n' "${NOIP_REFRESH_SEC:-86400}"
    printf 'NOIP_UPNP_TCP_MAPS=%q\n' "${NOIP_UPNP_TCP_MAPS:-80:80 443:443 22:10022}"
  } >"$ENV_FILE"
  chmod 600 "$ENV_FILE"
  mirror_pi_log "Scritte credenziali in ${ENV_FILE}"
elif [ ! -f "$ENV_FILE" ]; then
  install -m 600 "$ROOT_DIR/config/mirror/noip.env.example" "$ENV_FILE"
  mirror_pi_warn "Creato ${ENV_FILE} dal template: imposta NOIP_USERNAME e NOIP_PASSWORD"
fi
chown root:root "$ENV_FILE"
chmod 600 "$ENV_FILE"

for unit in kor35-mirror-noip.service kor35-mirror-noip.timer; do
  src="${ROOT_DIR}/config/systemd/${unit}"
  dst="/etc/systemd/system/${unit}"
  if [ ! -f "$src" ]; then
    mirror_pi_err "unit mancante: $src"
    exit 1
  fi
  cp "$src" "$dst"
  sed -i "s|/home/pi/kor35-replica|${KOR35_REPO_PATH}|g" "$dst"
  mirror_pi_log "installata: $dst"
done

dispatcher_src="${ROOT_DIR}/config/mirror/network/nm-dispatcher-kor35-noip.sh"
dispatcher_dst="/etc/NetworkManager/dispatcher.d/90-kor35-noip"
cp "$dispatcher_src" "$dispatcher_dst"
chmod 755 "$dispatcher_dst"
chown root:root "$dispatcher_dst"

systemctl daemon-reload
systemctl enable --now kor35-mirror-noip.timer
systemctl start kor35-mirror-noip.service || mirror_pi_warn "primo aggiornamento No-IP non riuscito (vedi journalctl -u kor35-mirror-noip.service)"

mirror_pi_log "Client No-IP installato (timer ogni 5 minuti + al cambio rete)."
echo ""
echo "Verifica:"
echo "  systemctl is-active kor35-mirror-noip.timer"
echo "  ${KOR35_REPO_PATH}/scripts/mirror_noip_update.sh --status"
echo "  journalctl -u kor35-mirror-noip.service -n 40 --no-pager"
echo ""
echo "Sul PC Windows disattiva il DUC No-IP (icona in tray → Exit, e toglilo dall'avvio automatico)."
echo "Due client sullo stesso hostname si sovrascrivono."
echo ""
if ! grep -qE '^NOIP_USERNAME=' "$ENV_FILE" || grep -qE '^NOIP_USERNAME=.*CHANGE_ME' "$ENV_FILE"; then
  echo "Credenziali ancora da compilare:"
  echo "  sudo nano ${ENV_FILE}"
  echo "  sudo systemctl start kor35-mirror-noip.service"
fi
