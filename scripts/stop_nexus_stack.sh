#!/usr/bin/env bash
# =============================================================================
# Nexus AI Stack — Stop Script
# =============================================================================
set -uo pipefail

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

log "=== Stopping Nexus stack ==="

stop_proc() {
    local label="$1"
    local pattern="$2"
    if pgrep -f "$pattern" >/dev/null 2>&1; then
        pkill -f "$pattern" 2>/dev/null && log "  ✓ stopped $label" || log "  ✗ failed to stop $label"
        sleep 1
    else
        log "  — $label not running"
    fi
}

stop_proc "Hermes gateway" "hermes gateway"
stop_proc "Telegram bot"     "telegram_bot.py"
stop_proc "Dashboard"        "dashboard.py"
stop_proc "Signal review"    "signal_poller.py"

log ""
log "=== Stack stopped ==="
log "Remaining Nexus processes:"
pgrep -a -f "hermes|telegram_bot|dashboard|signal_poller" 2>/dev/null || log "  (none)"
