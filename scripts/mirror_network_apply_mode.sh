#!/usr/bin/env bash
set -euo pipefail

# Applica modalità rete mirror Pi: router | event | auto
#
# router — DHCP dal router, spegne dnsmasq 192.168.100.0/24, rimuove vhost HTTP evento
# event  — IP statico 192.168.100.1, DHCP+DNS locale, abilita vhost HTTP www.kor35.it
# auto   — event se internet non raggiungibile, altrimenti router
#
# Uso:
#   sudo ./scripts/mirror_network_apply_mode.sh --mode router
#   sudo ./scripts/mirror_network_apply_mode.sh --mode event
#   sudo ./scripts/mirror_network_apply_mode.sh --mode auto

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib_mirror_pi.sh
source "$SCRIPT_DIR/lib_mirror_pi.sh"

MODE=""
while [ $# -gt 0 ]; do
  case "$1" in
    --mode)
      MODE="${2:-}"
      shift 2
      ;;
    -h|--help)
      sed -n '1,14p' "$0"
      exit 0
      ;;
    *)
      mirror_pi_err "argomento non riconosciuto: $1"
      exit 1
      ;;
  esac
done

if [ -z "$MODE" ]; then
  mirror_pi_err "specificare --mode router|event|auto"
  exit 1
fi

if [ "$(id -u)" -ne 0 ]; then
  mirror_pi_err "eseguire come root (sudo)"
  exit 1
fi

mirror_pi_load_config
LAN_IFACE="$(mirror_pi_detect_lan_interface)" || {
  mirror_pi_err "interfaccia LAN evento non trovata (${EVENT_LAN_INTERFACE})"
  exit 1
}

if [ "$MODE" = "auto" ]; then
  if mirror_pi_has_internet; then
    MODE="router"
    mirror_pi_log "auto: internet OK → modalità router"
  else
    MODE="event"
    mirror_pi_log "auto: internet assente → modalità evento"
  fi
fi

case "$MODE" in
  router|event) ;;
  *)
    mirror_pi_err "modalità non valida: $MODE (usa router|event|auto)"
    exit 1
    ;;
esac

apply_event_lan_ip() {
  mirror_pi_log "LAN evento: ${EVENT_LAN_IP}/${EVENT_LAN_CIDR} su ${LAN_IFACE}"
  if command -v nmcli >/dev/null 2>&1; then
    nmcli dev set "$LAN_IFACE" managed yes 2>/dev/null || true
    if ! nmcli -t -f NAME con show | grep -qx 'kor35-mirror-event'; then
      nmcli con add type ethernet ifname "$LAN_IFACE" con-name kor35-mirror-event \
        ipv4.method manual ipv4.addresses "${EVENT_LAN_IP}/${EVENT_LAN_CIDR}" \
        ipv6.method ignore autoconnect yes
    else
      nmcli con modify kor35-mirror-event \
        ipv4.method manual ipv4.addresses "${EVENT_LAN_IP}/${EVENT_LAN_CIDR}" \
        connection.interface-name "$LAN_IFACE"
    fi
    nmcli con down kor35-mirror-router 2>/dev/null || true
    nmcli con down netplan-eth0 2>/dev/null || true
    nmcli con up kor35-mirror-event
  else
    dhclient -r "$LAN_IFACE" 2>/dev/null || true
    ip addr flush dev "$LAN_IFACE"
    ip link set "$LAN_IFACE" up
    ip addr add "${EVENT_LAN_IP}/${EVENT_LAN_CIDR}" dev "$LAN_IFACE"
  fi
}

apply_router_dhcp() {
  mirror_pi_log "LAN router: DHCP client su ${LAN_IFACE}"
  systemctl stop kor35-mirror-dhcp-event.service 2>/dev/null || true

  if command -v nmcli >/dev/null 2>&1; then
    nmcli dev set "$LAN_IFACE" managed yes 2>/dev/null || true
    nmcli con down kor35-mirror-event 2>/dev/null || true
    # Pi con netplan: rimuovi IP statico evento (es. 192.168.100.10) e usa solo DHCP router.
    if nmcli -t -f NAME con show | grep -qx 'netplan-eth0'; then
      nmcli con modify netplan-eth0 \
        ipv4.method auto ipv4.addresses "" \
        connection.interface-name "$LAN_IFACE" \
        connection.autoconnect yes
      nmcli con down kor35-mirror-router 2>/dev/null || true
      nmcli con up netplan-eth0
      return 0
    fi
    if ! nmcli -t -f NAME con show | grep -qx 'kor35-mirror-router'; then
      nmcli con add type ethernet ifname "$LAN_IFACE" con-name kor35-mirror-router \
        ipv4.method auto ipv6.method ignore autoconnect yes
    else
      nmcli con modify kor35-mirror-router ipv4.method auto connection.interface-name "$LAN_IFACE"
    fi
    nmcli con up kor35-mirror-router
  else
    ip addr flush dev "$LAN_IFACE" 2>/dev/null || true
    ip link set "$LAN_IFACE" up
    dhclient "$LAN_IFACE" 2>/dev/null || true
  fi
}

