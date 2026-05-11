#!/usr/bin/env bash
# =============================================================================
# Nexus AI Stack — Bootstrap Script (called by com.raymonddavis.nexus launchd)
#
# This script runs ONCE at boot/login as a one-shot task.
# It does NOT start services itself — each service has its own launchd plist:
#
#   Hermes gateway    →  com.nexus.hermes                   (AI completions)
#   Telegram bot      →  com.raymonddavis.nexus.telegram    (new)
#   Dashboard         →  com.raymonddavis.nexus.dashboard   (new)
#   Signal router     →  com.nexus.signal-router            (pre-existing)
#   Signal review     →  com.nexus.signal-review            (managed here)
#
# This script just ensures the service plists are loaded and logs the status.
# Trading engine is NOT started — DRY_RUN=True, manual only.
# =============================================================================
set -uo pipefail

export HOME="/Users/raymonddavis"
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"

NEXUS_ROOT="/Users/raymonddavis/nexus-ai"
LOG_DIR="$NEXUS_ROOT/logs"
LAUNCH_AGENTS="$HOME/Library/LaunchAgents"

mkdir -p "$LOG_DIR"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

log "=== Nexus bootstrap starting ==="

# ---------------------------------------------------------------------------
# Ensure per-service plists are loaded (idempotent)
# ---------------------------------------------------------------------------
ensure_loaded() {
    local label="$1"
    local plist="$LAUNCH_AGENTS/$label.plist"
    if [[ ! -f "$plist" ]]; then
        log "  SKIP $label — plist not found at $plist"
        return
    fi
    if launchctl list "$label" >/dev/null 2>&1; then
        log "  OK   $label — already loaded"
    else
        log "  LOAD $label"
        launchctl load "$plist" 2>/dev/null && log "       loaded" || log "       load failed"
    fi
}

ensure_loaded "com.nexus.hermes"
ensure_loaded "com.nexus.signal-router"
ensure_loaded "com.nexus.signal-review"
ensure_loaded "com.raymonddavis.nexus.telegram"
ensure_loaded "com.raymonddavis.nexus.dashboard"

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
sleep 3

log "=== Nexus bootstrap complete ==="
log ""
log "Services registered with launchd:"
launchctl list 2>/dev/null | grep -E "hermes|nexus|signal-router" | \
    awk '{printf "['"'"'%s'"'"'] pid=%-8s exit=%s\n", $3, $1, $2}' | \
    while read -r line; do log "  $line"; done

log ""
log "Ports:"
lsof -i :8642  2>/dev/null | grep LISTEN | awk '{print "  8642:  "$1" PID="$2}' | while read -r l; do log "$l"; done || log "  8642:  not yet listening (Hermes)"
lsof -i :3000  2>/dev/null | grep LISTEN | awk '{print "  3000:  "$1" PID="$2}' | while read -r l; do log "$l"; done || log "  3000:  not yet listening"
lsof -i :8000  2>/dev/null | grep LISTEN | awk '{print "  8000:  "$1" PID="$2}' | while read -r l; do log "$l"; done || log "  8000:  not yet listening"

log ""
log "NOTICE: Trading engine NOT started. DRY_RUN=True. Broker execution disabled."
log "        Run manually: python3 $NEXUS_ROOT/trading-engine/nexus_trading_engine.py"
