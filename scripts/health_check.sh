#!/usr/bin/env bash
# Elicius PdM — Health Check Script
# Usage: ./scripts/health_check.sh
# Cron:  */5 * * * * /path/to/scripts/health_check.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_FILE="$PROJECT_DIR/backend/data/logs/health_check.log"
mkdir -p "$(dirname "$LOG_FILE")"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG_FILE"; }
ALERT=false

# 1. Check backend API
if curl -sf --max-time 10 http://localhost/api/health > /dev/null 2>&1; then
    log "OK: Backend API responding"
else
    log "ALERT: Backend API not responding!"
    ALERT=true
fi

# 2. Check frontend
if curl -sf --max-time 10 http://localhost/ > /dev/null 2>&1; then
    log "OK: Frontend responding"
else
    log "ALERT: Frontend not responding!"
    ALERT=true
fi

# 3. Check disk space (alert if >85% used)
DISK_USAGE=$(df / | tail -1 | awk '{print $5}' | tr -d '%')
if [ "$DISK_USAGE" -gt 85 ]; then
    log "ALERT: Disk usage at ${DISK_USAGE}%!"
    ALERT=true
else
    log "OK: Disk usage at ${DISK_USAGE}%"
fi

# 4. Check memory
MEM_AVAILABLE=$(free -m | awk '/Mem:/ {printf "%.0f", $7/$2*100}')
if [ "$MEM_AVAILABLE" -lt 15 ]; then
    log "ALERT: Only ${MEM_AVAILABLE}% memory available!"
    ALERT=true
else
    log "OK: ${MEM_AVAILABLE}% memory available"
fi

# 5. Check Docker containers
DOCKER_COMPOSE="docker compose"
if ! docker compose version &>/dev/null 2>&1; then
    DOCKER_COMPOSE="docker-compose"
fi

RUNNING=$($DOCKER_COMPOSE -f "$PROJECT_DIR/docker-compose.yml" ps --format '{{.State}}' 2>/dev/null | grep -c 'running' || echo 0)
if [ "$RUNNING" -lt 3 ]; then
    log "ALERT: Only $RUNNING/3 containers running!"
    ALERT=true
else
    log "OK: All $RUNNING containers running"
fi

# 6. Check database file size (alert if >1GB)
DB_PATH="$PROJECT_DIR/backend/data/sensor_data.db"
if [ -f "$DB_PATH" ]; then
    DB_SIZE_MB=$(du -m "$DB_PATH" | cut -f1)
    if [ "$DB_SIZE_MB" -gt 1024 ]; then
        log "ALERT: Database size is ${DB_SIZE_MB}MB (>1GB)!"
        ALERT=true
    else
        log "OK: Database size is ${DB_SIZE_MB}MB"
    fi
fi

if [ "$ALERT" = true ]; then
    log "--- HEALTH CHECK: ISSUES DETECTED ---"
else
    log "--- HEALTH CHECK: ALL OK ---"
fi
