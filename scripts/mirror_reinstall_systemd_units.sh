#!/usr/bin/env bash
set -euo pipefail

# Copia unit systemd mirror da config/systemd/ → /etc/systemd/system/
# (sorgente versionata nel repo — non modificare /etc/systemd a mano sul Pi).
#
# Uso sul Pi:
#   sudo ./scripts/mirror_reinstall_systemd_units.sh
#
# Make:
#   sudo make mirror-reinstall-units ENV=mirror

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
# shellcheck source=lib_mirror_pi.sh
source "$SCRIPT_DIR/lib_mirror_pi.sh"

if [ "$(id -u)" -ne 0 ]; then
  mirror_pi_err "eseguire come root (sudo)"
  exit 1
fi

mirror_pi_load_config

mirror_pi_log "Arresto unit mirror (evita restart loop durante aggiornamento)..."
systemctl stop kor35-mirror-emergency-wifi.service 2>/dev/null || true
systemctl stop kor35-mirror-ensure-emergency-wifi.service 2>/dev/null || true

for unit in kor35-mirror-dhcp-event.service kor35-mirror-emergency-wifi.service kor35-mirror-network-mode.service kor35-mirror-ensure-emergency-wifi.service; do
  src="$ROOT_DIR/config/systemd/$unit"
  dst="/etc/systemd/system/$unit"
  if [ ! -f "$src" ]; then
    mirror_pi_err "unit mancante nel repo: $src"
    exit 1
  fi
  cp "$src" "$dst"
  sed -i "s|/home/pi/kor35-replica|${KOR35_REPO_PATH}|g" "$dst"
  mirror_pi_log "installata: $dst ← $src"
done

if [ -f /etc/systemd/system/kor35-mirror-emergency-wifi.service ]; then
  sed -i "s|wlan0|${EMERGENCY_WIFI_INTERFACE}|g" /etc/systemd/system/kor35-mirror-emergency-wifi.service
  sed -i "s|10.42.0.1/24|${EMERGENCY_WIFI_IP}/${EMERGENCY_WIFI_CIDR}|g" /etc/systemd/system/kor35-mirror-emergency-wifi.service
fi

systemctl daemon-reload
mirror_pi_log "Unit systemd aggiornate dal monorepo (${ROOT_DIR}/config/systemd/)."
