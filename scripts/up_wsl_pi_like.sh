#!/usr/bin/env bash
set -euo pipefail

# Avvia lo stack WSL Pi-like (Nginx + Gunicorn + Daphne + Postgres + Redis).
# Opzioni:
#   --setup      esegue prima setup_wsl_pi_like.sh (build frontend + symlink)
#   --no-build   non passa --build a docker compose up (riavvio veloce)
#   --skip-collectstatic non esegue collectstatic dopo l'avvio
#   Altri argomenti vengono passati a: docker compose up -d

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib_wsl_pi_like.sh
source "$SCRIPT_DIR/lib_wsl_pi_like.sh"

DO_SETUP=false
BUILD_FLAG=(--build)
RUN_COLLECTSTATIC=true
COMPOSE_EXTRA=()

while [ $# -gt 0 ]; do
  case "$1" in
    --setup)
      DO_SETUP=true
      shift
      ;;
    --no-build)
      BUILD_FLAG=()
      shift
      ;;
    --skip-collectstatic)
      RUN_COLLECTSTATIC=false
      shift
      ;;
    --)
      shift
      COMPOSE_EXTRA+=("$@")
      break
      ;;
    *)
      COMPOSE_EXTRA+=("$1")
      shift
      ;;
  esac
done

wsl_pi_require_docker
wsl_pi_require_stack_dir

if [ "$DO_SETUP" = true ]; then
  "$SCRIPT_DIR/setup_wsl_pi_like.sh"
else
  wsl_pi_require_backend_link || exit 1
fi

echo "Avvio stack in $WSL_PI_STACK_DIR ..."
wsl_pi_compose up -d "${BUILD_FLAG[@]}" "${COMPOSE_EXTRA[@]}"

if [ "$RUN_COLLECTSTATIC" = true ]; then
  echo "Eseguo collectstatic nel container backend..."
  wsl_pi_compose exec -T backend python manage.py collectstatic --noinput
fi

echo ""
echo "Stack avviato. App: http://127.0.0.1:8080"
echo "Log: $SCRIPT_DIR/logs_wsl_pi_like.sh"
echo "Stop: $SCRIPT_DIR/down_wsl_pi_like.sh"
