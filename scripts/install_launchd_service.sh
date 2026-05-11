#!/usr/bin/env bash
# =============================================================================
# Nexus AI — Install / Reload all launchd Services
# =============================================================================
set -uo pipefail

NEXUS_ROOT="/Users/raymonddavis/nexus-ai"
LAUNCH_AGENTS="$HOME/Library/LaunchAgents"
LOG_DIR="$NEXUS_ROOT/hermes/logs"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

log "=== Installing Nexus launchd services ==="

# Ensure directories and permissions
mkdir -p "$LOG_DIR"
chmod +x /Users/raymonddavis/nexus-ai/scripts/*.sh
log "  ✓ directories and permissions ready"

sync_plist() {
    local source="$1"
    local target="$LAUNCH_AGENTS/$(basename "$source")"
    if [[ -f "$source" ]]; then
        cp "$source" "$target"
        chmod 644 "$target"
        log "  ✓ synced $(basename "$source")"
    fi
}

sync_plist "$NEXUS_ROOT/signal_review/launchd/com.nexus.signal-review.plist"
sync_plist "$NEXUS_ROOT/coordination/launchd/com.nexus.coordination-worker.plist"

# Plists to install (in load order)
PLISTS=(
    "com.nexus.coordination-worker"
    "com.nexus.signal-review"
    "com.raymonddavis.nexus.telegram"
    "com.raymonddavis.nexus.dashboard"
    "com.raymonddavis.nexus"
)

install_plist() {
    local label="$1"
    local plist="$LAUNCH_AGENTS/$label.plist"

    if [[ ! -f "$plist" ]]; then
        log "  SKIP $label — plist not found"
        return
    fi

    if ! plutil -lint "$plist" >/dev/null 2>&1; then
        log "  ERROR $label — plist syntax invalid"
        return
    fi

    chmod 644 "$plist"

    # Unload if already loaded
    if launchctl list "$label" >/dev/null 2>&1; then
        launchctl unload "$plist" 2>/dev/null || true
        sleep 1
    fi

    launchctl load "$plist"
    sleep 1
    log "  ✓ $label loaded"
}

for label in "${PLISTS[@]}"; do
    install_plist "$label"
done

sleep 5

# ---------------------------------------------------------------------------
echo ""
log "=== Validation ==="
echo ""
echo "  Nexus services in launchctl:"
launchctl list 2>/dev/null | grep -E "nexus|signal" || echo "    (none found)"
echo ""
echo "  Port 8642 (Hermes):"
lsof -i :8642 2>/dev/null | grep LISTEN || echo "    (not yet — give it 10s)"
echo ""
echo "  Port 3000 (Dashboard):"
lsof -i :3000 2>/dev/null | grep LISTEN || echo "    (not yet — give it 10s)"
echo ""
echo "  Port 8000 (Signal router):"
lsof -i :8000 2>/dev/null | grep LISTEN || echo "    (not yet)"
echo ""
echo "  Signal review process:"
pgrep -af "signal_poller.py" || echo "    (not yet)"
echo ""
log "Done. Run './check_nexus_stack.sh' to verify full status."