enable_nginx_event_vhost() {
  local src="${KOR35_REPO_PATH}/config/docker/nginx-docker/nginx_conf/mirror-event-local.conf.example"
  local dst="${KOR35_REPO_PATH}/config/docker/nginx-docker/nginx_conf/mirror-event-local.conf"
  if [ ! -f "$src" ]; then
    mirror_pi_warn "template nginx evento mancante: $src"
    return 0
  fi
  cp "$src" "$dst"
  mirror_pi_log "Abilitato vhost HTTP evento: mirror-event-local.conf"
  if docker ps --format '{{.Names}}' 2>/dev/null | grep -q 'kor35_mirror_frontend'; then
    (
      cd "$(mirror_pi_compose_dir)"
      export COMPOSE_PROJECT_NAME
      export KOR35_BACKEND_ENV_FILE
      docker compose -f compose.base.yml -f compose.mirror.yml exec -T frontend nginx -s reload
    ) || mirror_pi_warn "reload nginx fallito (container frontend non pronto?)"
  fi
}

disable_nginx_event_vhost() {
  local dst="${KOR35_REPO_PATH}/config/docker/nginx-docker/nginx_conf/mirror-event-local.conf"
  if [ -f "$dst" ]; then
    rm -f "$dst"
    mirror_pi_log "Rimosso vhost HTTP evento"
    if docker ps --format '{{.Names}}' 2>/dev/null | grep -q 'kor35_mirror_frontend'; then
      (
        cd "$(mirror_pi_compose_dir)"
        export COMPOSE_PROJECT_NAME
        export KOR35_BACKEND_ENV_FILE
        docker compose -f compose.base.yml -f compose.mirror.yml exec -T frontend nginx -s reload
      ) || true
    fi
  fi
}

ensure_emergency_wifi() {
  if command -v nmcli >/dev/null 2>&1; then
    if nmcli -t -f NAME con show 2>/dev/null | grep -qx 'Hotspot-Emergenza'; then
      nmcli dev set "$EMERGENCY_WIFI_INTERFACE" managed yes 2>/dev/null || true
      if ! nmcli -t -f NAME con show --active 2>/dev/null | grep -qx 'Hotspot-Emergenza'; then
        nmcli con up Hotspot-Emergenza 2>/dev/null || mirror_pi_warn "riavvio Hotspot-Emergenza NM fallito"
      fi
      mirror_pi_log "WiFi emergenza: NetworkManager Hotspot-Emergenza"
      return 0
    fi
  fi
  if ! mirror_pi_service_active kor35-mirror-emergency-wifi.service; then
    if systemctl is-enabled kor35-mirror-emergency-wifi.service 2>/dev/null | grep -q enabled; then
      systemctl start kor35-mirror-emergency-wifi.service || mirror_pi_warn "avvio WiFi emergenza (hostapd) fallito"
    fi
  fi
  if command -v nmcli >/dev/null 2>&1; then
    nmcli dev set "$EMERGENCY_WIFI_INTERFACE" managed no 2>/dev/null || true
  fi
  if ! ip -4 addr show dev "$EMERGENCY_WIFI_INTERFACE" 2>/dev/null | grep -q "${EMERGENCY_WIFI_IP}/"; then
    ip link set "$EMERGENCY_WIFI_INTERFACE" up 2>/dev/null || true
    ip addr add "${EMERGENCY_WIFI_IP}/${EMERGENCY_WIFI_CIDR}" dev "$EMERGENCY_WIFI_INTERFACE" 2>/dev/null || true
  fi
}

ensure_stack() {
  if [ -x "${KOR35_REPO_PATH}/scripts/mirror_boot_stack.sh" ]; then
    sudo -u pi env \
      KOR35_REPO_PATH="$KOR35_REPO_PATH" \
      COMPOSE_PROJECT_NAME="$COMPOSE_PROJECT_NAME" \
      KOR35_BACKEND_ENV_FILE="$KOR35_BACKEND_ENV_FILE" \
      "${KOR35_REPO_PATH}/scripts/mirror_boot_stack.sh" || mirror_pi_warn "mirror_boot_stack non riuscito"
  fi
}

if [ "$MODE" = "event" ]; then
  apply_event_lan_ip
  systemctl enable --now kor35-mirror-dhcp-event.service
  enable_nginx_event_vhost
  ensure_stack
  mirror_pi_log "Modalità EVENTO: Omada UI su http://${EVENT_LAN_IP}:8088 — giocatori su WiFi kor35-larp → http://www.kor35.it/"
else
  apply_router_dhcp
  systemctl disable --now kor35-mirror-dhcp-event.service 2>/dev/null || true
  disable_nginx_event_vhost
  mirror_pi_log "Modalità ROUTER: sync verso master attivo; DHCP locale 192.168.100.0/24 spento"
fi

ensure_emergency_wifi
mirror_pi_write_mode_state "$MODE"
mirror_pi_log "Modalità applicata: $MODE"
