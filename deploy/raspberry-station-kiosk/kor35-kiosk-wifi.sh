#!/usr/bin/env bash
# Connette il Pi kiosk al WiFi evento (kor35-larp) oppure a una rete di riserva.
# Va eseguito come root (il servizio kiosk lo chiama via sudo).
#
# All'avvio la rete di casa è spesso già associata, mentre le EAP Omada
# compaiono dopo. ensure riprova kor35-larp prima di accettare la riserva.
# prefer (chiamato a ciclo dal kiosk) passa alla rete evento appena è visibile.
set -uo pipefail

ENV_FILE="${KOR35_KIOSK_STATION_ENV:-/etc/kor35/kiosk-station.env}"
# shellcheck source=/dev/null
[ -f "$ENV_FILE" ] && source "$ENV_FILE"

PRIMARY_SSID="${KIOSK_WIFI_PRIMARY_SSID:-kor35-larp}"
PRIMARY_PSK="${KIOSK_WIFI_PRIMARY_PSK:-}"
FALLBACK_SSID="${KIOSK_WIFI_FALLBACK_SSID:-}"
FALLBACK_PSK="${KIOSK_WIFI_FALLBACK_PSK:-}"
IFACE="${KIOSK_WIFI_IFACE:-}"
SCAN_WAIT="${KIOSK_WIFI_SCAN_WAIT:-2}"
PRIMARY_ATTEMPTS="${KIOSK_WIFI_PRIMARY_ATTEMPTS:-8}"
PRIMARY_PRIORITY="${KIOSK_WIFI_PRIMARY_PRIORITY:-100}"

log() { echo "[kor35-kiosk-wifi] $*"; }

unescape_nmcli() {
  local s="$1"
  printf '%s' "${s//\\:/:}"
}

wifi_iface() {
  if [ -n "$IFACE" ]; then
    printf '%s\n' "$IFACE"
    return 0
  fi
  nmcli -t -f DEVICE,TYPE device 2>/dev/null \
    | awk -F: '$2 == "wifi" { print $1; exit }'
}

current_ssid() {
  local iface line ssid
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
  unescape_nmcli "$line"
}

connection_names() {
  nmcli -g NAME connection show 2>/dev/null || true
}

connection_exists() {
  local name="$1" found
  [ -n "$name" ] || return 1
  while IFS= read -r found; do
    [ "$found" = "$name" ] && return 0
  done < <(connection_names)
  return 1
}

connection_for_ssid() {
  local ssid="$1" name found
  [ -n "$ssid" ] || return 1
  while IFS= read -r name; do
    [ -n "$name" ] || continue
    found="$(nmcli -g 802-11-wireless.ssid connection show "$name" 2>/dev/null || true)"
    if [ "$found" = "$ssid" ]; then
      printf '%s\n' "$name"
      return 0
    fi
  done < <(connection_names)
  return 1
}

wifi_connection_names() {
  local name type
  while IFS= read -r name; do
    [ -n "$name" ] || continue
    type="$(nmcli -g connection.type connection show "$name" 2>/dev/null || true)"
    [ "$type" = "802-11-wireless" ] && printf '%s\n' "$name"
  done < <(connection_names)
}

refresh_scan() {
  local iface
  iface="$(wifi_iface || true)"
  if [ -n "$iface" ]; then
    nmcli device wifi rescan ifname "$iface" >/dev/null 2>&1 || true
  else
    nmcli device wifi rescan >/dev/null 2>&1 || true
  fi
  sleep "$SCAN_WAIT"
}

nmcli_ssids() {
  local iface
  iface="$(wifi_iface || true)"
  if [ -n "$iface" ]; then
    nmcli -t -f SSID device wifi list ifname "$iface" 2>/dev/null || true
  else
    nmcli -t -f SSID device wifi list 2>/dev/null || true
  fi
}

iw_ssids() {
  local iface
  iface="$(wifi_iface || true)"
  [ -n "$iface" ] || return 0
  command -v iw >/dev/null 2>&1 || return 0
  iw dev "$iface" scan 2>/dev/null | sed -n 's/^[[:space:]]*SSID: //p' || true
}

visible_ssids() {
  nmcli_ssids
  iw_ssids
}

ssid_in_lines() {
  local ssid="$1" line
  while IFS= read -r line; do
    line="$(unescape_nmcli "$line")"
    [ "$line" = "$ssid" ] && return 0
  done
  return 1
}

