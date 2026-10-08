#!/usr/bin/env bash
# KOR35 — console stazione, un solo schermo 800×480.
# Stesso modello della plancia dual-screen: non stacco il WiFi.
# Chromium parte solo quando https://www.kor35.it risponde, e si riapre se cade.
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
KIOSK_ROTATE="${KIOSK_ROTATE:-normal}"
KIOSK_MODE="${KIOSK_MODE:-800x480}"
KIOSK_START_PATH="${KIOSK_START_PATH:-/pilot/?screen=station&viewport=800x480}"
KIOSK_PROFILE="${KIOSK_PROFILE:-${HOME}/.config/kiosk-station}"
KIOSK_DISABLE_GPU="${KIOSK_DISABLE_GPU:-0}"

# shellcheck source=/dev/null
[ -f "$KIOSK_ENV" ] && source "$KIOSK_ENV"

log() { echo "[kiosk-station] $*"; }
warn() { echo "[kiosk-station] WARN: $*" >&2; }

[ -f "$NO_KIOSK_FLAG" ] && { log "NO_KIOSK attivo ($NO_KIOSK_FLAG), esco."; exit 0; }

log "modello plancia: non stacco il WiFi"

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
  local code
  code="$(curl -4 -k -s -o /dev/null -w "%{http_code}" --connect-timeout 4 --max-time 12 "$1" 2>/dev/null || true)"
  printf '%s\n' "${code:-000}"
}

server_up() {
  local base="$1" code
  code="$(http_code "${base%/}/api/healthz/")"
  [[ "$code" == 2* || "$code" == 3* ]]
}

log_net() {
  log "RAM: $(awk '/MemTotal|MemAvailable/ {printf "%s=%skB ", $1, $2}' /proc/meminfo)"
  log "SSID: $(iw dev "$(nmcli -t -f DEVICE,TYPE device 2>/dev/null | awk -F: '$2=="wifi" && $1 !~ /^p2p/ {print $1; exit}')" link 2>/dev/null | sed -n 's/^[[:space:]]*SSID: //p' | head -n 1)"
  log "Route: $(ip -4 route show default 2>/dev/null | head -n 1)"
  log "DNS www.kor35.it: $(getent hosts www.kor35.it 2>/dev/null | head -n 1 || echo 'non risolve')"
}

maybe_low_ram() {
  local avail
  avail="$(awk '/MemAvailable/ {print $2}' /proc/meminfo)"
  if [ "${avail:-0}" -lt 250000 ]; then
    KIOSK_DISABLE_GPU=1
    warn "Poca memoria libera (${avail} kB). Chromium parte senza GPU."
  fi
}

prepare_wifi_once() {
  [ "$KIOSK_WIFI_MANAGE" = "1" ] || { log "WiFi lasciato a NetworkManager"; return 0; }
  [ -x "$WIFI_HELPER" ] || { warn "Helper WiFi assente"; return 0; }
  sudo -n "$WIFI_HELPER" once || warn "helper WiFi once non eseguito"
}

repair_dns() {
  [ -x "$WIFI_HELPER" ] || return 0
  sudo -n "$WIFI_HELPER" dns || true
}

# Stampa la base URL quando healthz risponde. Vuoto se non c'è.
probe_base() {
  local primary candidate normalized scheme
  primary="$(normalize_base "${PILOT_BASE_URL:-$DEFAULT_BASE}")" || primary="$DEFAULT_BASE"
  normalized="${primary#https://}"
  normalized="${normalized#http://}"
  for scheme in https http; do
    candidate="${scheme}://${normalized}"
    if server_up "$candidate"; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done
  return 1
}

wait_for_display() {
  local _
  if [ -S "${XDG_RUNTIME_DIR}/wayland-0" ] || [ -S "${XDG_RUNTIME_DIR}/wayland-1" ]; then
    log "Sessione Wayland presente. Chromium userà Wayland, non Xwayland."
    return 0
  fi
  for _ in $(seq 1 60); do
    xset q >/dev/null 2>&1 && return 0
    sleep 1
  done
  warn "Né Wayland né X su ${DISPLAY}"
  return 1
}

configure_x11() {
  local out
  command -v xrandr >/dev/null 2>&1 || return 0
  xset q >/dev/null 2>&1 || return 0
  out="$(xrandr --query | awk '/ connected/{print $1; exit}')"
  [ -n "$out" ] || return 0
  log "X11 ${out} mode ${KIOSK_MODE} rotate ${KIOSK_ROTATE}"
  if xrandr --query | awk -v o="$out" -v m="$KIOSK_MODE" '
      $1 == o { inside=1; next }
      inside && $1 ~ /^[A-Za-z]/ { exit }
      inside && $1 == m { found=1 }
      END { exit !found }
    '; then
    xrandr --output "$out" --mode "$KIOSK_MODE" --rotate "$KIOSK_ROTATE" || xrandr --output "$out" --auto || true
  else
    xrandr --output "$out" --auto --rotate "$KIOSK_ROTATE" || true
  fi
  xset s off || true
  xset -dpms || true
  xset s noblank || true
}

