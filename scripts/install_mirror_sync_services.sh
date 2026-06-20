#!/usr/bin/env bash
set -euo pipefail

# Installa e attiva i servizi systemd di sync mirror (DB + media).
#
# Uso:
#   ./scripts/install_mirror_sync_services.sh
#   ./scripts/install_mirror_sync_services.sh --repo-path /home/pi/kor35-replica --user pi --group pi
#   ./scripts/install_mirror_sync_services.sh --db-interval 1m --media-calendar "*-*-* 23:00:00"
#   ./scripts/install_mirror_sync_services.sh --backup-calendar "*-*-* 05:00:00" --backup-retention-days 15
#   ./scripts/install_mirror_sync_services.sh --no-enable

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

REPO_PATH="/home/pi/kor35-replica"
RUN_USER="pi"
RUN_GROUP="pi"
DB_INTERVAL="2m"
MEDIA_CALENDAR="*-*-* 22:30:00"
BACKUP_CALENDAR="*-*-* 05:00:00"
BACKUP_RETENTION_DAYS="15"
BACKUP_DIR="/home/pi/backups/kor35/db"
ENABLE_NOW="1"

while [ $# -gt 0 ]; do
  case "$1" in
    --repo-path)
      REPO_PATH="${2:-}"
      shift 2
      ;;
    --user)
      RUN_USER="${2:-}"
      shift 2
      ;;
    --group)
      RUN_GROUP="${2:-}"
      shift 2
      ;;
    --db-interval)
      DB_INTERVAL="${2:-}"
      shift 2
      ;;
    --media-calendar)
      MEDIA_CALENDAR="${2:-}"
      shift 2
      ;;
    --backup-calendar)
      BACKUP_CALENDAR="${2:-}"
      shift 2
      ;;
    --backup-retention-days)
      BACKUP_RETENTION_DAYS="${2:-}"
      shift 2
      ;;
    --backup-dir)
      BACKUP_DIR="${2:-}"
      shift 2
      ;;
    --no-enable)
      ENABLE_NOW="0"
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

if [ ! -d "$REPO_PATH" ]; then
  echo "Repo path non trovato: $REPO_PATH" >&2
  exit 1
fi

SYSTEMD_DIR="/etc/systemd/system"
UNITS=(
  "kor35-mirror-stack.service"
  "kor35-mirror-db-sync.service"
  "kor35-mirror-db-sync.timer"
  "kor35-mirror-resync.service"
  "kor35-mirror-media-sync.service"
  "kor35-mirror-media-sync.timer"
  "kor35-mirror-db-backup.service"
  "kor35-mirror-db-backup.timer"
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

# Parametrizzazione locale (path repo, utente/gruppo, scheduling).
sed -i "s|/home/pi/kor35-replica|$REPO_PATH|g" "$SYSTEMD_DIR"/kor35-mirror-*.service
sed -i "s|^User=.*$|User=$RUN_USER|g" "$SYSTEMD_DIR"/kor35-mirror-*.service
sed -i "s|^Group=.*$|Group=$RUN_GROUP|g" "$SYSTEMD_DIR"/kor35-mirror-*.service
sed -i "s|^OnUnitActiveSec=.*$|OnUnitActiveSec=$DB_INTERVAL|g" "$SYSTEMD_DIR/kor35-mirror-db-sync.timer"
sed -i "s|^OnCalendar=.*$|OnCalendar=$MEDIA_CALENDAR|g" "$SYSTEMD_DIR/kor35-mirror-media-sync.timer"
sed -i "s|^OnCalendar=.*$|OnCalendar=$BACKUP_CALENDAR|g" "$SYSTEMD_DIR/kor35-mirror-db-backup.timer"
sed -i "s|^Environment=KOR35_DB_BACKUP_DIR=.*$|Environment=KOR35_DB_BACKUP_DIR=$BACKUP_DIR|g" "$SYSTEMD_DIR/kor35-mirror-db-backup.service"
sed -i "s|^Environment=KOR35_DB_BACKUP_RETENTION_DAYS=.*$|Environment=KOR35_DB_BACKUP_RETENTION_DAYS=$BACKUP_RETENTION_DAYS|g" "$SYSTEMD_DIR/kor35-mirror-db-backup.service"
sed -i "s|^Environment=KOR35_DB_BACKUP_MONTHLY_ARCHIVE_DIR=.*$|Environment=KOR35_DB_BACKUP_MONTHLY_ARCHIVE_DIR=$BACKUP_DIR/monthly|g" "$SYSTEMD_DIR/kor35-mirror-db-backup.service"

systemctl daemon-reload

if [ "$ENABLE_NOW" = "1" ]; then
  systemctl enable --now kor35-mirror-stack.service
  systemctl enable --now kor35-mirror-db-sync.timer
  systemctl enable --now kor35-mirror-media-sync.timer
  systemctl enable --now kor35-mirror-db-backup.timer
fi

echo "Installazione completata."
echo "Repo path: $REPO_PATH"
echo "User/Group: $RUN_USER:$RUN_GROUP"
echo "DB interval: $DB_INTERVAL"
echo "Media calendar: $MEDIA_CALENDAR"
echo "Backup calendar: $BACKUP_CALENDAR"
echo "Backup dir: $BACKUP_DIR"
echo "Backup retention days: $BACKUP_RETENTION_DAYS"
echo ""
echo "Verifica:"
echo "  systemctl status kor35-mirror-stack.service --no-pager"
echo "  systemctl status kor35-mirror-db-sync.timer --no-pager"
echo "  systemctl status kor35-mirror-media-sync.timer --no-pager"
echo "  systemctl status kor35-mirror-db-backup.timer --no-pager"
echo "  systemctl list-timers | grep -E 'kor35-mirror-(db-sync|media-sync|db-backup)'"
