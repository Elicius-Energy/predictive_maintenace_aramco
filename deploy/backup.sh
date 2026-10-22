#!/usr/bin/env bash
# LEDL Motor Energy Monitoring — Automated Database Backup Script
# Supports TimescaleDB/PostgreSQL (via pg_dump) and SQLite fallback.
# Keeps 14 days of encrypted/compressed backups.
# Recommended cron: 0 2 * * * /path/to/deploy/backup.sh >> /var/log/ledl_backup.log 2>&1

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="${PROJECT_DIR}/backups"
RETENTION_DAYS=14
TIMESTAMP=$(date '+%Y%m%d_%H%M%S')

mkdir -p "${BACKUP_DIR}"

echo "=================================================="
echo "Starting LEDL Database Backup at $(date '+%Y-%m-%d %H:%M:%S %Z')"
echo "=================================================="

# Check if Docker compose timescale/postgres container is running
if docker ps --format '{{.Names}}' 2>/dev/null | grep -E "db|timescale|postgres" > /dev/null; then
    CONTAINER_NAME=$(docker ps --format '{{.Names}}' | grep -E "db|timescale|postgres" | head -n 1)
    BACKUP_FILE="${BACKUP_DIR}/ledl_energy_pg_${TIMESTAMP}.sql.gz"
    echo "Found active PostgreSQL/TimescaleDB container: ${CONTAINER_NAME}"
    echo "Dumping database 'ledl_energy'..."
    docker exec -t "${CONTAINER_NAME}" pg_dump -U postgres -d ledl_energy | gzip > "${BACKUP_FILE}"
    echo "PostgreSQL backup successfully written to: ${BACKUP_FILE} ($(du -h "${BACKUP_FILE}" | cut -f1))"
elif [ -f "${PROJECT_DIR}/data/ledl_energy.db" ]; then
    SQLITE_FILE="${PROJECT_DIR}/data/ledl_energy.db"
    BACKUP_FILE="${BACKUP_DIR}/ledl_energy_sqlite_${TIMESTAMP}.db.gz"
    echo "Found local SQLite database: ${SQLITE_FILE}"
    TEMP_FILE="${BACKUP_DIR}/temp_${TIMESTAMP}.db"
    sqlite3 "${SQLITE_FILE}" ".backup '${TEMP_FILE}'"
    gzip -c "${TEMP_FILE}" > "${BACKUP_FILE}"
    rm -f "${TEMP_FILE}"
    echo "SQLite backup successfully written to: ${BACKUP_FILE} ($(du -h "${BACKUP_FILE}" | cut -f1))"
else
    echo "Warning: No running TimescaleDB container or SQLite database found to backup."
    exit 0
fi

# Rotate backups older than 14 days
echo "Rotating backups older than ${RETENTION_DAYS} days..."
find "${BACKUP_DIR}" -name 'ledl_energy_*.gz' -mtime +${RETENTION_DAYS} -delete
REMAINING=$(find "${BACKUP_DIR}" -name 'ledl_energy_*.gz' | wc -l | tr -d ' ')
echo "Backup completed successfully. ${REMAINING} total backup archives retained in ${BACKUP_DIR}."
