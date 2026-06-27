#!/usr/bin/env bash
# Elicius PdM — Production Deployment Script
# Usage: ./scripts/deploy.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_FILE="$PROJECT_DIR/deploy.log"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"; }

log "=== Starting deployment ==="
cd "$PROJECT_DIR"

# Pre-flight checks
if ! command -v docker &>/dev/null; then
    log "ERROR: Docker is not installed"
    exit 1
fi
if ! command -v docker-compose &>/dev/null && ! docker compose version &>/dev/null 2>&1; then
    log "ERROR: Docker Compose is not installed"
    exit 1
fi
if [ ! -f .env ]; then
    log "ERROR: .env file not found. Copy .env.example and configure it."
    exit 1
fi

# Determine docker compose command
DOCKER_COMPOSE="docker compose"
if ! docker compose version &>/dev/null 2>&1; then
    DOCKER_COMPOSE="docker-compose"
fi

# Pull latest code (if git repo)
if [ -d .git ]; then
    log "Pulling latest code..."
    git pull --ff-only || { log "WARNING: git pull failed, continuing with current code"; }
fi

# Backup database before deployment
if [ -f backend/data/sensor_data.db ]; then
    log "Backing up database..."
    bash scripts/backup.sh || log "WARNING: Backup failed, continuing..."
fi

# Build and deploy
log "Building containers..."
$DOCKER_COMPOSE build --no-cache 2>&1 | tee -a "$LOG_FILE"

log "Starting services..."
$DOCKER_COMPOSE up -d 2>&1 | tee -a "$LOG_FILE"

# Wait for health checks
log "Waiting for services to become healthy..."
MAX_WAIT=120
ELAPSED=0
while [ $ELAPSED -lt $MAX_WAIT ]; do
    HEALTHY=$($DOCKER_COMPOSE ps --format json 2>/dev/null | grep -c '"healthy"' || echo 0)
    TOTAL=$($DOCKER_COMPOSE ps --format json 2>/dev/null | wc -l | tr -d ' ')
    log "Health status: $HEALTHY/$TOTAL services healthy (${ELAPSED}s elapsed)"
    if [ "$HEALTHY" -ge 2 ]; then
        break
    fi
    sleep 10
    ELAPSED=$((ELAPSED + 10))
done

# Verify
if curl -sf http://localhost/api/health > /dev/null 2>&1; then
    log "✅ Deployment successful! Backend health check passed."
else
    log "⚠️  Backend health check failed. Check logs with: $DOCKER_COMPOSE logs backend"
fi

log "Container status:"
$DOCKER_COMPOSE ps 2>&1 | tee -a "$LOG_FILE"
log "=== Deployment complete ==="