ozone_args() {
  if [ -S "${XDG_RUNTIME_DIR}/wayland-0" ]; then
    export WAYLAND_DISPLAY=wayland-0
    printf '%s\n' "--ozone-platform=wayland"
    return 0
  fi
  if [ -S "${XDG_RUNTIME_DIR}/wayland-1" ]; then
    export WAYLAND_DISPLAY=wayland-1
    printf '%s\n' "--ozone-platform=wayland"
    return 0
  fi
  unset WAYLAND_DISPLAY || true
  printf '%s\n' "--ozone-platform=x11"
}

launch_chromium() {
  local url="$1" chromium ozone
  chromium="$(find_chromium)" || { warn "Chromium non trovato"; return 1; }
  ozone="$(ozone_args)"
  mkdir -p "$KIOSK_PROFILE"
  rm -f "$KIOSK_PROFILE/SingletonLock" "$KIOSK_PROFILE/SingletonSocket" "$KIOSK_PROFILE/SingletonCookie" 2>/dev/null || true
  local -a gpu=()
  if [ "$KIOSK_DISABLE_GPU" = "1" ]; then
    gpu=(--disable-gpu)
  fi
  # shellcheck disable=SC2086
  "$chromium" \
    --no-first-run \
    --disable-session-crashed-bubble \
    --disable-infobars \
    --disable-dev-shm-usage \
    --disable-background-networking \
    --disable-sync \
    --disable-translate \
    --renderer-process-limit=1 \
    --disable-features=Translate,BackForwardCache,MediaRouter \
    --disk-cache-size=1048576 \
    --ignore-certificate-errors \
    --disable-ipv6 \
    --password-store=basic \
    --user-data-dir="$KIOSK_PROFILE" \
    ${gpu[@]+"${gpu[@]}"} \
    "$ozone" \
    --kiosk \
    --start-fullscreen \
    --window-position=0,0 \
    --window-size=800,480 \
    --force-device-scale-factor=1 \
    "$url" &
  echo $! >/tmp/kor35-kiosk-station.pid
  log "Chromium pid $(cat /tmp/kor35-kiosk-station.pid) → ${url} (${ozone})"
}

stop_chromium() {
  local pid
  pid="$(cat /tmp/kor35-kiosk-station.pid 2>/dev/null || true)"
  if [ -n "$pid" ]; then
    kill "$pid" 2>/dev/null || true
    wait "$pid" 2>/dev/null || true
  fi
}

main() {
  local base misses pid
  wait_for_display || exit 1
  maybe_low_ram
  log_net
  prepare_wifi_once
  configure_x11
  if command -v unclutter >/dev/null 2>&1 && xset q >/dev/null 2>&1; then
    pkill -x unclutter 2>/dev/null || true
    unclutter -idle 0.5 -root >/dev/null 2>&1 &
  fi

  while true; do
    base=""
    misses=0
    while [ "$misses" -lt 30 ]; do
      if base="$(probe_base)"; then
        break
      fi
      misses=$((misses + 1))
      log "Server non raggiungibile (${misses}/30). Non stacco il WiFi, riprovo."
      if [ "$misses" -eq 2 ] || [ "$misses" -eq 10 ]; then
        repair_dns
        log_net
      fi
      sleep 3
      base=""
    done
    if [ -z "$base" ]; then
      warn "healthz ancora muto. Apro comunque ${PILOT_BASE_URL:-$DEFAULT_BASE}"
      base="$(normalize_base "${PILOT_BASE_URL:-$DEFAULT_BASE}")" || base="$DEFAULT_BASE"
    else
      log "Server ok: ${base}"
    fi

    launch_chromium "${base}${KIOSK_START_PATH}" || exit 1
    pid="$(cat /tmp/kor35-kiosk-station.pid)"
    misses=0
    while kill -0 "$pid" 2>/dev/null; do
      sleep 15
      if server_up "$base"; then
        misses=0
      else
        misses=$((misses + 1))
        log "healthz perso (${misses})"
        if [ "$misses" -ge 4 ]; then
          log "Chiudo Chromium e riapro quando il server risponde"
          stop_chromium
          repair_dns
          break
        fi
      fi
    done
    log "Chromium chiuso, nuovo giro"
    sleep 2
  done
}

main
