#!/usr/bin/env bash
# =============================================================================
# Nexus AI Stack — Status Check Script
# =============================================================================
set -uo pipefail

export HOME="/Users/raymonddavis"
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"

NVM_BIN="$HOME/.nvm/versions/node/v24.14.0/bin"
[[ -d "$NVM_BIN" ]] && export PATH="$NVM_BIN:$PATH"

LOG_DIR="/Users/raymonddavis/nexus-ai/hermes/logs"

sep() { echo ""; echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; }

show_listeners() {
    local port="$1"
    local label="$2"
    local attempts=3
    local delay=1
    local output=""

    for _ in $(seq 1 "$attempts"); do
        output=$(lsof -nP -iTCP:"$port" -sTCP:LISTEN 2>/dev/null | grep -v "^COMMAND" || true)
        if [[ -n "$output" ]]; then
            break
        fi
        sleep "$delay"
    done

    echo "  :$port ($label):"
    if [[ -n "$output" ]]; then
        awk '{printf "    %s PID=%s\n", $1, $2}' <<<"$output"
    else
        echo "    nothing listening"
    fi
    echo ""
}

# ---------------------------------------------------------------------------
echo "🦞 Nexus AI Stack Status — $(date)"
# ---------------------------------------------------------------------------

sep; echo "📦 RUNTIME VERSIONS"
echo "  node:      $(node --version 2>/dev/null || echo 'NOT FOUND')"
echo "  npm:       $(npm --version 2>/dev/null  || echo 'NOT FOUND')"
echo "  hermes:  $(hermes --version 2>/dev/null | head -1 || echo 'NOT FOUND')"
echo "  python3:   $(python3 --version 2>/dev/null || echo 'NOT FOUND')"

sep; echo "🔄 PROCESSES"
check_proc() {
    local label="$1"
    local pattern="$2"
    if pgrep -f "$pattern" >/dev/null 2>&1; then
        local pid
        pid=$(pgrep -f "$pattern" | head -1)
        echo "  ✅ $label (PID $pid)"
    else
        echo "  ❌ $label — NOT RUNNING"
    fi
}
check_proc "Hermes gateway" "hermes"
check_proc "Telegram monitor" "telegram_bot.py --monitor"
check_proc "Legacy Hermes status poller" "hermes_status_bot.py"
check_proc "Dashboard"        "dashboard.py"
check_proc "Signal router"    "tradingview_router.py"
check_proc "Signal review"    "signal_poller.py"

echo ""
echo "  Trading engine: $(pgrep -f 'nexus_trading_engine' >/dev/null 2>&1 && echo '⚠️  RUNNING' || echo '✅ not running (correct)')"

sep; echo "🌐 PORTS"
show_listeners "18789" "Hermes"
show_listeners "3000" "Dashboard"
show_listeners "8000" "Signal router"
show_listeners "5000" "Trading engine"

sep; echo "📋 LAUNCHD SERVICES"
launchctl list 2>/dev/null | grep -E "nexus|hermes|signal" || echo "  (none registered)"

sep; echo "📄 RECENT LOGS (last 20 lines each)"

tail_log() {
    local label="$1"
    local path="$2"
    echo ""
    echo "  — $label ($path):"
    if [[ -f "$path" ]]; then
        tail -20 "$path" | sed 's/^/    /'
    else
        echo "    (file not found)"
    fi
}

tail_log "Gateway"   "$LOG_DIR/gateway.log"
tail_log "Telegram"  "$LOG_DIR/telegram.log"
tail_log "Dashboard" "$LOG_DIR/dashboard.log"
tail_log "Signal Review" "$LOG_DIR/signal-review.log"
tail_log "LaunchD"   "$LOG_DIR/launchd.out.log"

sep
echo ""
echo "Telegram inbound authority: telegram_bot.py --monitor"
echo "Local fallback: python3 scripts/hermes_status.py"
echo ""
echo "Done."
