#!/usr/bin/env bash
# LEDL Motor Energy Monitoring — Database Restore Script
# Usage: ./deploy/restore.sh <path_to_backup_file.sql.gz | path_to_backup_file.db.gz>

set -euo pipefail

if [ $# -lt 1 ]; then
    echo "Usage: $0 <path_to_backup_file>"
    echo "Examples:"
    echo "  $0 backups/ledl_energy_pg_20261015_120000.sql.gz"
    echo "  $0 backups/ledl_energy_sqlite_20261015_120000.db.gz"
    exit 1
fi

BACKUP_FILE="$1"

if [ ! -f "${BACKUP_FILE}" ]; then
    echo "Error: Backup file '${BACKUP_FILE}' does not exist."
    exit 1
fi

echo "=================================================="
echo "Starting LEDL Database Restore from: ${BACKUP_FILE}"
echo "=================================================="

# Check file type
if [[ "${BACKUP_FILE}" =~ \.sql\.gz$ ]]; then
    if ! docker ps --format '{{.Names}}' 2>/dev/null | grep -E "db|timescale|postgres" > /dev/null; then
        echo "Error: PostgreSQL/TimescaleDB container is not running."
        exit 1
    fi
    CONTAINER_NAME=$(docker ps --format '{{.Names}}' | grep -E "db|timescale|postgres" | head -n 1)
    echo "Restoring into container: ${CONTAINER_NAME} database 'ledl_energy'..."
    gunzip -c "${BACKUP_FILE}" | docker exec -i "${CONTAINER_NAME}" psql -U postgres -d ledl_energy
    echo "PostgreSQL database restored successfully!"
elif [[ "${BACKUP_FILE}" =~ \.db\.gz$ ]]; then
    TARGET_DB="data/ledl_energy.db"
    echo "Restoring into SQLite database: ${TARGET_DB}..."
    mkdir -p data
    gunzip -c "${BACKUP_FILE}" > "${TARGET_DB}"
    echo "SQLite database restored successfully to ${TARGET_DB}!"
else
    echo "Error: Unrecognized backup format. Expected .sql.gz or .db.gz"
    exit 1
fi

echo "Restore operation completed successfully."
