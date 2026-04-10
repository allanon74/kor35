#!/usr/bin/env bash
set -euo pipefail

# Mostra lo stato dello stack docker per un profilo ambiente.
# Uso:
#   ./scripts/status_wsl_pi_like.sh --env dev-home

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib_wsl_pi_like.sh
source "$SCRIPT_DIR/lib_wsl_pi_like.sh"

ENV_PROFILE="dev-home"
STATUS_EXTRA=()

while [ $# -gt 0 ]; do
  case "$1" in
    --env)
      ENV_PROFILE="${2:-}"
      if [ -z "$ENV_PROFILE" ]; then
        echo "--env richiede un valore" >&2
        exit 1
      fi
      shift 2
      ;;
    --)
      shift
      STATUS_EXTRA+=("$@")
      break
      ;;
    *)
      STATUS_EXTRA+=("$1")
      shift
      ;;
  esac
done

wsl_pi_set_env_profile "$ENV_PROFILE"
wsl_pi_require_docker
wsl_pi_require_stack_dir

echo "Stato stack [$WSL_PI_ENV_PROFILE] in $WSL_PI_STACK_DIR"
wsl_pi_compose ps "${STATUS_EXTRA[@]}"
