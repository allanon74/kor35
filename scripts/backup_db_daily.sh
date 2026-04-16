#!/usr/bin/env bash
set -euo pipefail

# Dump giornaliero PostgreSQL su file, con rotazione (default: 14 giorni).
# Pensato per girare sul server di produzione (ENV=prod), ma funziona anche per altri profili.
#
# Requisiti:
# - repo KOR35 presente sul server
# - docker + docker compose v2
# - stack avviato (o almeno servizio db esistente)
#
# Uso:
#   ./scripts/backup_db_daily.sh --env prod
#
# Variabili opzionali:
#   KOR35_DB_BACKUP_DIR=/var/backups/kor35/db
#   KOR35_DB_BACKUP_RETENTION_DAYS=14

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib_wsl_pi_like.sh
source "$SCRIPT_DIR/lib_wsl_pi_like.sh"

ENV_PROFILE="prod"
BACKUP_DIR="${KOR35_DB_BACKUP_DIR:-/var/backups/kor35/db}"
RETENTION_DAYS="${KOR35_DB_BACKUP_RETENTION_DAYS:-14}"

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
    *)
      echo "Argomento non riconosciuto: $1" >&2
      exit 2
      ;;
  esac
done

wsl_pi_set_env_profile "$ENV_PROFILE"
wsl_pi_require_docker
wsl_pi_require_stack_dir

umask 077
mkdir -p "$BACKUP_DIR"

timestamp="$(date -u +'%Y%m%dT%H%M%SZ')"
prefix="kor35_${WSL_PI_ENV_PROFILE}_${timestamp}"
tmp_file="$BACKUP_DIR/${prefix}.dump.tmp"
dump_file="$BACKUP_DIR/${prefix}.dump"
sha_file="$BACKUP_DIR/${prefix}.dump.sha256"

echo "Eseguo dump DB (profilo: $WSL_PI_ENV_PROFILE) in: $dump_file"

# Usiamo variabili del container db (POSTGRES_USER/DB) ed esportiamo in formato custom.
# --no-owner/--no-acl per ripristini più portabili.
wsl_pi_compose exec -T db sh -lc '
  set -euo pipefail
  pg_dump -U "$POSTGRES_USER" --format=custom --no-owner --no-acl "$POSTGRES_DB"
' >"$tmp_file"

mv "$tmp_file" "$dump_file"
sha256sum "$dump_file" >"$sha_file"

echo "OK: $(basename "$dump_file")"

echo "Rotazione: mantengo ultimi $RETENTION_DAYS giorni in $BACKUP_DIR"
find "$BACKUP_DIR" -type f -name "kor35_${WSL_PI_ENV_PROFILE}_*.dump" -mtime "+$RETENTION_DAYS" -print -delete || true
find "$BACKUP_DIR" -type f -name "kor35_${WSL_PI_ENV_PROFILE}_*.dump.sha256" -mtime "+$RETENTION_DAYS" -print -delete || true