ssid_visible() {
  local ssid="$1"
  [ -n "$ssid" ] || return 1
  if ssid_in_lines "$ssid" < <(nmcli_ssids); then
    return 0
  fi
  ssid_in_lines "$ssid" < <(iw_ssids)
}

bring_up() {
  local name="$1" iface
  iface="$(wifi_iface || true)"
  if [ -n "$iface" ]; then
    nmcli connection up "$name" ifname "$iface"
  else
    nmcli connection up "$name"
  fi
}

pin_primary() {
  local name other
  name="$(connection_for_ssid "$PRIMARY_SSID" || true)"
  [ -n "$name" ] || return 0
  nmcli connection modify "$name" \
    connection.autoconnect yes \
    connection.autoconnect-priority "$PRIMARY_PRIORITY" || true
  while IFS= read -r other; do
    [ -n "$other" ] || continue
    [ "$other" = "$name" ] && continue
    nmcli connection modify "$other" connection.autoconnect-priority 0 || true
  done < <(wifi_connection_names)
}

ensure_profile() {
  local ssid="$1" psk="$2" name iface
  name="$(connection_for_ssid "$ssid" || true)"
  if [ -z "$name" ]; then
    [ -n "$psk" ] || return 1
    name="$ssid"
    iface="$(wifi_iface || true)"
    if [ -n "$iface" ]; then
      nmcli connection add type wifi ifname "$iface" con-name "$name" ssid "$ssid" \
        wifi-sec.key-mgmt wpa-psk wifi-sec.psk "$psk" >/dev/null
    else
      nmcli connection add type wifi con-name "$name" ssid "$ssid" \
        wifi-sec.key-mgmt wpa-psk wifi-sec.psk "$psk" >/dev/null
    fi
  elif [ -n "$psk" ]; then
    nmcli connection modify "$name" wifi-sec.key-mgmt wpa-psk wifi-sec.psk "$psk" >/dev/null
  fi
  printf '%s\n' "$name"
}

try_ssid() {
  local ssid="$1" psk="$2" name
  [ -n "$ssid" ] || return 1
  if [ "$(current_ssid)" = "$ssid" ]; then
    log "Già connesso a ${ssid}"
    return 0
  fi
  if ! ssid_visible "$ssid"; then
    log "SSID non in elenco: ${ssid}"
    return 1
  fi
  name="$(ensure_profile "$ssid" "$psk" || true)"
  [ -n "$name" ] || { log "Nessun profilo per ${ssid}"; return 1; }
  log "Connessione a ${ssid} (${name})"
  bring_up "$name"
}

cmd_scan() {
  refresh_scan
  visible_ssids | awk 'NF && !seen[$0]++ { print }'
}

cmd_connect() {
  local ssid="${1:-}" psk="${2:-}"
  [ -n "$ssid" ] && [ -n "$psk" ] || { echo "Uso: connect SSID PSK" >&2; exit 1; }
  refresh_scan
  try_ssid "$ssid" "$psk"
}

cmd_ensure() {
  local attempt
  if ! command -v nmcli >/dev/null 2>&1; then
    log "nmcli assente"
    exit 10
  fi
  attempt=1
  while [ "$attempt" -le "$PRIMARY_ATTEMPTS" ]; do
    refresh_scan
    if try_ssid "$PRIMARY_SSID" "$PRIMARY_PSK"; then
      pin_primary
      exit 0
    fi
    log "Tentativo ${attempt}/${PRIMARY_ATTEMPTS}: ${PRIMARY_SSID} non pronta"
    attempt=$((attempt + 1))
  done
  if try_ssid "$FALLBACK_SSID" "$FALLBACK_PSK"; then
    exit 0
  fi
  log "Né ${PRIMARY_SSID} né la rete di riserva sono disponibili"
  exit 10
}

cmd_prefer() {
  if ! command -v nmcli >/dev/null 2>&1; then
    exit 10
  fi
  if [ "$(current_ssid)" = "$PRIMARY_SSID" ]; then
    pin_primary
    exit 0
  fi
  refresh_scan
  if try_ssid "$PRIMARY_SSID" "$PRIMARY_PSK"; then
    pin_primary
    log "Passato a ${PRIMARY_SSID}"
    exit 0
  fi
  exit 10
}

case "${1:-ensure}" in
  ensure) cmd_ensure ;;
  prefer) cmd_prefer ;;
  scan) cmd_scan ;;
  connect) cmd_connect "${2:-}" "${3:-}" ;;
  current) current_ssid ;;
  *)
    echo "Comandi: ensure | prefer | scan | connect SSID PSK | current" >&2
    exit 1
    ;;
esac
