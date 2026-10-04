#!/bin/bash
# NetworkManager dispatcher: aggiorna No-IP quando cambia la rete verso Internet.
# Argomenti NM: $1 interfaccia, $2 azione.
# Non modificare a mano sul Pi: lo installa scripts/install_mirror_noip.sh.

set -euo pipefail

IFACE="${1:-}"
ACTION="${2:-}"

case "$ACTION" in
  up|dhcp4-change|connectivity-change) ;;
  *) exit 0 ;;
esac

case "$IFACE" in
  lo|docker*|br-*|veth*|tun*|tap*|wg*|nm-*) exit 0 ;;
esac

if command -v nmcli >/dev/null 2>&1; then
  if nmcli -t -f NAME,DEVICE con show --active 2>/dev/null | grep -qx "Hotspot-Emergenza:${IFACE}"; then
    exit 0
  fi
fi

systemctl start --no-block kor35-mirror-noip.service
