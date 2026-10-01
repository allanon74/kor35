#!/usr/bin/env bash
# KOR35 — kiosk singolo schermo 800×480 (Console Ingegneria o Scientifica).
# Apre /pilot/?screen=station : ingegneria, scientifica e comunicazioni, poi il QR.
set -uo pipefail

export DISPLAY="${DISPLAY:-:0}"
export XAUTHORITY="${XAUTHORITY:-${HOME}/.Xauthority}"
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
export DBUS_SESSION_BUS_ADDRESS="${DBUS_SESSION_BUS_ADDRESS:-unix:path=${XDG_RUNTIME_DIR}/bus}"

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

prepare_runtime() {
  local uid runtime
  uid="$(id -u)"
  runtime="/run/user/${uid}"
  if [ ! -S "${XDG_RUNTIME_DIR:-}/wayland-0" ] && [ -S "${runtime}/wayland-0" ]; then
    export XDG_RUNTIME_DIR="$runtime"
  else
    export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-$runtime}"
  fi
  if [ -S "${XDG_RUNTIME_DIR}/wayland-0" ]; then
    export WAYLAND_DISPLAY="${WAYLAND_DISPLAY:-wayland-0}"
  else
    unset WAYLAND_DISPLAY || true
  fi
  if [ -S "${XDG_RUNTIME_DIR}/bus" ]; then
    export DBUS_SESSION_BUS_ADDRESS="unix:path=${XDG_RUNTIME_DIR}/bus"
  fi
}

# Su Pi OS il desktop è Wayland: :0 è Xwayland. xset risponde appena il
# socket X esiste, prima che il compositor abbia un frame. Chromium lanciato
# in quel momento resta bianco finché non lo si riavvia a sessione pronta.
session_ready() {
  prepare_runtime
  if [ -n "${WAYLAND_DISPLAY:-}" ] && [ -S "${XDG_RUNTIME_DIR}/${WAYLAND_DISPLAY}" ]; then
    return 0
  fi
  xset q >/dev/null 2>&1 || return 1
  xrandr --query 2>/dev/null | awk '/ connected/{found=1} END{exit !found}'
}

wait_for_session() {
  local i now age sock
  for i in $(seq 1 90); do
    if session_ready; then
      if [ -n "${WAYLAND_DISPLAY:-}" ]; then
        sock="${XDG_RUNTIME_DIR}/${WAYLAND_DISPLAY}"
        now="$(date +%s)"
        age=$(( now - $(stat -c %Y "$sock" 2>/dev/null || echo "$now") ))
        if [ "$age" -lt 20 ]; then
          log "Wayland appena avviato, attendo il primo frame"
          sleep 3
          prepare_runtime
        fi
        log "Sessione Wayland pronta (${WAYLAND_DISPLAY})"
      else
        log "Sessione X11 pronta (${DISPLAY})"
      fi
      return 0
    fi
    sleep 1
  done
  warn "Sessione grafica non pronta"
  return 1
}

configure_wayland_output() {
  local out transform
  command -v wlr-randr >/dev/null 2>&1 || {
    log "Wayland: modalità del pannello invariata (un solo schermo, niente xrandr su Xwayland)"
    return 0
  }
  out="$(wlr-randr 2>/dev/null | awk 'NF && $1 !~ /^$/ { print $1; exit }')"
  [ -n "$out" ] || return 0
  case "$KIOSK_ROTATE" in
    left) transform=90 ;;
    right) transform=270 ;;
    inverted) transform=180 ;;
    *) transform=normal ;;
  esac
  wlr-randr --output "$out" --mode "${KIOSK_MODE}" --transform "$transform" \
    || wlr-randr --output "$out" --transform "$transform" \
    || true
  log "Wayland output ${out} transform ${transform}"
}

