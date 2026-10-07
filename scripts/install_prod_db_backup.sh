#!/usr/bin/env bash
set -euo pipefail

# Installa e attiva il timer systemd di backup DB su produzione.
#
# Uso (sul server prod, come root o con sudo):
#   sudo ./scripts/install_prod_db_backup.sh
#   sudo ./scripts/install_prod_db_backup.sh --calendar "*-*-* 06:00:00" --keep 10
#   sudo ./scripts/install_prod_db_backup.sh --no-enable
#   sudo ./scripts/install_prod_db_backup.sh --run-now
#
# Da postazione remota (dopo git pull su /srv/kor35):
#   ssh kor35-prod 'cd /srv/kor35 && sudo ./scripts/install_prod_db_backup.sh --run-now'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

REPO_PATH="/srv/kor35"
BACKUP_DIR="/var/backups/kor35/db"
BACKUP_CALENDAR="*-*-* 06:00:00"
BACKUP_KEEP="10"
ENABLE_NOW="1"
RUN_NOW="0"

while [ $# -gt 0 ]; do
  case "$1" in
    --repo-path)
      REPO_PATH="${2:-}"
      shift 2
      ;;
    --backup-dir)
      BACKUP_DIR="${2:-}"
      shift 2
      ;;
    --calendar)
      BACKUP_CALENDAR="${2:-}"
      shift 2
      ;;
    --keep)
      BACKUP_KEEP="${2:-}"
      shift 2
      ;;
    --no-enable)
      ENABLE_NOW="0"
      shift
      ;;
    --run-now)
      RUN_NOW="1"
      shift
      ;;
    -h|--help)
      sed -n '1,20p' "$0"
      exit 0
      ;;
    *)
      echo "Argomento non riconosciuto: $1" >&2
      exit 1
      ;;
  esac
done

if [ "$(id -u)" -ne 0 ]; then
  echo "Esegui come root (sudo $0 ...)" >&2
  exit 1
fi

if [ ! -d "$REPO_PATH" ]; then
  echo "Repo path non trovato: $REPO_PATH" >&2
  exit 1
fi

if [ ! -x "$REPO_PATH/scripts/backup_db_daily.sh" ]; then
  echo "Script backup mancante o non eseguibile: $REPO_PATH/scripts/backup_db_daily.sh" >&2
  exit 1
fi

SYSTEMD_DIR="/etc/systemd/system"
UNITS=(
  "kor35-db-backup.service"
  "kor35-db-backup.timer"
)

for unit in "${UNITS[@]}"; do
  src="$ROOT_DIR/config/systemd/$unit"
  dst="$SYSTEMD_DIR/$unit"
  if [ ! -f "$src" ]; then
    echo "File unit mancante nel repo: $src" >&2
    exit 1
  fi
  cp "$src" "$dst"
done

# Parametrizzazione locale
sed -i "s|/srv/kor35|$REPO_PATH|g" "$SYSTEMD_DIR/kor35-db-backup.service"
sed -i "s|^OnCalendar=.*$|OnCalendar=$BACKUP_CALENDAR|g" "$SYSTEMD_DIR/kor35-db-backup.timer"
sed -i "s|^Environment=KOR35_DB_BACKUP_DIR=.*$|Environment=KOR35_DB_BACKUP_DIR=$BACKUP_DIR|g" "$SYSTEMD_DIR/kor35-db-backup.service"
sed -i "s|^Environment=KOR35_DB_BACKUP_KEEP=.*$|Environment=KOR35_DB_BACKUP_KEEP=$BACKUP_KEEP|g" "$SYSTEMD_DIR/kor35-db-backup.service"
sed -i "s|^Environment=KOR35_DB_BACKUP_MONTHLY_ARCHIVE_DIR=.*$|Environment=KOR35_DB_BACKUP_MONTHLY_ARCHIVE_DIR=$BACKUP_DIR/monthly|g" "$SYSTEMD_DIR/kor35-db-backup.service"

mkdir -p "$BACKUP_DIR" "$BACKUP_DIR/monthly"
chmod 700 "$BACKUP_DIR" "$BACKUP_DIR/monthly"

systemctl daemon-reload

if [ "$ENABLE_NOW" = "1" ]; then
  systemctl enable --now kor35-db-backup.timer
fi

if [ "$RUN_NOW" = "1" ]; then
  echo "Eseguo backup immediato (kor35-db-backup.service)..."
  systemctl start kor35-db-backup.service
fi

echo "Installazione backup DB produzione completata."
echo "Repo path: $REPO_PATH"
echo "Backup dir: $BACKUP_DIR"
echo "Calendar: $BACKUP_CALENDAR"
echo "Keep last: $BACKUP_KEEP"
echo ""
echo "Verifica:"
echo "  systemctl status kor35-db-backup.timer --no-pager"
echo "  systemctl list-timers | grep kor35-db-backup"
echo "  journalctl -u kor35-db-backup.service -n 50 --no-pager"
echo "  ls -lah $BACKUP_DIR"
