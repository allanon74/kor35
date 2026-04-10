#!/usr/bin/env bash
set -euo pipefail

# Segue i log dello stack WSL Pi-like (docker compose logs -f).
# Opzioni: qualsiasi argomento extra va a docker compose logs (es. un nome servizio).

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib_wsl_pi_like.sh
source "$SCRIPT_DIR/lib_wsl_pi_like.sh"

wsl_pi_require_docker
wsl_pi_require_stack_dir

wsl_pi_compose logs -f "$@"
