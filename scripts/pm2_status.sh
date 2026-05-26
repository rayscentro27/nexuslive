#!/usr/bin/env bash
# =============================================================================
# Nexus AI Stack — PM2 Status
# Shows PM2 process status, memory usage, and recent log tails
# =============================================================================

export PATH="$HOME/.nvm/versions/node/v22.22.3/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
NEXUS_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOG_DIR="$NEXUS_ROOT/logs"

sep() { echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; }

echo ""
echo "Nexus PM2 Status — $(date)"
sep

echo ""
echo "PM2 PROCESS LIST"
pm2 list 2>/dev/null || echo "  PM2 daemon not running — start with: scripts/pm2_start.sh"

sep
echo ""
echo "MEMORY USAGE"
pm2 info nexus-telegram 2>/dev/null | grep -E "memory|status|restart" | sed 's/^/  /' || echo "  nexus-telegram: not running"
pm2 info nexus-watchers 2>/dev/null | grep -E "memory|status|restart" | sed 's/^/  /' || echo "  nexus-watchers: not running"
pm2 info nexus-executor 2>/dev/null | grep -E "memory|status|restart" | sed 's/^/  /' || echo "  nexus-executor: not running"

sep
echo ""
echo "LAUNCHD SERVICES (Hermes gateway)"
launchctl list 2>/dev/null | grep -E "hermes|nexus" | awk '{printf "  %-40s pid=%-8s exit=%s\n", $3, $1, $2}' || echo "  (none registered)"

sep
echo ""
echo "PORTS"
for port in 8642 18789 3000; do
    result=$(lsof -nP -iTCP:"$port" -sTCP:LISTEN 2>/dev/null | grep -v "^COMMAND" || true)
    if [[ -n "$result" ]]; then
        echo "  :$port → $(echo "$result" | awk '{print $1" PID="$2}' | head -1)"
    else
        echo "  :$port → nothing listening"
    fi
done

sep
echo ""
echo "RECENT LOGS (last 10 lines)"
for log_file in pm2-telegram.err.log pm2-watchers.err.log pm2-executor.err.log; do
    path="$LOG_DIR/$log_file"
    echo ""
    echo "  $log_file:"
    if [[ -f "$path" ]]; then
        tail -10 "$path" | sed 's/^/    /' | grep -v "^    $" || echo "    (empty)"
    else
        echo "    (not created yet)"
    fi
done

sep
echo ""
echo "Commands: pm2 logs | pm2 monit | scripts/pm2_restart.sh"
