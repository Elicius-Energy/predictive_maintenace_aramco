#!/usr/bin/env bash
# Elicius PdM — Database Backup Script
# Usage: ./scripts/backup.sh
# Cron:  0 2 * * * /path/to/scripts/backup.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="$PROJECT_DIR/backups"
DB_PATH="$PROJECT_DIR/backend/data/sensor_data.db"
RETENTION_DAYS=7
TIMESTAMP=$(date '+%Y%m%d_%H%M%S')

mkdir -p "$BACKUP_DIR"

if [ ! -f "$DB_PATH" ]; then
    echo "[$(date)] No database found at $DB_PATH — skipping backup."
    exit 0
fi

# Use SQLite's backup command for consistency (handles WAL properly)
BACKUP_FILE="$BACKUP_DIR/sensor_data_${TIMESTAMP}.db"
sqlite3 "$DB_PATH" ".backup '$BACKUP_FILE'"

# Compress
gzip "$BACKUP_FILE"
echo "[$(date)] Backup created: ${BACKUP_FILE}.gz ($(du -h "${BACKUP_FILE}.gz" | cut -f1))"

# Rotate old backups
find "$BACKUP_DIR" -name 'sensor_data_*.db.gz' -mtime +$RETENTION_DAYS -delete
REMAINING=$(find "$BACKUP_DIR" -name 'sensor_data_*.db.gz' | wc -l | tr -d ' ')
echo "[$(date)] Backup rotation complete. $REMAINING backups retained."