configure_display() {
  local out
  if [ -n "${WAYLAND_DISPLAY:-}" ]; then
    configure_wayland_output
    return 0
  fi
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

# xinput sul server Xwayland non mappa il touch e riempie il journal con
# «running xinput against an Xwayland server». Sul pannello 800×480 c'è un
# solo output: il touch è già quello schermo.
map_touch() {
  local out dev_id
  if [ -n "${WAYLAND_DISPLAY:-}" ]; then
    return 0
  fi
  out="$(cat /tmp/kor35-kiosk-station-output 2>/dev/null || true)"
  [ -n "$out" ] || return 0
  command -v xinput >/dev/null 2>&1 || return 0
  while IFS= read -r dev_id; do
    [ -n "$dev_id" ] || continue
    xinput map-to-output "$dev_id" "$out" 2>/dev/null || true
  done < <(
    xinput list 2>/dev/null | awk -F'id=' '
      /[Tt]ouch|[Pp]en|[Ii][Ll]itek/ && !/[Kk]eyboard/ {
        gsub(/[^0-9].*/, "", $2)
        if ($2 != "") print $2
      }
    '
  )
}

disable_blank() {
  if [ -n "${WAYLAND_DISPLAY:-}" ]; then
    return 0
  fi
  xset s off || true
  xset -dpms || true
  xset s noblank || true
  if command -v unclutter >/dev/null 2>&1; then
    pkill -x unclutter 2>/dev/null || true
    unclutter -idle 0.5 -root >/dev/null 2>&1 &
  fi
}

launch_chromium() {
  local url="$1" chromium pid
  chromium="$(find_chromium)" || { warn "Chromium non trovato"; return 1; }
  mkdir -p "$KIOSK_PROFILE"
  rm -f "$KIOSK_PROFILE/SingletonLock" "$KIOSK_PROFILE/SingletonSocket" "$KIOSK_PROFILE/SingletonCookie" 2>/dev/null || true
  local -a cmd
  cmd=(
    "$chromium"
    --no-first-run
    --disable-session-crashed-bubble
    --disable-infobars
    --disable-dev-shm-usage
    --disable-pinch
    --overscroll-history-navigation=0
    --ignore-certificate-errors
    --password-store=basic
    --user-data-dir="$KIOSK_PROFILE"
    --kiosk
    --force-device-scale-factor=1
  )
  if [ -n "${WAYLAND_DISPLAY:-}" ] && [ "${KIOSK_FORCE_X11:-0}" != "1" ]; then
    CHROMIUM_BACKEND=wayland
    cmd+=(--ozone-platform=wayland)
    env -u DISPLAY \
      XDG_RUNTIME_DIR="$XDG_RUNTIME_DIR" \
      WAYLAND_DISPLAY="$WAYLAND_DISPLAY" \
      "${cmd[@]}" "$url" &
  else
    CHROMIUM_BACKEND=x11
    cmd+=(--window-position=0,0 --window-size=800,480)
    "${cmd[@]}" "$url" &
  fi
  pid=$!
  echo "$pid" >/tmp/kor35-kiosk-station.pid
  log "Chromium pid ${pid} backend ${CHROMIUM_BACKEND} → ${url}"
}

main() {
  local base url pid
  CHROMIUM_BACKEND=x11
  wait_for_session || exit 1
  ensure_wifi
  base="$(resolve_working_base)"
  PILOT_BASE_URL="$base"
  url="${base}${KIOSK_START_PATH}"
  configure_display
  disable_blank
  map_touch
  if [ -z "${WAYLAND_DISPLAY:-}" ]; then
    (
      while true; do
        sleep 45
        map_touch
      done
    ) &
  fi
  while true; do
    launch_chromium "$url" || exit 1
    pid="$(cat /tmp/kor35-kiosk-station.pid)"
    if [ "$CHROMIUM_BACKEND" = "wayland" ]; then
      sleep 4
      if ! kill -0 "$pid" 2>/dev/null; then
        warn "Chromium Wayland uscito subito, riprovo via X11"
        KIOSK_FORCE_X11=1
        continue
      fi
    fi
    wait "$pid" || true
    log "Chromium terminato, riavvio"
    sleep 2
  done
}

main
