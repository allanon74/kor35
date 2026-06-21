#!/usr/bin/env bash
# KOR35 — client kiosk dual-screen (solo Chromium).
# Schermo grande (HDMI-2) → /pilot/?screen=status
# Schermo touch piccolo (HDMI-1) → /pilot/?screen=control
set -uo pipefail

export DISPLAY="${DISPLAY:-:0}"
export XAUTHORITY="${XAUTHORITY:-/home/pi/.Xauthority}"
export DBUS_SESSION_BUS_ADDRESS="${DBUS_SESSION_BUS_ADDRESS:-unix:path=/run/user/$(id -u)/bus}"

KIOSK_ENV="${KOR35_KIOSK_ENV:-/etc/kor35/kiosk.env}"
KIOSK_STATE="${KOR35_KIOSK_STATE:-/var/lib/kor35/kiosk-base-url}"
NO_KIOSK_FLAG="${KOR35_NO_KIOSK_FLAG:-/etc/kor35/NO_KIOSK}"

DEFAULT_BASE="https://www.kor35.it"
PROMPT_URL="${KOR35_KIOSK_PROMPT_URL:-0}"

# Hardware tipico installazione KOR35 (affiancati, non impilati).
KIOSK_LAYOUT="${KIOSK_LAYOUT:-side_by_side}"
KIOSK_STATUS_OUTPUT="${KIOSK_STATUS_OUTPUT:-HDMI-2}"
KIOSK_CONTROL_OUTPUT="${KIOSK_CONTROL_OUTPUT:-HDMI-1}"
KIOSK_STATUS_MODE="${KIOSK_STATUS_MODE:-1920x1200}"
KIOSK_CONTROL_MODE="${KIOSK_CONTROL_MODE:-1920x440}"
KIOSK_TOUCH_DEVICE="${KIOSK_TOUCH_DEVICE:-ILITEK ILITEK-TOUCH}"

STATUS_PROFILE="${KIOSK_STATUS_PROFILE:-${HOME}/.config/kiosk-status}"
CONTROL_PROFILE="${KIOSK_CONTROL_PROFILE:-${HOME}/.config/kiosk-control}"

log() { echo "[kiosk-master] $*"; }
warn() { echo "[kiosk-master] WARN: $*" >&2; }

