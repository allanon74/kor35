#!/usr/bin/env bash
set -euo pipefail

# Ferma lo stack WSL Pi-like.
# Opzioni:
#   --env <nome> profilo ambiente: dev-home | dev-office | mirror | prod
#   --volumes    docker compose down -v (cancella volumi Postgres locale del compose)
#   Altri argomenti passati a docker compose down

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib_wsl_pi_like.sh
source "$SCRIPT_DIR/lib_wsl_pi_like.sh"

VOLUMES_FLAG=()
DOWN_EXTRA=()
ENV_PROFILE="dev-home"

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
    --volumes)
      VOLUMES_FLAG=(-v)
      shift
      ;;
    --)
      shift
      DOWN_EXTRA+=("$@")
      break
      ;;
    *)
      DOWN_EXTRA+=("$1")
      shift
      ;;
  esac
done

wsl_pi_set_env_profile "$ENV_PROFILE"
wsl_pi_require_docker
wsl_pi_require_stack_dir

echo "Arresto stack [$WSL_PI_ENV_PROFILE] in $WSL_PI_STACK_DIR ..."
wsl_pi_compose down "${VOLUMES_FLAG[@]}" "${DOWN_EXTRA[@]}"
