#!/usr/bin/env bash
set -euo pipefail

export DISPLAY=:0
export XAUTHORITY="/home/pi/.Xauthority"

PILOT_BASE_URL="${PILOT_BASE_URL:-http://10.42.0.1}"
STATUS_URL="${PILOT_BASE_URL}/pilot/?screen=status"
CONTROL_URL="${PILOT_BASE_URL}/pilot/?screen=control"

# Attendi X disponibile
for _ in $(seq 1 20); do
  if xset q >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

# Layout doppio schermo (adatta output dopo test con xrandr)
xrandr --output HDMI-1 --primary --mode 1920x1080 --pos 0x0 || true
xrandr --output HDMI-2 --mode 1920x440 --pos 0x1080 || true

# Disabilita power management
xset s off
xset -dpms
xset s noblank
unclutter -idle 1 -root &

# Browser fullscreen su entrambi gli schermi
chromium-browser \
  --kiosk \
  --noerrdialogs \
  --disable-infobars \
  --incognito \
  --window-position=0,0 \
  --window-size=1920,1080 \
  "${STATUS_URL}" &

sleep 2

chromium-browser \
  --kiosk \
  --noerrdialogs \
  --disable-infobars \
  --incognito \
  --window-position=0,1080 \
  --window-size=1920,440 \
  "${CONTROL_URL}" &

wait
