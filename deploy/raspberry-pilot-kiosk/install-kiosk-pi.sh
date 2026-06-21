#!/usr/bin/env bash
set -euo pipefail

# Installa il client kiosk KOR35 su un Raspberry dedicato (solo browser, due HDMI).
# Non richiede il monorepo completo: basta questa cartella deploy/raspberry-pilot-kiosk/.
#
#   sudo ./install-kiosk-pi.sh
#   sudo ./install-kiosk-pi.sh --prompt-url
#   sudo ./install-kiosk-pi.sh --base-url https://www.kor35.it

PILOT_BASE_URL="${PILOT_BASE_URL:-https://www.kor35.it}"
KOR35_KIOSK_PROMPT_URL="${KOR35_KIOSK_PROMPT_URL:-0}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ "$(id -u)" -ne 0 ]; then
  echo "Esegui come root: sudo $0 [--prompt-url] [--base-url URL]" >&2
  exit 1
fi

while [ $# -gt 0 ]; do
  case "$1" in
    --prompt-url) KOR35_KIOSK_PROMPT_URL=1; shift ;;
    --base-url)
      PILOT_BASE_URL="${2:-}"
      shift 2
      ;;
    -h|--help)
      sed -n '1,20p' "$0"
      exit 0
      ;;
    *)
      echo "Argomento non riconosciuto: $1" >&2
      exit 1
      ;;
  esac
done

apt-get update
apt-get install -y \
  xserver-xorg x11-xserver-utils xinit openbox xinput \
  chromium-browser curl unclutter zenity wmctrl

install -d /etc/kor35 /var/lib/kor35 /usr/local/bin
install -m 0755 "${SCRIPT_DIR}/kiosk-master.sh" /usr/local/bin/kiosk-master.sh

cat > /etc/kor35/kiosk.env <<EOF
PILOT_BASE_URL=${PILOT_BASE_URL}
KOR35_KIOSK_PROMPT_URL=${KOR35_KIOSK_PROMPT_URL}
EOF
chmod 644 /etc/kor35/kiosk.env
printf '%s\n' "${PILOT_BASE_URL}" > /var/lib/kor35/kiosk-base-url

# Disabilita eventuale installazione precedente
systemctl disable --now kor35-kiosk.service 2>/dev/null || true

install -m 0644 "${SCRIPT_DIR}/kiosk-master.service" /etc/systemd/system/kiosk-master.service
systemctl daemon-reload
systemctl enable kiosk-master.service
systemctl restart kiosk-master.service

echo ""
echo "Kiosk installato."
echo "  Servizio:  systemctl status kiosk-master.service"
echo "  Config:    /etc/kor35/kiosk.env"
echo "  Server:    ${PILOT_BASE_URL}"
echo "  Schermo grande → /pilot/?screen=status"
echo "  Schermo piccolo → /pilot/?screen=control"
echo ""
echo "Test: curl -fsS ${PILOT_BASE_URL%/}/api/healthz/ && echo OK"
