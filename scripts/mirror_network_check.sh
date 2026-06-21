#!/usr/bin/env bash
set -euo pipefail

# Diagnostica rete + stack mirror Pi (read-only).
#
# Sul Pi:
#   ./scripts/mirror_network_check.sh
#   ./scripts/mirror_network_check.sh --json
#
# Da PC sviluppatore (se SSH configurato):
#   MIRROR_SSH_HOST=kor35-mirror ./scripts/mirror_ssh_check.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib_mirror_pi.sh
source "$SCRIPT_DIR/lib_mirror_pi.sh"

JSON_OUTPUT=0
while [ $# -gt 0 ]; do
  case "$1" in
    --json) JSON_OUTPUT=1; shift ;;
    -h|--help)
      sed -n '1,12p' "$0"
      exit 0
      ;;
    *) mirror_pi_err "argomento non riconosciuto: $1"; exit 1 ;;
  esac
done

mirror_pi_load_config

LAN_IFACE="$(mirror_pi_detect_lan_interface)" || LAN_IFACE="${EVENT_LAN_INTERFACE:-eth0}"
MODE="$(mirror_pi_read_mode_state)"
HAS_INTERNET=0
mirror_pi_has_internet && HAS_INTERNET=1 || true

STACK_OK=0
OMADA_OK=0
DHCP_EVENT_ACTIVE=0
EMERGENCY_WIFI_ACTIVE=0
NGINX_EVENT_VHOST=0
HEALTH_LOCAL_OK=0
DHCP_CONFLICT=0

if [ -f "${KOR35_REPO_PATH}/config/docker/compose.base.yml" ]; then
  if mirror_pi_service_active kor35-mirror-stack.service || \
     docker ps --format '{{.Names}}' 2>/dev/null | grep -q 'kor35_mirror_frontend'; then
    STACK_OK=1
  fi
fi

if curl -fsS --max-time 3 http://127.0.0.1:8088/ >/dev/null 2>&1; then
  OMADA_OK=1
fi

mirror_pi_service_active kor35-mirror-dhcp-event.service && DHCP_EVENT_ACTIVE=1 || true
mirror_pi_service_active kor35-mirror-emergency-wifi.service && EMERGENCY_WIFI_ACTIVE=1 || true
mirror_pi_emergency_wifi_up && EMERGENCY_WIFI_ACTIVE=1 || true

if [ -f "${KOR35_REPO_PATH}/config/docker/nginx-docker/nginx_conf/mirror-event-local.conf" ]; then
  NGINX_EVENT_VHOST=1
fi

if curl -fsS --max-time 5 http://127.0.0.1/api/healthz/ >/dev/null 2>&1; then
  HEALTH_LOCAL_OK=1
fi

# Conflitto: DHCP evento attivo ma internet raggiungibile (tipico errore su router)
if [ "$DHCP_EVENT_ACTIVE" = "1" ] && [ "$HAS_INTERNET" = "1" ]; then
  DHCP_CONFLICT=1
fi

EVENT_LAN_IP_ACTUAL="$(ip -4 -o addr show dev "$LAN_IFACE" 2>/dev/null | awk '{print $4}' | head -1 || true)"
EMERGENCY_IP_ACTUAL="$(ip -4 -o addr show dev "$EMERGENCY_WIFI_INTERFACE" 2>/dev/null | awk '{print $4}' | head -1 || true)"

if [ "$JSON_OUTPUT" = "1" ]; then
  cat <<EOF
{
  "mode": "$MODE",
  "has_internet": $HAS_INTERNET,
  "lan_interface": "$LAN_IFACE",
  "event_lan_ip": "${EVENT_LAN_IP_ACTUAL:-}",
  "emergency_wifi_ip": "${EMERGENCY_IP_ACTUAL:-}",
  "stack_ok": $STACK_OK,
  "omada_ok": $OMADA_OK,
  "dhcp_event_active": $DHCP_EVENT_ACTIVE,
  "emergency_wifi_active": $EMERGENCY_WIFI_ACTIVE,
  "nginx_event_vhost": $NGINX_EVENT_VHOST,
  "health_local_ok": $HEALTH_LOCAL_OK,
  "dhcp_conflict": $DHCP_CONFLICT
}
EOF
  exit 0
fi

mirror_pi_log "=== KOR35 Mirror — diagnostica rete ==="
echo "Modalità registrata:     $MODE"
echo "Internet (master):       $([ "$HAS_INTERNET" = "1" ] && echo OK || echo NON RAGGIUNGIBILE)"
echo "Interfaccia LAN evento:  $LAN_IFACE (${EVENT_LAN_IP_ACTUAL:-nessun IPv4})"
echo "WiFi emergenza ($EMERGENCY_WIFI_INTERFACE): ${EMERGENCY_IP_ACTUAL:-nessun IPv4} SSID=${EMERGENCY_WIFI_SSID}"
echo ""
echo "Stack Docker KOR35:      $([ "$STACK_OK" = "1" ] && echo OK || echo PROBLEMA)"
echo "Omada controller:        $([ "$OMADA_OK" = "1" ] && echo OK || echo NON RAGGIUNGIBILE)"
echo "Healthz locale:          $([ "$HEALTH_LOCAL_OK" = "1" ] && echo OK || echo FAIL)"
echo "DHCP evento (dnsmasq):   $([ "$DHCP_EVENT_ACTIVE" = "1" ] && echo ATTIVO || echo spento)"
echo "WiFi emergenza service:  $([ "$EMERGENCY_WIFI_ACTIVE" = "1" ] && echo ATTIVO || echo spento)"
echo "Nginx vhost evento HTTP: $([ "$NGINX_EVENT_VHOST" = "1" ] && echo attivo || echo disattivo)"
echo ""

if [ "$DHCP_CONFLICT" = "1" ]; then
  mirror_pi_warn "DHCP evento attivo con internet raggiungibile — rischio conflitto col router."
  mirror_pi_warn "Esegui: sudo ./scripts/mirror_network_apply_mode.sh --mode router"
fi

if [ "$MODE" = "event" ] && [ "$DHCP_EVENT_ACTIVE" != "1" ]; then
  mirror_pi_warn "Modalità event registrata ma DHCP evento non attivo."
fi

if [ "$MODE" = "router" ] && [ "$DHCP_EVENT_ACTIVE" = "1" ]; then
  mirror_pi_warn "Modalità router registrata ma DHCP evento ancora attivo."
fi

echo ""
echo "--- Interfacce IPv4 ---"
ip -4 addr show | grep -E '^[0-9]+:|inet ' || true

echo ""
echo "--- Timer sync mirror ---"
if command -v systemctl >/dev/null 2>&1; then
  systemctl list-timers --no-pager 2>/dev/null | grep -E 'kor35-mirror-' || true
else
  echo "(systemd non disponibile)"
fi

echo ""
echo "--- Docker (mirror) ---"
if [ -d "$(mirror_pi_compose_dir)" ]; then
  docker ps --format 'table {{.Names}}\t{{.Status}}' 2>/dev/null | grep -E 'kor35_mirror|omada' || true
fi

echo ""
echo "Prossimi passi:"
echo "  sudo ./scripts/mirror_network_apply_mode.sh --mode router   # a casa, collegato al router"
echo "  sudo ./scripts/mirror_network_apply_mode.sh --mode event    # bosco / offline"
echo "  sudo ./scripts/mirror_network_apply_mode.sh --mode auto     # boot: sceglie in automatico"
