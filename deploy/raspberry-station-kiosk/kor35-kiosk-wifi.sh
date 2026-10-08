#!/usr/bin/env bash
# WiFi della console stazione, sullo stesso modello della plancia dual-screen.
#
# NetworkManager tiene i profili. Questo script NON stacca la rete attuale:
# se kor35-larp è già su, non la tocca. Se non lo è, alza il profilo salvato
# una volta sola. Le password non si riscrivono.
set -uo pipefail

ENV_FILE="${KOR35_KIOSK_STATION_ENV:-/etc/kor35/kiosk-station.env}"
# shellcheck source=/dev/null
[ -f "$ENV_FILE" ] && source "$ENV_FILE"

PRIMARY_SSID="${KIOSK_WIFI_PRIMARY_SSID:-kor35-larp}"
PRIMARY_PSK="${KIOSK_WIFI_PRIMARY_PSK:-}"
IFACE="${KIOSK_WIFI_IFACE:-}"
PRIMARY_PRIORITY="${KIOSK_WIFI_PRIMARY_PRIORITY:-100}"

log() { echo "[kor35-kiosk-wifi] $*"; }

normalize_ssid() {
  printf '%s' "$1" | tr '[:upper:]' '[:lower:]' | tr '_' '-' | tr -d '\r'
}

is_event_ssid() {
  case "$(normalize_ssid "$1")" in
    *kor35*larp*) return 0 ;;
  esac
  return 1
}

wifi_iface() {
  if [ -n "$IFACE" ]; then
    printf '%s\n' "$IFACE"
    return 0
  fi
  nmcli -t -f DEVICE,TYPE device 2>/dev/null \
    | awk -F: '$2 == "wifi" && $1 !~ /^p2p/ { print $1; exit }'
}

current_ssid() {
  local iface ssid line
  iface="$(wifi_iface || true)"
  if [ -n "$iface" ] && command -v iw >/dev/null 2>&1; then
    ssid="$(iw dev "$iface" link 2>/dev/null | sed -n 's/^[[:space:]]*SSID: //p' | head -n 1)"
    if [ -n "$ssid" ]; then
      printf '%s\n' "$ssid"
      return 0
    fi
  fi
  line="$(nmcli -t -f ACTIVE,SSID dev wifi 2>/dev/null \
    | awk -F: '$1 == "yes" && $2 != "" { print substr($0, index($0, ":") + 1); exit }')"
  printf '%s\n' "${line//\\:/:}"
}

connection_names() {
  nmcli -g NAME connection show 2>/dev/null || true
}

# Nome del profilo evento più usato. Vuoto se non c'è.
event_profile() {
  local name found ts best_name="" best_ts=-1
  while IFS= read -r name; do
    [ -n "$name" ] || continue
    found="$(nmcli -g 802-11-wireless.ssid connection show "$name" 2>/dev/null || true)"
    is_event_ssid "$found" || continue
    ts="$(nmcli -g connection.timestamp connection show "$name" 2>/dev/null || echo 0)"
    case "$ts" in
      ''|*[!0-9]*) ts=0 ;;
    esac
    if [ "$ts" -ge "$best_ts" ]; then
      best_ts=$ts
      best_name=$name
    fi
  done < <(connection_names)
  printf '%s\n' "$best_name"
}

active_wifi_name() {
  local line name type
  while IFS= read -r line; do
    [ -n "$line" ] || continue
    name="${line%%:*}"
    type="${line#*:}"
    type="${type%%:*}"
    if [ "$type" = "802-11-wireless" ] || [ "$type" = "wifi" ]; then
      printf '%s\n' "$name"
      return 0
    fi
  done < <(nmcli -t -f NAME,TYPE connection show --active 2>/dev/null)
}

bring_up() {
  local name="$1" iface
  iface="$(wifi_iface || true)"
  if [ -n "$iface" ]; then
    nmcli -w 20 connection up "$name" ifname "$iface"
  else
    nmcli -w 20 connection up "$name"
  fi
}

cmd_current() {
  current_ssid
}

