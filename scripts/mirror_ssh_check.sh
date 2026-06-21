#!/usr/bin/env bash
set -euo pipefail

# Esegue mirror_network_check.sh sul Pi via SSH (da PC sviluppatore / agente Cursor).

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib_mirror_ssh.sh
source "$SCRIPT_DIR/lib_mirror_ssh.sh"

REPO="$(mirror_ssh_repo_path)"
mirror_ssh_run "cd '${REPO}' && ./scripts/mirror_network_check.sh"
