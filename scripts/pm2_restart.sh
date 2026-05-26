#!/usr/bin/env bash
# =============================================================================
# Nexus AI Stack — PM2 Restart
# Graceful rolling restart of all PM2-managed nexus services
# =============================================================================
set -euo pipefail

export PATH="$HOME/.nvm/versions/node/v22.22.3/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
NEXUS_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$NEXUS_ROOT"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

SERVICE="${1:-all}"  # optional: "nexus-telegram", "nexus-watchers", "nexus-executor"

log "=== Nexus PM2 Restart: $SERVICE ==="

if [[ "$SERVICE" == "all" ]]; then
    pm2 reload ecosystem.config.cjs --update-env
else
    pm2 restart "$SERVICE"
fi

pm2 save
pm2 list
