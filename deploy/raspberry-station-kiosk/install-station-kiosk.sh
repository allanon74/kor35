#!/usr/bin/env bash
# Installa il kiosk stazione (Raspberry Pi 4, schermo touch 800×480).
# Solo browser: niente Docker sul device. La console vive sul mirror / prod.
#
#   sudo ./install-station-kiosk.sh
#   sudo ./install-station-kiosk.sh --base-url https://www.kor35.it --wifi-psk 'segreto'
#   sudo ./install-station-kiosk.sh --fallback-ssid Casa --fallback-psk 'altra'
set -euo pipefail

PILOT_BASE_URL="${PILOT_BASE_URL:-https://www.kor35.it}"
PRIMARY_SSID="${KIOSK_WIFI_PRIMARY_SSID:-kor35-larp}"
PRIMARY_PSK="${KIOSK_WIFI_PRIMARY_PSK:-}"
FALLBACK_SSID="${KIOSK_WIFI_FALLBACK_SSID:-}"
FALLBACK_PSK="${KIOSK_WIFI_FALLBACK_PSK:-}"
WIFI_PROMPT="${KIOSK_WIFI_PROMPT:-1}"
KIOSK_USER="${KIOSK_USER:-${SUDO_USER:-pi}}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ "$(id -u)" -ne 0 ]; then
  echo "Esegui come root: sudo $0" >&2
  exit 1
fi

while [ $# -gt 0 ]; do
  case "$1" in
    --base-url) PILOT_BASE_URL="${2:-}"; shift 2 ;;
    --wifi-ssid) PRIMARY_SSID="${2:-}"; shift 2 ;;
    --wifi-psk) PRIMARY_PSK="${2:-}"; shift 2 ;;
    --fallback-ssid) FALLBACK_SSID="${2:-}"; shift 2 ;;
    --fallback-psk) FALLBACK_PSK="${2:-}"; shift 2 ;;
    --no-prompt-wifi) WIFI_PROMPT=0; shift ;;
    --user) KIOSK_USER="${2:-}"; shift 2 ;;
    -h|--help)
      sed -n '1,16p' "$0"
      exit 0
      ;;
    *)
      echo "Argomento non riconosciuto: $1" >&2
      exit 1
      ;;
  esac
done

if [ ! -d "/home/${KIOSK_USER}" ]; then
  echo "Home assente per utente ${KIOSK_USER}. Passa --user." >&2
  exit 1
fi

if [ -t 0 ]; then
  if [ -z "$PRIMARY_PSK" ]; then
    read -r -p "Password WiFi ${PRIMARY_SSID} (Invio = solo profilo già salvato): " PRIMARY_PSK || true
  fi
  if [ -z "$FALLBACK_SSID" ]; then
    read -r -p "SSID di riserva se ${PRIMARY_SSID} non c'è (Invio = chiedi a schermo): " FALLBACK_SSID || true
  fi
  if [ -n "$FALLBACK_SSID" ] && [ -z "$FALLBACK_PSK" ]; then
    read -r -p "Password ${FALLBACK_SSID}: " FALLBACK_PSK || true
  fi
fi

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y \
  xserver-xorg x11-xserver-utils xinit openbox xinput \
  chromium-browser curl unclutter zenity network-manager sudo iw \
  || apt-get install -y chromium curl unclutter zenity network-manager sudo iw

install -d -o "$KIOSK_USER" -g "$KIOSK_USER" /etc/kor35 /var/lib/kor35
install -m 0755 "${SCRIPT_DIR}/kiosk-station.sh" /usr/local/bin/kiosk-station.sh
install -m 0755 "${SCRIPT_DIR}/kor35-kiosk-wifi.sh" /usr/local/sbin/kor35-kiosk-wifi.sh

umask 077
{
  printf 'PILOT_BASE_URL=%q\n' "$PILOT_BASE_URL"
  printf 'KIOSK_START_PATH=%q\n' '/pilot/?screen=station&viewport=800x480'
  printf 'KIOSK_WIFI_MANAGE=%q\n' '1'
  printf 'KIOSK_WIFI_PRIMARY_SSID=%q\n' "$PRIMARY_SSID"
  printf 'KIOSK_WIFI_PRIMARY_PSK=%q\n' "$PRIMARY_PSK"
  printf 'KIOSK_WIFI_FALLBACK_SSID=%q\n' "$FALLBACK_SSID"
  printf 'KIOSK_WIFI_FALLBACK_PSK=%q\n' "$FALLBACK_PSK"
  printf 'KIOSK_WIFI_PROMPT=%q\n' "$WIFI_PROMPT"
  printf 'KIOSK_MODE=%q\n' '800x480'
  printf 'KIOSK_ROTATE=%q\n' 'normal'
} > /etc/kor35/kiosk-station.env
chown "$KIOSK_USER:$KIOSK_USER" /etc/kor35/kiosk-station.env
chmod 600 /etc/kor35/kiosk-station.env

usermod -aG netdev "$KIOSK_USER" || true
cat > /etc/sudoers.d/kor35-kiosk-wifi <<EOF
${KIOSK_USER} ALL=(root) NOPASSWD: /usr/local/sbin/kor35-kiosk-wifi.sh
EOF
chmod 440 /etc/sudoers.d/kor35-kiosk-wifi

sed "s/__KIOSK_USER__/${KIOSK_USER}/g" "${SCRIPT_DIR}/kiosk-station.service" \
  > /etc/systemd/system/kiosk-station.service
systemctl daemon-reload
systemctl enable kiosk-station.service
systemctl restart kiosk-station.service || true

echo ""
echo "Kiosk stazione installato per ${KIOSK_USER}."
echo "  Servizio: systemctl status kiosk-station.service"
echo "  Config:   /etc/kor35/kiosk-station.env"
echo "  Schermo:  /pilot/?screen=station&viewport=800x480"
echo "  WiFi:     prima ${PRIMARY_SSID}, poi la rete di riserva o una scelta a schermo"
echo ""
echo "Serve Raspberry Pi OS con desktop e login automatico sulla sessione grafica."
echo "Per il desktop di debug: sudo touch /etc/kor35/NO_KIOSK && sudo systemctl stop kiosk-station.service"
