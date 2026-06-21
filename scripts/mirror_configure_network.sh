#!/usr/bin/env bash
set -euo pipefail

# Configurazione rete mirror sul Pi locale (eseguire sul Raspberry).
#
# Uso:
#   sudo ./scripts/mirror_configure_network.sh
#   sudo ./scripts/mirror_configure_network.sh --mode event
#   sudo ./scripts/mirror_configure_network.sh --no-auto-mode
#
# Make (sul Pi):
#   make mirror-configure ENV=mirror MIRROR_NETWORK_MODE=router

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

NETWORK_MODE="${MIRROR_NETWORK_MODE:-router}"
INSTALL_AUTO_MODE="${MIRROR_NETWORK_AUTO_BOOT:-0}"

while [ $# -gt 0 ]; do
  case "$1" in
    --mode)
      NETWORK_MODE="${2:-}"
      shift 2
      ;;
    --no-auto-mode)
      INSTALL_AUTO_MODE=0
      shift
      ;;
    --auto-mode)
      INSTALL_AUTO_MODE=1
      shift
      ;;
    -h|--help)
      sed -n '1,14p' "$0"
      exit 0
      ;;
    *)
      echo "Argomento non riconosciuto: $1" >&2
      exit 1
      ;;
  esac
done

if [ "$(id -u)" -ne 0 ]; then
  echo "Eseguire come root: sudo $0" >&2
  exit 1
fi

install_args=()
if [ "$INSTALL_AUTO_MODE" = "0" ]; then
  install_args+=(--no-auto-mode)
fi

cd "$ROOT_DIR"
./scripts/install_mirror_network.sh "${install_args[@]}"
./scripts/mirror_network_apply_mode.sh --mode "$NETWORK_MODE"

if [ "$(id -u)" = "0" ] && [ -n "${SUDO_USER:-}" ]; then
  sudo -u "$SUDO_USER" ./scripts/mirror_network_check.sh
else
  ./scripts/mirror_network_check.sh
fi
