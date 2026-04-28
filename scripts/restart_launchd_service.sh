#!/usr/bin/env bash
# =============================================================================
# Nexus AI — Restart all launchd Services
# =============================================================================
set -uo pipefail

LAUNCH_AGENTS="$HOME/Library/LaunchAgents"
UID_NUM=$(id -u)

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

log "=== Restarting Nexus services ==="

LABELS=(
    "com.nexus.coordination-worker"
    "com.nexus.signal-review"
    "com.raymonddavis.nexus.telegram"
    "com.raymonddavis.nexus.dashboard"
    "com.raymonddavis.nexus"
)

for label in "${LABELS[@]}"; do
    plist="$LAUNCH_AGENTS/$label.plist"
    [[ ! -f "$plist" ]] && continue

    if launchctl kickstart -k "gui/${UID_NUM}/${label}" 2>/dev/null; then
        log "  ✓ kickstarted $label"
    else
        log "  fallback: unload/load $label"
        launchctl unload "$plist" 2>/dev/null || true
        sleep 1
        launchctl load   "$plist" 2>/dev/null || true
        log "  ✓ reloaded $label"
    fi
done

sleep 5
log "=== Status ==="
launchctl list 2>/dev/null | grep -E "nexus|signal" || echo "  (none found)"
echo ""
echo "  Run './check_nexus_stack.sh' for full status."
