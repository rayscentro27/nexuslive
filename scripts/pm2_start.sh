#!/usr/bin/env bash
# =============================================================================
# Nexus AI Stack — PM2 Start
# Starts all PM2-managed services: telegram, watchers, executor
# =============================================================================
set -euo pipefail

NEXUS_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export PYTHONPATH="$NEXUS_ROOT"
export PATH="$HOME/.nvm/versions/node/v22.22.3/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"

cd "$NEXUS_ROOT"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

log "=== Nexus PM2 Start ==="
log "Root: $NEXUS_ROOT"

# Load env if not already loaded
if [[ -f "$NEXUS_ROOT/.env" ]]; then
    set -a
    # shellcheck disable=SC1091
    source "$NEXUS_ROOT/.env"
    set +a
    log "Env loaded from .env"
fi

# Start or reload PM2 services
if pm2 list 2>/dev/null | grep -q "nexus-"; then
    log "PM2 services already running — reloading..."
    pm2 reload ecosystem.config.cjs --update-env
else
    log "Starting PM2 services..."
    pm2 start ecosystem.config.cjs --env production
fi

pm2 save
log ""
log "=== PM2 Service Status ==="
pm2 list
log ""
log "Logs: pm2 logs"
log "Monitor: pm2 monit"
log "Stop all: pm2 stop ecosystem.config.cjs"