cmd_pin() {
  local name found
  while IFS= read -r name; do
    [ -n "$name" ] || continue
    found="$(nmcli -g 802-11-wireless.ssid connection show "$name" 2>/dev/null || true)"
    [ -n "$found" ] || continue
    if is_event_ssid "$found"; then
      nmcli connection modify "$name" connection.autoconnect yes connection.autoconnect-priority "$PRIMARY_PRIORITY" || true
      log "Priorità ${PRIMARY_PRIORITY} su ${name} (${found})"
    else
      nmcli connection modify "$name" connection.autoconnect yes connection.autoconnect-priority 0 || true
      log "Priorità 0 su ${name} (${found})"
    fi
  done < <(connection_names)
}

is_private_ip() {
  case "$1" in
    10.*|192.168.*|172.1[6-9].*|172.2[0-9].*|172.3[0-1].*) return 0 ;;
  esac
  return 1
}

resolved_v4() {
  local ip
  ip="$(getent ahostsv4 www.kor35.it 2>/dev/null | awk '{print $1; exit}')"
  if [ -z "$ip" ]; then
    ip="$(getent hosts www.kor35.it 2>/dev/null | awk '{print $1; exit}')"
  fi
  printf '%s\n' "$ip"
}

# Chiamato solo se healthz non risponde. Se il nome è già un IP della LAN
# non si tocca il profilo: il guasto non è il DNS.
cmd_dns() {
  local gw iface name ip
  if command -v resolvectl >/dev/null 2>&1; then
    resolvectl flush-caches >/dev/null 2>&1 || true
  fi
  gw="$(ip -4 route show default 2>/dev/null | awk '{print $3; exit}')"
  iface="$(wifi_iface || true)"
  name="$(active_wifi_name || true)"
  ip="$(resolved_v4)"
  log "Gateway '${gw:-nessuno}' iface '${iface:-}' profilo '${name:-}' DNS '${ip:-non risolve}'"
  if is_private_ip "$ip"; then
    log "www.kor35.it è già in LAN (${ip}). Non modifico il DNS"
    return 0
  fi
  if [ -z "$gw" ] || [ -z "$name" ]; then
    log "Niente gateway o profilo: lascio il DNS com'è"
    return 0
  fi
  log "Il nome esce dalla LAN. Punto il DNS al gateway ${gw} e spengo IPv6"
  nmcli connection modify "$name" ipv6.method disabled || true
  nmcli connection modify "$name" ipv4.dns "$gw" ipv4.ignore-auto-dns yes || true
  if [ -n "$iface" ]; then
    nmcli device reapply "$iface" >/dev/null 2>&1 || true
    if command -v resolvectl >/dev/null 2>&1; then
      resolvectl dns "$iface" "$gw" >/dev/null 2>&1 || true
      resolvectl domain "$iface" '~.' >/dev/null 2>&1 || true
      resolvectl flush-caches >/dev/null 2>&1 || true
    fi
  fi
  log "DNS dopo la correzione: $(resolved_v4 || echo 'non risolve')"
}

cmd_once() {
  local cur name
  if ! command -v nmcli >/dev/null 2>&1; then
    log "nmcli assente"
    exit 0
  fi
  cur="$(current_ssid)"
  if is_event_ssid "$cur"; then
    log "WiFi evento già attivo: ${cur}. Non stacco la rete attuale"
    exit 0
  fi
  name="$(event_profile)"
  if [ -z "$name" ]; then
    log "Nessun profilo kor35-larp. Resto su '${cur:-nessuna rete}'. Connettila una volta dal desktop."
    exit 0
  fi
  log "Attivo il profilo salvato ${name} (password non modificata)"
  if bring_up "$name"; then
    log "Profilo ${name} attivo"
    exit 0
  fi
  if [ -n "$PRIMARY_PSK" ]; then
    log "Il profilo non è salito. Provo una connessione nuova a ${PRIMARY_SSID}"
    iface="$(wifi_iface || true)"
    if [ -n "$iface" ]; then
      nmcli -w 20 device wifi connect "$PRIMARY_SSID" password "$PRIMARY_PSK" ifname "$iface" && exit 0
    else
      nmcli -w 20 device wifi connect "$PRIMARY_SSID" password "$PRIMARY_PSK" && exit 0
    fi
  fi
  log "Non sono passato a ${PRIMARY_SSID}. Resto su '${cur:-nessuna rete}'"
  exit 0
}

case "${1:-once}" in
  once) cmd_once ;;
  pin) cmd_pin ;;
  dns) cmd_dns ;;
  current) cmd_current ;;
  *)
    echo "Comandi: once | pin | dns | current" >&2
    exit 1
    ;;
esac
