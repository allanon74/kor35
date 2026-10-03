#!/usr/bin/env bash
# Aggiorna solo gli script del kiosk stazione. Non tocca /etc/kor35/kiosk-station.env
# (lì stanno URL e password WiFi: install-station-kiosk.sh le riscriverebbe).
#
# Sul Pi, da questa cartella:
#   sudo ./update-station-kiosk.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ "$(id -u)" -ne 0 ]; then
  echo "Esegui come root: sudo $0" >&2
  exit 1
fi

for f in kiosk-station.sh kor35-kiosk-wifi.sh; do
  if [ ! -f "${SCRIPT_DIR}/${f}" ]; then
    echo "Manca ${SCRIPT_DIR}/${f}" >&2
    exit 1
  fi
done

install -d /usr/local/bin /usr/local/sbin
install -m 0755 "${SCRIPT_DIR}/kiosk-station.sh" /usr/local/bin/kiosk-station.sh
install -m 0755 "${SCRIPT_DIR}/kor35-kiosk-wifi.sh" /usr/local/sbin/kor35-kiosk-wifi.sh

KIOSK_USER="${KIOSK_USER:-${SUDO_USER:-pi}}"
if [ ! -f /etc/sudoers.d/kor35-kiosk-wifi ]; then
  cat > /etc/sudoers.d/kor35-kiosk-wifi <<EOF
${KIOSK_USER} ALL=(root) NOPASSWD: /usr/local/sbin/kor35-kiosk-wifi.sh
EOF
  chmod 440 /etc/sudoers.d/kor35-kiosk-wifi
fi

systemctl daemon-reload
if [ -f /etc/kor35/NO_KIOSK ]; then
  echo "NO_KIOSK presente: script copiati, servizio non riavviato."
else
  systemctl restart kiosk-station.service
fi

echo ""
echo "Script aggiornati, env non toccato."
echo "  /usr/local/bin/kiosk-station.sh"
echo "  /usr/local/sbin/kor35-kiosk-wifi.sh"
if grep -q "Scan da .* non elenca" /usr/local/sbin/kor35-kiosk-wifi.sh; then
  echo "  wifi script: stacca-e-scansiona OK"
else
  echo "  ATTENZIONE: /usr/local/sbin/kor35-kiosk-wifi.sh è vecchio (manca stacca-e-scansiona)"
fi
echo "  firma: $(sha256sum /usr/local/sbin/kor35-kiosk-wifi.sh | awk '{print $1}')"
echo "  env: /etc/kor35/kiosk-station.env"
echo "  wifi: sudo /usr/local/sbin/kor35-kiosk-wifi.sh current"
echo "  debug: sudo /usr/local/sbin/kor35-kiosk-wifi.sh debug"
echo "  log:  journalctl -u kiosk-station.service -n 40 --no-pager"
