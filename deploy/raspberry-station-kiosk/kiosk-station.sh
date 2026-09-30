#!/usr/bin/env bash
# KOR35 — kiosk singolo schermo 800×480 (Console Ingegneria o Scientifica).
# Apre /pilot/?screen=station : ingegneria, scientifica e comunicazioni, poi il QR.
set -uo pipefail

export DISPLAY="${DISPLAY:-:0}"
export XAUTHORITY="${XAUTHORITY:-${HOME}/.Xauthority}"
export DBUS_SESSION_BUS_ADDRESS="${DBUS_SESSION_BUS_ADDRESS:-unix:path=/run/user/$(id -u)/bus}"

KIOSK_ENV="${KOR35_KIOSK_STATION_ENV:-/etc/kor35/kiosk-station.env}"
NO_KIOSK_FLAG="${KOR35_NO_KIOSK_FLAG:-/etc/kor35/NO_KIOSK}"
WIFI_HELPER="${KOR35_WIFI_HELPER:-/usr/local/sbin/kor35-kiosk-wifi.sh}"

DEFAULT_BASE="https://www.kor35.it"
PILOT_BASE_URL="${PILOT_BASE_URL:-$DEFAULT_BASE}"
KIOSK_WIFI_MANAGE="${KIOSK_WIFI_MANAGE:-1}"
KIOSK_WIFI_PROMPT="${KIOSK_WIFI_PROMPT:-1}"
KIOSK_ROTATE="${KIOSK_ROTATE:-normal}"
KIOSK_MODE="${KIOSK_MODE:-800x480}"
KIOSK_START_PATH="${KIOSK_START_PATH:-/pilot/?screen=station&viewport=800x480}"
KIOSK_PROFILE="${KIOSK_PROFILE:-${HOME}/.config/kiosk-station}"

# shellcheck source=/dev/null
[ -f "$KIOSK_ENV" ] && source "$KIOSK_ENV"

log() { echo "[kiosk-station] $*"; }
warn() { echo "[kiosk-station] WARN: $*" >&2; }

[ -f "$NO_KIOSK_FLAG" ] && { log "NO_KIOSK attivo ($NO_KIOSK_FLAG), esco."; exit 0; }

find_chromium() {
  local c
  for c in chromium chromium-browser google-chrome; do
    command -v "$c" >/dev/null 2>&1 && echo "$c" && return 0
  done
  return 1
}

