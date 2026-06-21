#!/usr/bin/env bash
# Retrocompatibilità: delega a kiosk-master.sh
exec /usr/local/bin/kiosk-master.sh "$@"
