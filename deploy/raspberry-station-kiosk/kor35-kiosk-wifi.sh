#!/usr/bin/env bash
# Connette il Pi kiosk al WiFi evento (kor35-larp) oppure a una rete di riserva.
# Va eseguito come root (il servizio kiosk lo chiama via sudo).
#
# La plancia dual-screen usa i profili NetworkManager: kor35-larp vince se c'è,
# altrimenti resta la rete di casa. Qui NM è già su Vodafone e NON cambia da solo
# finché quella rete è buona. Quindi: se esiste un profilo evento, stacca la
# casa e alza quello — anche se lo scan (mentre sei associato) non elenca Omada.
# Non riscrive la password dei profili già salvati.
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
PRIMARY_PRIORITY="${KIOSK_WIFI_PRIMARY_PRIORITY:-200}"
FALLBACK_PRIORITY="${KIOSK_WIFI_FALLBACK_PRIORITY:--100}"

log() { echo "[kor35-kiosk-wifi] $*"; }

unescape_nmcli() {
  local s="$1"
  printf '%s' "${s//\\:/:}"
}

# kor35-larp e kor35_larp (e maiuscole) sono la stessa rete evento.
normalize_ssid() {
  printf '%s' "$1" | tr '[:upper:]' '[:lower:]' | tr '_' '-' | tr -d '\r'
}

ssid_eq() {
  [ -n "$1" ] && [ -n "$2" ] && [ "$(normalize_ssid "$1")" = "$(normalize_ssid "$2")" ]
}

wifi_iface() {
  if [ -n "$IFACE" ]; then
    printf '%s\n' "$IFACE"
    return 0
  fi
  # p2p-dev-wlan0 è virtuale: attivarlo fallisce e il Pi torna in casa.
  nmcli -t -f DEVICE,TYPE device 2>/dev/null \
    | awk -F: '$2 == "wifi" && $1 !~ /^p2p/ { print $1; exit }'
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

connection_timestamp() {
  local name="$1" ts
  ts="$(nmcli -g connection.timestamp connection show "$name" 2>/dev/null || true)"
  case "$ts" in
    ''|*[!0-9]*) printf '%s\n' "0" ;;
    *) printf '%s\n' "$ts" ;;
  esac
}

# Profili di questo SSID, dal più usato (connessione manuale) al più vecchio.
connections_for_ssid() {
  local ssid="$1" name found ts
  [ -n "$ssid" ] || return 1
  while IFS= read -r name; do
    [ -n "$name" ] || continue
    found="$(nmcli -g 802-11-wireless.ssid connection show "$name" 2>/dev/null || true)"
    if ssid_eq "$found" "$ssid"; then
      ts="$(connection_timestamp "$name")"
      printf '%s\t%s\n' "$ts" "$name"
    fi
  done < <(connection_names)
}

wifi_connection_names() {
  local name type
  while IFS= read -r name; do
    [ -n "$name" ] || continue
    type="$(nmcli -g connection.type connection show "$name" 2>/dev/null || true)"
    [ "$type" = "802-11-wireless" ] && printf '%s\n' "$name"
  done < <(connection_names)
}

