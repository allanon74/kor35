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
# auto = rileva schermo grande/piccolo da xrandr (consigliato)
KIOSK_DETECT_OUTPUTS="${KIOSK_DETECT_OUTPUTS:-auto}"
KIOSK_STATUS_OUTPUT="${KIOSK_STATUS_OUTPUT:-HDMI-2}"
KIOSK_CONTROL_OUTPUT="${KIOSK_CONTROL_OUTPUT:-HDMI-1}"
KIOSK_STATUS_MODE="${KIOSK_STATUS_MODE:-1920x1200}"
KIOSK_CONTROL_MODE="${KIOSK_CONTROL_MODE:-1920x440}"
KIOSK_SWAP_SCREENS="${KIOSK_SWAP_SCREENS:-0}"
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
    echo "KIOSK_DETECT_OUTPUTS=${KIOSK_DETECT_OUTPUTS}"
    echo "KIOSK_SWAP_SCREENS=${KIOSK_SWAP_SCREENS}"
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

# Ritorna: name width height x y  (solo output connessi con geometria attiva)
list_connected_outputs() {
  xrandr --query | awk '
    / connected / {
      name = $1
      for (i = 1; i <= NF; i++) {
        if ($i ~ /^[0-9]+x[0-9]+[+][0-9]+[+][0-9]+/) {
          split($i, a, /[x+]/)
          print name, a[1], a[2], a[3], a[4]
          break
        }
      }
    }
  '
}

# Miglior modalità listata sotto un output (preferisce corrente *, altrimenti max area)
best_mode_for_output() {
  local out="$1"
  xrandr --query | awk -v o="$out" '
    $0 ~ "^" o " connected" { found=1; next }
    found && /^[A-Za-z0-9.-]+ connected/ { exit }
    found && /^[[:space:]]+[0-9]+x[0-9]+/ {
      mode = $1
      split(mode, a, "x")
      area = a[1] * a[2]
      if ($0 ~ /\*/) cur = mode
      if (area > max) { max = area; best = mode }
    }
    END {
      if (cur != "") print cur
      else if (best != "") print best
    }
  '
}

get_output_xywh() {
  local out="$1"
  xrandr --query | awk -v o="$out" '
    $1 == o && /connected/ {
      for (i = 1; i <= NF; i++) {
        if ($i ~ /^[0-9]+x[0-9]+[+][0-9]+[+][0-9]+/) {
          split($i, a, /[x+]/)
          print a[3], a[4], a[1], a[2]
          exit
        }
      }
    }
  '
}

apply_output_layout() {
  local out="$1" primary="$2" mode="$3" pos="$4"
  local -a primary_args=()
  [ "$primary" = "1" ] && primary_args=(--primary)

  if [ -n "$mode" ] && xrandr --output "$out" "${primary_args[@]}" --mode "$mode" --pos "$pos" --rotate normal 2>/dev/null; then
    return 0
  fi
  if [ -n "$mode" ]; then
    warn "Modalità ${mode} assente su ${out}, provo --auto"
  fi
  xrandr --output "$out" "${primary_args[@]}" --auto --pos "$pos" --rotate normal 2>/dev/null || \
    xrandr --output "$out" "${primary_args[@]}" --auto --rotate normal 2>/dev/null || \
    warn "xrandr fallito su ${out}"
}

detect_outputs_by_resolution() {
  local -a lines=()
  local name w h x y area max_area=0 min_area=999999999
  local big_out="" big_w=0 big_h=0 small_out="" small_w=0 small_h=0

  mapfile -t lines < <(list_connected_outputs)
  if [ "${#lines[@]}" -lt 2 ]; then
    warn "Meno di 2 output con geometria; uso nomi da config + --auto."
    return 1
  fi

  for line in "${lines[@]}"; do
    read -r name w h x y <<<"$line"
    area=$((w * h))
    if [ "$area" -ge "$max_area" ]; then
      max_area=$area
      big_out=$name
      big_w=$w
      big_h=$h
    fi
    if [ "$area" -le "$min_area" ]; then
      min_area=$area
      small_out=$name
      small_w=$w
      small_h=$h
    fi
  done

  KIOSK_STATUS_OUTPUT="$big_out"
  KIOSK_CONTROL_OUTPUT="$small_out"
  KIOSK_STATUS_MODE="$(best_mode_for_output "$big_out")"
  KIOSK_CONTROL_MODE="$(best_mode_for_output "$small_out")"
  [ -z "$KIOSK_STATUS_MODE" ] && KIOSK_STATUS_MODE="${big_w}x${big_h}"
  [ -z "$KIOSK_CONTROL_MODE" ] && KIOSK_CONTROL_MODE="${small_w}x${small_h}"

  log "Rilevati: STATUS=${KIOSK_STATUS_OUTPUT} ${KIOSK_STATUS_MODE} | CONTROL=${KIOSK_CONTROL_OUTPUT} ${KIOSK_CONTROL_MODE}"
  return 0
}

