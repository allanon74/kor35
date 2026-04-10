#!/usr/bin/env bash
set -euo pipefail

# Ferma lo stack WSL Pi-like.
# Opzioni:
#   --volumes    docker compose down -v (cancella volumi Postgres locale del compose)
#   Altri argomenti passati a docker compose down

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib_wsl_pi_like.sh
source "$SCRIPT_DIR/lib_wsl_pi_like.sh"

VOLUMES_FLAG=()
DOWN_EXTRA=()

while [ $# -gt 0 ]; do
  case "$1" in
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

wsl_pi_require_docker
wsl_pi_require_stack_dir

echo "Arresto stack in $WSL_PI_STACK_DIR ..."
wsl_pi_compose down "${VOLUMES_FLAG[@]}" "${DOWN_EXTRA[@]}"