normalize_base() {
  local raw="${1:-}"
  raw="${raw%/}"
  [ -n "$raw" ] || return 1
  if [[ "$raw" != http://* && "$raw" != https://* ]]; then
    echo "https://${raw}"
    return
  fi
  echo "$raw"
}

http_code() {
  curl -k -s -o /dev/null -w "%{http_code}" --connect-timeout 4 --max-time 12 "$1" 2>/dev/null || echo "000"
}

resolve_working_base() {
  local primary candidate normalized scheme
  primary="$(normalize_base "${PILOT_BASE_URL:-$DEFAULT_BASE}")" || primary="$DEFAULT_BASE"
  for candidate in "$primary"; do
    normalized="${candidate#https://}"
    normalized="${normalized#http://}"
    for scheme in https http; do
      candidate="${scheme}://${normalized}"
      code="$(http_code "${candidate}/api/healthz/")"
      if [[ "$code" == 2* || "$code" == 3* ]]; then
        echo "$candidate"
        return 0
      fi
    done
  done
  warn "Server non raggiungibile, apro comunque ${primary}"
  echo "$primary"
}

update_env_key() {
  local key="$1" value="$2" escaped tmp
  [ -f "$KIOSK_ENV" ] || return 0
  escaped="$(printf '%q' "$value")"
  tmp="$(mktemp)"
  if grep -q "^${key}=" "$KIOSK_ENV"; then
    awk -v k="$key" -v v="$escaped" 'index($0, k"=") == 1 { print k"="v; next } { print }' "$KIOSK_ENV" >"$tmp"
  else
    cat "$KIOSK_ENV" >"$tmp"
    printf '%s=%s\n' "$key" "$escaped" >>"$tmp"
  fi
  cat "$tmp" >"$KIOSK_ENV"
  rm -f "$tmp"
}

ensure_wifi() {
  [ "$KIOSK_WIFI_MANAGE" = "1" ] || { log "WiFi gestito fuori da questo script"; return 0; }
  [ -x "$WIFI_HELPER" ] || { warn "Helper WiFi assente: $WIFI_HELPER"; return 0; }
  local rc=0
  sudo -n "$WIFI_HELPER" ensure || rc=$?
  if [ "$rc" -eq 0 ]; then
    log "WiFi ok ($(sudo -n "$WIFI_HELPER" current || true))"
    return 0
  fi
  if [ "$KIOSK_WIFI_PROMPT" != "1" ]; then
    warn "WiFi non disponibile (codice ${rc}) e prompt disattivato"
    return 0
  fi
  command -v zenity >/dev/null 2>&1 || { warn "zenity assente, niente scelta WiFi"; return 0; }
  local list ssid psk
  list="$(sudo -n "$WIFI_HELPER" scan || true)"
  [ -n "$list" ] || { warn "Nessuna rete WiFi visibile"; return 0; }
  ssid="$(printf '%s\n' "$list" | zenity --list --title="KOR35 — WiFi" \
    --text="kor35-larp non disponibile. Scegli un'altra rete:" \
    --column="SSID" --column="Segnale" \
    --width=480 --height=360 2>/dev/null || true)"
  [ -n "$ssid" ] || return 0
  psk="$(zenity --entry --hide-text --title="KOR35 — WiFi" \
    --text="Password per ${ssid}:" 2>/dev/null || true)"
  [ -n "$psk" ] || return 0
  if sudo -n "$WIFI_HELPER" connect "$ssid" "$psk"; then
    update_env_key KIOSK_WIFI_FALLBACK_SSID "$ssid"
    update_env_key KIOSK_WIFI_FALLBACK_PSK "$psk"
    log "Rete di riserva salvata: ${ssid}"
  else
    zenity --error --text="Connessione a ${ssid} non riuscita." 2>/dev/null || true
  fi
}

watch_event_wifi() {
  [ "$KIOSK_WIFI_MANAGE" = "1" ] || return 0
  [ -x "$WIFI_HELPER" ] || return 0
  (
    while true; do
      sleep "${KIOSK_WIFI_WATCH_SECONDS:-20}"
      sudo -n "$WIFI_HELPER" prefer || true
    done
  ) &
  log "Controllo periodico della rete evento"
}

wait_for_x() {
  local _
  for _ in $(seq 1 60); do
    xset q >/dev/null 2>&1 && return 0
    sleep 1
  done
  warn "X non disponibile su ${DISPLAY}"
  return 1
}

configure_display() {
  local out
  out="$(xrandr --query | awk '/ connected/{print $1; exit}')"
  [ -n "$out" ] || { warn "Nessun output video"; return 0; }
  log "Output ${out} modalità ${KIOSK_MODE} rotate ${KIOSK_ROTATE}"
  if xrandr --query | awk -v o="$out" -v m="$KIOSK_MODE" '
      $1 == o { inside=1; next }
      inside && $1 ~ /^[A-Za-z]/ { exit }
      inside && $1 == m { found=1 }
      END { exit !found }
    '; then
    xrandr --output "$out" --mode "$KIOSK_MODE" --rotate "$KIOSK_ROTATE" || xrandr --output "$out" --auto
  else
    xrandr --output "$out" --auto --rotate "$KIOSK_ROTATE" || true
  fi
  echo "$out" >/tmp/kor35-kiosk-station-output
}

map_touch() {
  local out dev_id
  out="$(cat /tmp/kor35-kiosk-station-output 2>/dev/null || true)"
  [ -n "$out" ] || return 0
  command -v xinput >/dev/null 2>&1 || return 0
  while IFS= read -r dev_id; do
    [ -n "$dev_id" ] || continue
    xinput map-to-output "$dev_id" "$out" 2>/dev/null || true
  done < <(
    xinput list | awk -F'id=' '
      /[Tt]ouch|[Pp]en|[Ii][Ll]itek/ && !/[Kk]eyboard/ {
        gsub(/[^0-9].*/, "", $2)
        if ($2 != "") print $2
      }
    '
  )
}

disable_blank() {
  xset s off || true
  xset -dpms || true
  xset s noblank || true
  if command -v unclutter >/dev/null 2>&1; then
    pkill -x unclutter 2>/dev/null || true
    unclutter -idle 0.5 -root >/dev/null 2>&1 &
  fi
}

launch_chromium() {
  local url="$1" chromium
  chromium="$(find_chromium)" || { warn "Chromium non trovato"; return 1; }
  mkdir -p "$KIOSK_PROFILE"
  rm -f "$KIOSK_PROFILE/SingletonLock" "$KIOSK_PROFILE/SingletonSocket" "$KIOSK_PROFILE/SingletonCookie" 2>/dev/null || true
  "$chromium" \
    --no-first-run \
    --disable-session-crashed-bubble \
    --disable-infobars \
    --disable-dev-shm-usage \
    --disable-pinch \
    --overscroll-history-navigation=0 \
    --ignore-certificate-errors \
    --password-store=basic \
    --user-data-dir="$KIOSK_PROFILE" \
    --kiosk \
    --window-position=0,0 \
    --window-size=800,480 \
    --force-device-scale-factor=1 \
    "$url" &
  echo $! >/tmp/kor35-kiosk-station.pid
  log "Chromium pid $(cat /tmp/kor35-kiosk-station.pid) → ${url}"
}

main() {
  local base url
  wait_for_x || exit 1
  ensure_wifi
  watch_event_wifi
  base="$(resolve_working_base)"
  PILOT_BASE_URL="$base"
  url="${base}${KIOSK_START_PATH}"
  configure_display
  disable_blank
  map_touch
  (
    while true; do
      sleep 45
      map_touch
    done
  ) &
  while true; do
    launch_chromium "$url" || exit 1
    wait "$(cat /tmp/kor35-kiosk-station.pid)" || true
    log "Chromium terminato, riavvio"
    sleep 2
  done
}

main