apply_screen_swap_if_requested() {
  if [ "$KIOSK_SWAP_SCREENS" != "1" ]; then
    return 0
  fi
  local tmp_out tmp_mode
  tmp_out="$KIOSK_STATUS_OUTPUT"
  tmp_mode="$KIOSK_STATUS_MODE"
  KIOSK_STATUS_OUTPUT="$KIOSK_CONTROL_OUTPUT"
  KIOSK_STATUS_MODE="$KIOSK_CONTROL_MODE"
  KIOSK_CONTROL_OUTPUT="$tmp_out"
  KIOSK_CONTROL_MODE="$tmp_mode"
  log "KIOSK_SWAP_SCREENS=1: ruoli schermo invertiti."
}

configure_displays_side_by_side() {
  local sw sh cw ch sx sy cx cy

  if [ "$KIOSK_DETECT_OUTPUTS" = "auto" ]; then
    detect_outputs_by_resolution || true
  fi
  apply_screen_swap_if_requested

  # Se la modalità in config non esiste sul connettore, best_mode_for_output la sostituisce.
  if [ "$KIOSK_DETECT_OUTPUTS" = "auto" ] || ! xrandr --query | grep -q "^${KIOSK_STATUS_OUTPUT} connected"; then
    :
  else
    local bm
    bm="$(best_mode_for_output "$KIOSK_STATUS_OUTPUT")"
    [ -n "$bm" ] && KIOSK_STATUS_MODE="$bm"
    bm="$(best_mode_for_output "$KIOSK_CONTROL_OUTPUT")"
    [ -n "$bm" ] && KIOSK_CONTROL_MODE="$bm"
  fi

  parse_mode "$KIOSK_STATUS_MODE"
  sw=$MODE_W
  sh=$MODE_H

  log "Layout: STATUS ${KIOSK_STATUS_OUTPUT} mode=${KIOSK_STATUS_MODE} @0,0 | CONTROL ${KIOSK_CONTROL_OUTPUT} mode=${KIOSK_CONTROL_MODE} @${sw},0"

  apply_output_layout "$KIOSK_STATUS_OUTPUT" 1 "$KIOSK_STATUS_MODE" "0x0"
  sleep 1
  apply_output_layout "$KIOSK_CONTROL_OUTPUT" 0 "$KIOSK_CONTROL_MODE" "${sw}x0"
  sleep 1

  # Geometria reale post-xrandr (non assumere 1920x1200 se --auto ha scelto altro)
  read -r sx sy sw sh <<<"$(get_output_xywh "$KIOSK_STATUS_OUTPUT")"
  read -r cx cy cw ch <<<"$(get_output_xywh "$KIOSK_CONTROL_OUTPUT")"

  if [ -z "${sw:-}" ] || [ "$sw" = "0" ]; then
    parse_mode "$KIOSK_STATUS_MODE"
    sw=$MODE_W
    sh=$MODE_H
    sx=0
    sy=0
  fi
  if [ -z "${cw:-}" ] || [ "$cw" = "0" ]; then
    parse_mode "$KIOSK_CONTROL_MODE"
    cw=$MODE_W
    ch=$MODE_H
    cx=$sw
    cy=0
  fi

  STATUS_GEOM="${sx:-0} ${sy:-0} ${sw} ${sh}"
  CONTROL_GEOM="${cx:-$sw} ${cy:-0} ${cw} ${ch}"
  CONTROL_XRANDR_OUT="$KIOSK_CONTROL_OUTPUT"

  log "Finestre: STATUS geom=${STATUS_GEOM} | CONTROL geom=${CONTROL_GEOM}"
}

configure_displays_auto() {
  detect_outputs_by_resolution || true
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

move_window_by_pid() {
  local pid="$1" x="$2" y="$3" w="$4" h="$5" wid="" attempt
  command -v wmctrl >/dev/null 2>&1 || return 0
  for attempt in $(seq 1 40); do
    wid="$(wmctrl -lp 2>/dev/null | awk -v pid="$pid" '$3 == pid {print $1; exit}')"
    if [ -n "${wid:-}" ]; then
      wmctrl -ir "$wid" -e "0,${x},${y},${w},${h}" 2>/dev/null || true
      wmctrl -ir "$wid" -b add,fullscreen 2>/dev/null || true
      return 0
    fi
    sleep 0.25
  done
  warn "wmctrl: finestra pid ${pid} non trovata per posizione ${x},${y}"
}

launch_chromium() {
  local role="$1" url="$2" x="$3" y="$4" w="$5" h="$6" profile="$7"
  local chromium browser_pid
  chromium="$(find_chromium)" || { warn "Chromium non trovato"; exit 1; }

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
    --force-device-scale-factor=1 \
    "$url" &

  browser_pid=$!
  echo "$browser_pid" >"/tmp/kor35-kiosk-${role}.pid"
  sleep 2
  move_window_by_pid "$browser_pid" "$x" "$y" "$w" "$h"
  log "Avviato ${role} (pid ${browser_pid}) → ${url} @ ${x},${y} ${w}x${h} [${profile}]"
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
  sleep 3
  launch_chromium control "$control_url" "$cx" "$cy" "$cw" "$ch" "$CONTROL_PROFILE"
  map_touch_to_control

  wait
}

main