active_wifi_connection() {
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
  # scan dump = cache anche da associati; scan live a volte è "busy".
  iw dev "$iface" scan dump 2>/dev/null | sed -n 's/^[[:space:]]*SSID: //p' || true
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
    ssid_eq "$line" "$ssid" && return 0
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

remember_fallback_from_current() {
  local cur
  cur="$(current_ssid)"
  if [ -z "$FALLBACK_SSID" ] && [ -n "$cur" ] && ! ssid_eq "$cur" "$PRIMARY_SSID"; then
    FALLBACK_SSID="$cur"
    log "Rete di casa attuale usata come riserva: ${FALLBACK_SSID}"
  fi
}

disconnect_other_wifi() {
  local keep="${1:-}" name type line
  while IFS= read -r line; do
    [ -n "$line" ] || continue
    name="${line%%:*}"
    type="${line#*:}"
    type="${type%%:*}"
    [ "$type" = "802-11-wireless" ] || [ "$type" = "wifi" ] || continue
    [ -n "$keep" ] && [ "$name" = "$keep" ] && continue
    log "Stacco ${name} (resta su questa rete finché non la chiudi)"
    nmcli connection down "$name" >/dev/null 2>&1 || true
  done < <(nmcli -t -f NAME,TYPE connection show --active 2>/dev/null)
}

try_nmcli_up() {
  local name="$1" iface
  iface="$(wifi_iface || true)"
  if [ -n "$iface" ]; then
    nmcli -w 15 connection up "$name" ifname "$iface"
  else
    nmcli -w 15 connection up "$name"
  fi
}

pin_primary() {
  local name="$1" other
  [ -n "$name" ] || return 0
  nmcli connection modify "$name" \
    connection.autoconnect yes \
    connection.autoconnect-priority "$PRIMARY_PRIORITY" || true
  while IFS= read -r other; do
    [ -n "$other" ] || continue
    [ "$other" = "$name" ] && continue
    nmcli connection modify "$other" \
      connection.autoconnect yes \
      connection.autoconnect-priority "$FALLBACK_PRIORITY" || true
  done < <(wifi_connection_names)
}

# Stesso gesto del menu WiFi del desktop. Solo se non esiste già un profilo.
connect_new() {
  local ssid="$1" psk="$2" iface
  [ -n "$ssid" ] && [ -n "$psk" ] || return 1
  iface="$(wifi_iface || true)"
  log "Nuova connessione a ${ssid} (come dal desktop)"
  if [ -n "$iface" ]; then
    nmcli device wifi connect "$ssid" password "$psk" ifname "$iface"
  else
    nmcli device wifi connect "$ssid" password "$psk"
  fi
}

try_saved_profiles() {
  local ssid="$1" name prev
  local -a names=()
  prev="$(active_wifi_connection || true)"
  while IFS=$'\t' read -r _ name; do
    [ -n "$name" ] || continue
    names+=("$name")
  done < <(connections_for_ssid "$ssid" | sort -nr)
  if [ "${#names[@]}" -eq 0 ]; then
    return 1
  fi

  for name in "${names[@]}"; do
    log "Profilo salvato ${name} (password non modificata)"
    if try_nmcli_up "$name"; then
      LAST_PROFILE="$name"
      return 0
    fi
    log "Profilo ${name} occupato o rifiutato mentre un'altra rete è attiva"
  done

  log "Stacco la rete attuale per passare a ${ssid}"
  disconnect_other_wifi ""
  for name in "${names[@]}"; do
    if try_nmcli_up "$name"; then
      LAST_PROFILE="$name"
      return 0
    fi
    log "Profilo ${name} non si è attivato neppure da scollegati"
  done

  if [ -n "$prev" ]; then
    log "Ripristino ${prev}"
    try_nmcli_up "$prev" || true
  fi
  return 1
}

try_ssid() {
  local ssid="$1" psk="$2"
  LAST_PROFILE=""
  [ -n "$ssid" ] || return 1
  if ssid_eq "$(current_ssid)" "$ssid"; then
    log "Già connesso a ${ssid}"
    LAST_PROFILE="$(connections_for_ssid "$ssid" | sort -nr | head -n 1 | cut -f2-)"
    return 0
  fi
  if try_saved_profiles "$ssid"; then
    return 0
  fi
  if ! ssid_visible "$ssid"; then
    log "SSID non in elenco e nessun profilo salvato: ${ssid}"
    return 1
  fi
  connect_new "$ssid" "$psk" || return 1
  LAST_PROFILE="$(connections_for_ssid "$ssid" | sort -nr | head -n 1 | cut -f2-)"
  [ -n "$LAST_PROFILE" ] || LAST_PROFILE="$ssid"
  return 0
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
  remember_fallback_from_current
  attempt=1
  while [ "$attempt" -le "$PRIMARY_ATTEMPTS" ]; do
    refresh_scan
    if try_ssid "$PRIMARY_SSID" "$PRIMARY_PSK"; then
      pin_primary "$LAST_PROFILE"
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
  remember_fallback_from_current
  if ssid_eq "$(current_ssid)" "$PRIMARY_SSID"; then
    try_ssid "$PRIMARY_SSID" "$PRIMARY_PSK" || true
    pin_primary "$LAST_PROFILE"
    exit 0
  fi
  refresh_scan
  if try_ssid "$PRIMARY_SSID" "$PRIMARY_PSK"; then
    pin_primary "$LAST_PROFILE"
    log "Passato a ${PRIMARY_SSID} (staccata la rete di casa)"
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
