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

echo ""
echo "Diagnostica pilot_tick:"
RUNNING_SERVICES="$(wsl_pi_compose ps --services --filter status=running 2>/dev/null || true)"
if printf '%s\n' "$RUNNING_SERVICES" | grep -qx 'pilot_tick'; then
  echo "- servizio pilot_tick: RUNNING"
else
  echo "- servizio pilot_tick: NON RUNNING"
fi

if printf '%s\n' "$RUNNING_SERVICES" | grep -qx 'backend'; then
  runtime_json="$(wsl_pi_compose exec -T backend python manage.py shell -c "import json; from django.utils import timezone; from pilotaggio.models import PilotRuntimeConfig; c=PilotRuntimeConfig.get_solo(); hb=c.tick_last_heartbeat; alive=False; delta=None; interval=float(c.tick_interval_secondi or 5.0); 
if hb is not None:
    delta=(timezone.now()-hb).total_seconds();
    alive = delta <= max(8.0, interval*2.5);
print(json.dumps({'tick_enabled': bool(c.tick_enabled), 'interval': interval, 'last_heartbeat': hb.isoformat() if hb else None, 'seconds_since_heartbeat': delta, 'alive': alive, 'login_required_console': bool(c.login_required_console)}))" 2>/dev/null || true)"
  if [ -n "${runtime_json:-}" ]; then
    echo "- runtime config: $runtime_json"
  else
    echo "- runtime config: non disponibile (backend non pronto?)"
  fi
else
  echo "- backend non running: impossibile leggere heartbeat runtime"
fi
