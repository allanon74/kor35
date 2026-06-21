#!/usr/bin/env bash
set -euo pipefail

# Esegue comandi di configurazione rete mirror sul Pi via SSH (da PC dev).
#
# Uso:
#   ./scripts/mirror_pi_remote.sh check
#   ./scripts/mirror_pi_remote.sh pull
#   ./scripts/mirror_pi_remote.sh install-network [--no-auto-mode]
#   ./scripts/mirror_pi_remote.sh network-mode --mode router|event|auto
#   ./scripts/mirror_pi_remote.sh configure [--mode router] [--no-auto-mode] [--no-git-pull]
#
# Make (da PC dev):
#   make mirror-pi-check
#   make mirror-pi-pull
#   make mirror-pi-install-network
#   make mirror-pi-network-mode MIRROR_NETWORK_MODE=router
#   make mirror-pi-configure MIRROR_NETWORK_MODE=router

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib_mirror_ssh.sh
source "$SCRIPT_DIR/lib_mirror_ssh.sh"

ACTION="${1:-}"
shift || true

REPO="$(mirror_ssh_repo_path)"
GIT_REF="${MIRROR_PI_GIT_REF:-main}"
NETWORK_MODE="${MIRROR_NETWORK_MODE:-router}"
INSTALL_AUTO_MODE=1
DO_GIT_PULL=1

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
    --no-git-pull)
      DO_GIT_PULL=0
      shift
      ;;
    --git-ref)
      GIT_REF="${2:-}"
      shift 2
      ;;
    -h|--help)
      sed -n '1,22p' "$0"
      exit 0
      ;;
    *)
      echo "Argomento non riconosciuto: $1" >&2
      exit 1
      ;;
  esac
done

install_network_flags() {
  if [ "$INSTALL_AUTO_MODE" = "0" ]; then
    echo "--no-auto-mode"
  fi
}

remote_pull() {
  mirror_ssh_run "cd '${REPO}' && git fetch origin && git checkout '${GIT_REF}' && git pull --ff-only origin '${GIT_REF}'"
}

remote_install_network() {
  local flags
  flags="$(install_network_flags)"
  mirror_ssh_run "cd '${REPO}' && sudo ./scripts/install_mirror_network.sh ${flags}"
}

remote_network_mode() {
  mirror_ssh_run "cd '${REPO}' && sudo ./scripts/mirror_network_apply_mode.sh --mode '${NETWORK_MODE}'"
}

remote_check() {
  mirror_ssh_run "cd '${REPO}' && ./scripts/mirror_network_check.sh"
}

case "$ACTION" in
  check)
    remote_check
    ;;
  pull)
    mirror_ssh_require_connection
    remote_pull
    ;;
  install-network)
    mirror_ssh_require_connection
    remote_install_network
    ;;
  network-mode)
    if [ -z "$NETWORK_MODE" ]; then
      echo "Specificare --mode router|event|auto (o MIRROR_NETWORK_MODE=...)" >&2
      exit 1
    fi
    mirror_ssh_require_connection
    remote_network_mode
    ;;
  configure|update)
    mirror_ssh_require_connection
    if [ "$DO_GIT_PULL" = "1" ]; then
      remote_pull
    fi
    remote_install_network
    if [ "$ACTION" = "configure" ]; then
      remote_network_mode
    fi
    remote_check
    ;;
  "")
    echo "Specificare azione: check | pull | install-network | network-mode | configure | update" >&2
    exit 1
    ;;
  *)
    echo "Azione non riconosciuta: $ACTION" >&2
    exit 1
    ;;
esac
