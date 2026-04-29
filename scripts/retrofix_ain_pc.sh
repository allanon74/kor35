#!/usr/bin/env bash
set -euo pipefail

# Retrofix dei PC legati ai tratti AIN pregressi.
# - Dry-run di default (sicuro in produzione).
# - Opzionale backup DB prima dell'applicazione.
#
# Esempi:
#   ./scripts/retrofix_ain_pc.sh --env prod
#   ./scripts/retrofix_ain_pc.sh --env prod --apply --with-backup
#   ./scripts/retrofix_ain_pc.sh --env prod --apply --personaggio-id 123

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib_wsl_pi_like.sh
source "$SCRIPT_DIR/lib_wsl_pi_like.sh"

ENV_PROFILE="prod"
APPLY=false
WITH_BACKUP=false
PERSONAGGIO_ID=""
AUTO_UP=false

usage() {
  cat <<'EOF'
Uso: retrofix_ain_pc.sh [opzioni]

Opzioni:
  --env <profilo>         Profilo stack: dev-home | dev-office | mirror | prod (default: prod)
  --apply                 Applica davvero i movimenti PC (default: dry-run)
  --with-backup           Esegue backup DB prima di --apply
  --personaggio-id <id>   Limita il fix a un singolo personaggio
  --auto-up               Se backend è fermo, avvia db/redis/backend automaticamente
  -h, --help              Mostra questo help
EOF
}

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
    --apply)
      APPLY=true
      shift
      ;;
    --with-backup)
      WITH_BACKUP=true
      shift
      ;;
    --personaggio-id)
      PERSONAGGIO_ID="${2:-}"
      if [ -z "$PERSONAGGIO_ID" ]; then
        echo "--personaggio-id richiede un valore" >&2
        exit 1
      fi
      if ! [[ "$PERSONAGGIO_ID" =~ ^[0-9]+$ ]]; then
        echo "--personaggio-id deve essere un intero positivo" >&2
        exit 1
      fi
      shift 2
      ;;
    --auto-up)
      AUTO_UP=true
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Argomento non riconosciuto: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

wsl_pi_set_env_profile "$ENV_PROFILE"
wsl_pi_require_docker
wsl_pi_require_stack_dir
wsl_pi_require_backend_link || exit 1
wsl_pi_require_backend_env || exit 1

echo "Profilo: $WSL_PI_ENV_PROFILE"
echo "Stack dir: $WSL_PI_STACK_DIR"
echo "Modalità: $([ "$APPLY" = true ] && echo "APPLY" || echo "DRY-RUN")"

if [ "$WITH_BACKUP" = true ] && [ "$APPLY" != true ]; then
  echo "--with-backup ha senso solo con --apply" >&2
  exit 1
fi

if [ "$WITH_BACKUP" = true ]; then
  echo "Eseguo backup DB pre-retrofix..."
  "$SCRIPT_DIR/backup_db_daily.sh" --env "$WSL_PI_ENV_PROFILE"
fi

is_backend_running() {
  local running
  running="$(wsl_pi_compose ps --status running --services backend 2>/dev/null || true)"
  [ "$running" = "backend" ]
}

if ! is_backend_running; then
  if [ "$AUTO_UP" = true ]; then
    echo "Backend non in esecuzione: avvio db/redis/backend..."
    wsl_pi_compose up -d db redis backend
  fi
fi

if ! is_backend_running; then
  echo "Il servizio backend non è in esecuzione per il profilo '$WSL_PI_ENV_PROFILE'." >&2
  echo "Avvio suggerito:" >&2
  echo "  ./scripts/up_wsl_pi_like.sh --env $WSL_PI_ENV_PROFILE --no-build" >&2
  echo "Oppure riesegui questo script con --auto-up." >&2
  exit 1
fi

CMD=(python manage.py retrofix_ain_pc)
if [ "$APPLY" = true ]; then
  CMD+=(--apply)
fi
if [ -n "$PERSONAGGIO_ID" ]; then
  CMD+=(--personaggio-id "$PERSONAGGIO_ID")
fi

echo "Eseguo: ${CMD[*]}"
wsl_pi_compose exec -T backend "${CMD[@]}"

echo "Operazione completata."
