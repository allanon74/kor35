#!/usr/bin/env bash
set -euo pipefail

# Dump giornaliero PostgreSQL su file, con rotazione tipo logrotate.
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
#   KOR35_DB_BACKUP_KEEP=10                    # conserva solo gli ultimi N dump (prioritario se > 0)
#   KOR35_DB_BACKUP_RETENTION_DAYS=0           # fallback per età (usato solo se KEEP=0)
#   KOR35_DB_BACKUP_MONTHLY_ARCHIVE_DIR=/var/backups/kor35/db/monthly
#   KOR35_DB_BACKUP_ENABLE_MONTHLY_ARCHIVE=1

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib_wsl_pi_like.sh
source "$SCRIPT_DIR/lib_wsl_pi_like.sh"

ENV_PROFILE="prod"
BACKUP_DIR="${KOR35_DB_BACKUP_DIR:-/var/backups/kor35/db}"
KEEP="${KOR35_DB_BACKUP_KEEP:-10}"
RETENTION_DAYS="${KOR35_DB_BACKUP_RETENTION_DAYS:-0}"
MONTHLY_ARCHIVE_DIR="${KOR35_DB_BACKUP_MONTHLY_ARCHIVE_DIR:-$BACKUP_DIR/monthly}"
ENABLE_MONTHLY_ARCHIVE="${KOR35_DB_BACKUP_ENABLE_MONTHLY_ARCHIVE:-1}"

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

rotate_by_count() {
  local keep_n="$1"
  local pattern="$2"
  local idx=0
  local f

  # Ordine: più recenti prima (mtime). Solo file in BACKUP_DIR (non monthly/).
  while IFS= read -r f; do
    [ -n "$f" ] || continue
    idx=$((idx + 1))
    if [ "$idx" -gt "$keep_n" ]; then
      echo "Rotazione (keep=$keep_n): elimino $(basename "$f")"
      rm -f -- "$f"
    fi
  done < <(find "$BACKUP_DIR" -maxdepth 1 -type f -name "$pattern" -printf '%T@\t%p\n' | sort -nr | cut -f2-)
}

if [ "${KEEP}" -gt 0 ] 2>/dev/null; then
  echo "Rotazione: mantengo ultimi $KEEP dump in $BACKUP_DIR"
  rotate_by_count "$KEEP" "kor35_${WSL_PI_ENV_PROFILE}_*.dump"
  rotate_by_count "$KEEP" "kor35_${WSL_PI_ENV_PROFILE}_*.dump.sha256"
elif [ "${RETENTION_DAYS}" -gt 0 ] 2>/dev/null; then
  echo "Rotazione: mantengo ultimi $RETENTION_DAYS giorni in $BACKUP_DIR"
  find "$BACKUP_DIR" -maxdepth 1 -type f -name "kor35_${WSL_PI_ENV_PROFILE}_*.dump" -mtime "+$RETENTION_DAYS" -print -delete || true
  find "$BACKUP_DIR" -maxdepth 1 -type f -name "kor35_${WSL_PI_ENV_PROFILE}_*.dump.sha256" -mtime "+$RETENTION_DAYS" -print -delete || true
else
  echo "Rotazione: disabilitata (KOR35_DB_BACKUP_KEEP=0 e KOR35_DB_BACKUP_RETENTION_DAYS=0)"
fi

if [ "$ENABLE_MONTHLY_ARCHIVE" = "1" ]; then
  mkdir -p "$MONTHLY_ARCHIVE_DIR"
  month_tag="$(date -u +'%Y%m')"
  monthly_file="$MONTHLY_ARCHIVE_DIR/kor35_${WSL_PI_ENV_PROFILE}_${month_tag}.dump.gz"
  monthly_sha="$MONTHLY_ARCHIVE_DIR/kor35_${WSL_PI_ENV_PROFILE}_${month_tag}.dump.gz.sha256"
  if [ ! -f "$monthly_file" ]; then
    echo "Archivio mensile: creo snapshot persistente $monthly_file"
    gzip -c "$dump_file" >"$monthly_file"
    sha256sum "$monthly_file" >"$monthly_sha"
  else
    echo "Archivio mensile: già presente per $month_tag, skip."
  fi
fi
