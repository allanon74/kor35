#!/usr/bin/env bash
set -euo pipefail

# Installa il client kiosk su un Raspberry dedicato (display pilota).
# Lo stack KOR35 resta sul Pi mirror separato.

PILOT_BASE_URL="${PILOT_BASE_URL:-http://10.42.0.1}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ "$(id -u)" -ne 0 ]; then
  echo "Esegui come root: sudo $0 [--pilot-base-url http://10.42.0.1]" >&2
  exit 1
fi

while [ $# -gt 0 ]; do
  case "$1" in
    --pilot-base-url)
      PILOT_BASE_URL="${2:-}"
      shift 2
      ;;
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

apt-get update
apt-get install -y xserver-xorg x11-xserver-utils xinit openbox chromium-browser unclutter curl

install -d /opt/kor35-kiosk
install -m 0755 "${SCRIPT_DIR}/start-kiosk.sh" /opt/kor35-kiosk/start-kiosk.sh

install -d /etc/kor35
if [ ! -f /etc/kor35/kiosk.env ]; then
  printf 'PILOT_BASE_URL=%s\n' "${PILOT_BASE_URL}" > /etc/kor35/kiosk.env
  chmod 644 /etc/kor35/kiosk.env
fi

install -m 0644 "${SCRIPT_DIR}/kor35-kiosk.service" /etc/systemd/system/kor35-kiosk.service
systemctl daemon-reload
systemctl enable kor35-kiosk.service
systemctl restart kor35-kiosk.service

echo "Kiosk installato. Mirror atteso: ${PILOT_BASE_URL}"
echo "Verifica: systemctl status kor35-kiosk.service --no-pager"
echo "Test rete: curl -fsS ${PILOT_BASE_URL%/}/api/healthz/ && echo OK"
