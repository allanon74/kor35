#!/usr/bin/env bash
set -euo pipefail

# Riaccende WiFi staff Pi_Emergenza (10.42.0.1) — idempotente, anche al boot.
#
# Sul Pi:
#   sudo ./scripts/mirror_ensure_emergency_wifi.sh
#
# Make:
#   sudo make mirror-ensure-emergency-wifi ENV=mirror

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib_mirror_pi.sh
source "$SCRIPT_DIR/lib_mirror_pi.sh"

if [ "$(id -u)" -ne 0 ]; then
  mirror_pi_err "eseguire come root (sudo)"
  exit 1
fi

mirror_pi_load_config
mirror_pi_ensure_emergency_wifi

if mirror_pi_emergency_wifi_up; then
  mirror_pi_log "WiFi emergenza attiva (${EMERGENCY_WIFI_SSID} / ${EMERGENCY_WIFI_IP})"
else
  mirror_pi_warn "WiFi emergenza ancora non attiva"
  mirror_pi_diagnose_emergency_wifi
  echo ""
  echo "Prossimi passi:"
  echo "  1. sudo nano /etc/kor35/mirror-network.env   # EMERGENCY_WIFI_PASSPHRASE"
  echo "  2. sudo make mirror-install-network ENV=mirror MIRROR_NETWORK_AUTO_BOOT=0"
  echo "  3. sudo make mirror-ensure-emergency-wifi ENV=mirror"
  exit 1
fi
