#!/usr/bin/env bash
# Connette il Pi kiosk al WiFi evento (kor35-larp) oppure a una rete di riserva.
# Va eseguito come root (il servizio kiosk lo chiama via sudo).
set -uo pipefail

ENV_FILE="${KOR35_KIOSK_STATION_ENV:-/etc/kor35/kiosk-station.env}"
# shellcheck source=/dev/null
[ -f "$ENV_FILE" ] && source "$ENV_FILE"

PRIMARY_SSID="${KIOSK_WIFI_PRIMARY_SSID:-kor35-larp}"
PRIMARY_PSK="${KIOSK_WIFI_PRIMARY_PSK:-}"
FALLBACK_SSID="${KIOSK_WIFI_FALLBACK_SSID:-}"
FALLBACK_PSK="${KIOSK_WIFI_FALLBACK_PSK:-}"
IFACE="${KIOSK_WIFI_IFACE:-}"

log() { echo "[kor35-kiosk-wifi] $*"; }

current_ssid() {
  nmcli -t -f ACTIVE,SSID dev wifi 2>/dev/null \
    | awk -F: '$1 == "yes" && $2 != "" { print $2; exit }'
}

ssid_visible() {
  local ssid="$1"
  nmcli -t -f SSID dev wifi list 2>/dev/null | awk -F: -v s="$ssid" '$1 == s { found=1 } END { exit !found }'
}

connection_exists() {
  nmcli -t -f NAME connection show 2>/dev/null | awk -F: -v n="$1" '$1 == n { found=1 } END { exit !found }'
}

try_saved() {
  local name="$1"
  [ -n "$name" ] || return 1
  connection_exists "$name" || return 1
  log "Profilo salvato: ${name}"
  if [ -n "$IFACE" ]; then
    nmcli connection up "$name" ifname "$IFACE"
  else
    nmcli connection up "$name"
  fi
}

try_psk() {
  local ssid="$1" psk="$2"
  [ -n "$ssid" ] && [ -n "$psk" ] || return 1
  if ! ssid_visible "$ssid"; then
    log "SSID non in elenco: ${ssid}"
    return 1
  fi
  log "Connessione a ${ssid}"
  if [ -n "$IFACE" ]; then
    nmcli device wifi connect "$ssid" password "$psk" ifname "$IFACE"
  else
    nmcli device wifi connect "$ssid" password "$psk"
  fi
}

try_ssid() {
  local ssid="$1" psk="$2"
  [ -n "$ssid" ] || return 1
  if [ "$(current_ssid)" = "$ssid" ]; then
    log "Già connesso a ${ssid}"
    return 0
  fi
  try_psk "$ssid" "$psk" && return 0
  try_saved "$ssid" && return 0
  return 1
}

cmd_scan() {
  nmcli device wifi rescan >/dev/null 2>&1 || true
  sleep 2
  nmcli -t -f SSID,SIGNAL dev wifi list | awk -F: 'NF >= 2 && $1 != "" { print $1 "\t" $2 }' | sort -u
}

cmd_connect() {
  local ssid="${1:-}" psk="${2:-}"
  [ -n "$ssid" ] && [ -n "$psk" ] || { echo "Uso: connect SSID PSK" >&2; exit 1; }
  try_psk "$ssid" "$psk"
}

cmd_ensure() {
  if ! command -v nmcli >/dev/null 2>&1; then
    log "nmcli assente"
    exit 10
  fi
  nmcli device wifi rescan >/dev/null 2>&1 || true
  sleep 2
  if try_ssid "$PRIMARY_SSID" "$PRIMARY_PSK"; then
    exit 0
  fi
  if try_ssid "$FALLBACK_SSID" "$FALLBACK_PSK"; then
    exit 0
  fi
  log "Né ${PRIMARY_SSID} né la rete di riserva sono disponibili"
  exit 10
}

case "${1:-ensure}" in
  ensure) cmd_ensure ;;
  scan) cmd_scan ;;
  connect) cmd_connect "${2:-}" "${3:-}" ;;
  current) current_ssid ;;
  *)
    echo "Comandi: ensure | scan | connect SSID PSK | current" >&2
    exit 1
    ;;
esac
