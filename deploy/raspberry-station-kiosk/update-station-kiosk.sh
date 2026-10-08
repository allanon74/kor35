#!/usr/bin/env bash
# Aggiorna e azzera la console stazione. Non tocca le password WiFi.
exec "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/reset-station-kiosk.sh" "$@"