# shellcheck source=/dev/null
[ -f "$KIOSK_ENV" ] && source "$KIOSK_ENV"

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
  if [[ -z "$raw" ]]; then
    return 1
  fi
  if [[ "$raw" != http://* && "$raw" != https://* ]]; then
    echo "https://${raw}"
    return
  fi
  echo "$raw"
}

http_code() {
  local url="$1"
  curl -k -s -o /dev/null -w "%{http_code}" --connect-timeout 5 --max-time 15 "$url" 2>/dev/null || echo "000"
}

probe_pilot_server() {
  local base="$1" code health pilot
  base="${base%/}"
  code="$(http_code "${base}/api/healthz/")"
  if [[ "$code" != 2* && "$code" != 3* ]]; then
    return 1
  fi
  pilot="$(curl -k -fsS --connect-timeout 5 --max-time 15 "${base}/api/pilot/console-enabled/" 2>/dev/null || true)"
  if [[ "$pilot" == *'"enabled": true'* ]] || [[ "$pilot" == *'"enabled":true'* ]]; then
    return 0
  fi
  # healthz OK ma console disabilitata: non fare fallback silenzioso su IP locale.
  warn "healthz OK su ${base} ma console pilota non abilitata (PILOT_CONSOLE_ENABLED?)"
  return 0
}

resolve_working_base() {
  local primary fallback normalized scheme candidate
  primary="$(normalize_base "${PILOT_BASE_URL:-$DEFAULT_BASE}")" || primary="$DEFAULT_BASE"
  fallback=""
  if [ -n "${PILOT_FALLBACK_BASE_URL:-}" ]; then
    fallback="$(normalize_base "$PILOT_FALLBACK_BASE_URL")" || fallback=""
  fi

  for candidate in "$primary" "$fallback"; do
    [ -z "$candidate" ] && continue
    normalized="${candidate#https://}"
    normalized="${normalized#http://}"
    for scheme in https http; do
      candidate="${scheme}://${normalized}"
      if probe_pilot_server "$candidate"; then
        echo "$candidate"
        return 0
      fi
    done
  done

  warn "Nessun server pilota raggiungibile; uso ${primary}"
  echo "$primary"
}

prompt_for_base_url() {
  local current="${1:-$DEFAULT_BASE}" answer=""
  if command -v zenity >/dev/null 2>&1 && [ -n "${DISPLAY:-}" ]; then
    answer="$(zenity --entry \
      --title="KOR35 Kiosk" \
      --text="Indirizzo server (default www.kor35.it):" \
      --entry-text="$current" 2>/dev/null || true)"
  elif [ -r /dev/tty ]; then
    echo "Indirizzo server KOR35 [${current}]: " >/dev/tty
    read -r answer </dev/tty || true
  fi
  [ -z "$answer" ] && answer="$current"
  normalize_base "$answer" || echo "$DEFAULT_BASE"
}

persist_base_url() {
  local base="$1"
  install -d -m 0755 "$(dirname "$KIOSK_STATE")" /etc/kor35
  printf '%s\n' "$base" >"$KIOSK_STATE"
  {
    echo "PILOT_BASE_URL=${base}"
    echo "KOR35_KIOSK_PROMPT_URL=${PROMPT_URL}"
    echo "KIOSK_LAYOUT=${KIOSK_LAYOUT}"
    echo "KIOSK_STATUS_OUTPUT=${KIOSK_STATUS_OUTPUT}"
    echo "KIOSK_CONTROL_OUTPUT=${KIOSK_CONTROL_OUTPUT}"
    echo "KIOSK_STATUS_MODE=${KIOSK_STATUS_MODE}"
    echo "KIOSK_CONTROL_MODE=${KIOSK_CONTROL_MODE}"
    [ -n "${PILOT_FALLBACK_BASE_URL:-}" ] && echo "PILOT_FALLBACK_BASE_URL=${PILOT_FALLBACK_BASE_URL}"
  } >"$KIOSK_ENV"
  chmod 644 "$KIOSK_ENV"
}

load_or_choose_base_url() {
  local base=""
  if [ -n "${PILOT_BASE_URL:-}" ]; then
    base="$(normalize_base "$PILOT_BASE_URL")" || base="$DEFAULT_BASE"
  elif [ -f "$KIOSK_STATE" ]; then
    base="$(normalize_base "$(tr -d '\r\n' <"$KIOSK_STATE")")" || base="$DEFAULT_BASE"
  fi

  if [ "${PROMPT_URL}" = "1" ]; then
    base="$(prompt_for_base_url "${base:-$DEFAULT_BASE}")"
  elif [ -z "$base" ]; then
    base="$DEFAULT_BASE"
  fi

  PILOT_BASE_URL="$base"
  PILOT_BASE_URL="$(resolve_working_base)"
  persist_base_url "$PILOT_BASE_URL"
  log "Server: ${PILOT_BASE_URL}"
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

parse_mode() {
  local mode="$1"
  MODE_W="${mode%x*}"
  MODE_H="${mode#*x}"
}

configure_displays_side_by_side() {
  local sw sh cw ch
  parse_mode "$KIOSK_STATUS_MODE"
  sw=$MODE_W
  sh=$MODE_H
  parse_mode "$KIOSK_CONTROL_MODE"
  cw=$MODE_W
  ch=$MODE_H

  log "Layout affiancato: STATUS ${KIOSK_STATUS_OUTPUT} ${sw}x${sh} @0,0 | CONTROL ${KIOSK_CONTROL_OUTPUT} ${cw}x${ch} @${sw},0"

  xrandr \
    --output "$KIOSK_STATUS_OUTPUT" --primary --mode "$KIOSK_STATUS_MODE" --pos 0x0 --rotate normal \
    --output "$KIOSK_CONTROL_OUTPUT" --mode "$KIOSK_CONTROL_MODE" --pos "${sw}x0" --rotate normal \
    2>/dev/null || true
  sleep 1
  xrandr \
    --output "$KIOSK_STATUS_OUTPUT" --primary --mode "$KIOSK_STATUS_MODE" --pos 0x0 --rotate normal \
    --output "$KIOSK_CONTROL_OUTPUT" --mode "$KIOSK_CONTROL_MODE" --pos "${sw}x0" --rotate normal \
    2>/dev/null || true

  STATUS_GEOM="0 0 ${sw} ${sh}"
  CONTROL_GEOM="${sw} 0 ${cw} ${ch}"
  CONTROL_XRANDR_OUT="$KIOSK_CONTROL_OUTPUT"
}

configure_displays_auto() {
  local -a lines=()
  local status_out="" control_out="" status_w=0 status_h=0 control_w=0 control_h=0
  local line name w h area max_area=0 min_area=999999999

  mapfile -t lines < <(xrandr --query | awk '
    /^[A-Za-z0-9.-]+ connected/ {
      name = $1
      for (i = 1; i <= NF; i++) {
        if ($i ~ /^[0-9]+x[0-9]+/) {
          split($i, a, "x")
          gsub(/\+.*/, "", a[2])
          print name, a[1], a[2]
          break
        }
      }
    }
  ')

  if [ "${#lines[@]}" -lt 1 ]; then
    configure_displays_side_by_side
    return
  fi

  for line in "${lines[@]}"; do
    read -r name w h <<<"$line"
    area=$((w * h))
    if [ "$area" -ge "$max_area" ]; then
      max_area=$area
      status_out=$name
      status_w=$w
      status_h=$h
    fi
    if [ "$area" -le "$min_area" ]; then
      min_area=$area
      control_out=$name
      control_w=$w
      control_h=$h
    fi
  done

  KIOSK_STATUS_OUTPUT="$status_out"
  KIOSK_CONTROL_OUTPUT="$control_out"
  KIOSK_STATUS_MODE="${status_w}x${status_h}"
  KIOSK_CONTROL_MODE="${control_w}x${control_h}"
  configure_displays_side_by_side
}

configure_displays() {
  if [ "$KIOSK_LAYOUT" = "side_by_side" ]; then
    configure_displays_side_by_side
  else
    configure_displays_auto
  fi
}

map_touch_to_control() {
  local dev_id=""
  if ! command -v xinput >/dev/null 2>&1; then
    return 0
  fi
  dev_id="$(xinput list --id-only "$KIOSK_TOUCH_DEVICE" 2>/dev/null || true)"
  if [ -n "$dev_id" ] && [ -n "${CONTROL_XRANDR_OUT:-}" ]; then
    xinput map-to-output "$dev_id" "$CONTROL_XRANDR_OUT" 2>/dev/null || true
    log "Touch ${KIOSK_TOUCH_DEVICE} (id ${dev_id}) → ${CONTROL_XRANDR_OUT}"
  fi
}

disable_power_management() {
  xset s off || true
  xset -dpms || true
  xset s noblank || true
  if command -v unclutter >/dev/null 2>&1; then
    pkill -x unclutter 2>/dev/null || true
    unclutter -idle 0.5 -root &
  fi
}

cleanup_singleton() {
  rm -f "$1/SingletonLock" "$1/SingletonSocket" "$1/SingletonCookie" 2>/dev/null || true
}

move_window() {
  local profile_substr="$1" x="$2" y="$3" w="$4" h="$5" wid=""
  command -v wmctrl >/dev/null 2>&1 || return 0
  wid="$(wmctrl -lx 2>/dev/null | awk -v s="$profile_substr" '$0 ~ s {print $1; exit}')"
  [ -n "${wid:-}" ] || return 0
  wmctrl -ir "$wid" -e "0,${x},${y},${w},${h}" 2>/dev/null || true
}

launch_chromium() {
  local role="$1" url="$2" x="$3" y="$4" w="$5" h="$6" profile="$7"
  local chromium profile_key
  chromium="$(find_chromium)" || { warn "Chromium non trovato"; exit 1; }
  profile_key="kiosk-${role}"
  mkdir -p "$profile"
  cleanup_singleton "$profile"

  # shellcheck disable=SC2086
  "$chromium" \
    --no-first-run \
    --disable-session-crashed-bubble \
    --disable-infobars \
    --disable-dev-shm-usage \
    --disable-background-networking \
    --disable-sync \
    --metrics-recording-disabled \
    --ignore-certificate-errors \
    --password-store=basic \
    --user-data-dir="$profile" \
    --kiosk --new-window \
    --window-position="${x},${y}" \
    --window-size="${w},${h}" \
    "$url" &

  echo $! >"/tmp/kor35-kiosk-${role}.pid"
  sleep 5
  move_window "$profile_key" "$x" "$y" "$w" "$h"
  log "Avviato ${role} → ${url} @ ${x},${y} ${w}x${h}"
}

main() {
  local status_url control_url sx sy sw sh cx cy cw ch
  status_url="${PILOT_BASE_URL}/pilot/?screen=status"
  control_url="${PILOT_BASE_URL}/pilot/?screen=control"

  load_or_choose_base_url
  status_url="${PILOT_BASE_URL}/pilot/?screen=status"
  control_url="${PILOT_BASE_URL}/pilot/?screen=control"

  wait_for_x
  sleep 2
  configure_displays
  disable_power_management

  pkill -9 chromium 2>/dev/null || true
  pkill -9 chromium-browser 2>/dev/null || true
  sleep 1

  read -r sx sy sw sh <<<"$STATUS_GEOM"
  read -r cx cy cw ch <<<"$CONTROL_GEOM"

  launch_chromium status "$status_url" "$sx" "$sy" "$sw" "$sh" "$STATUS_PROFILE"
  launch_chromium control "$control_url" "$cx" "$cy" "$cw" "$ch" "$CONTROL_PROFILE"
  map_touch_to_control

  wait
}

main
