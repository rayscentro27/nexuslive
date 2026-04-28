#!/bin/bash
# Nexus Worker Health — quick CLI status check
# Usage: bash ~/nexus-ai/scripts/check_worker_health.sh

NEXUS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$NEXUS_DIR/.env"

# Load env
if [ -f "$ENV_FILE" ]; then
  set -a; source "$ENV_FILE"; set +a
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  NEXUS WORKER HEALTH CHECK"
echo "  $(date '+%Y-%m-%d %H:%M:%S')"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ── Process status ────────────────────────────────────────────────────────────
echo ""
echo "▸ PROCESSES"

for label in com.nexus.mac-mini-worker com.nexus.signal-review com.nexus.signal-router ai.hermes.gateway; do
  pid=$(launchctl list "$label" 2>/dev/null | grep '"PID"' | awk -F' = ' '{print $2}' | tr -d '";')
  last_exit=$(launchctl list "$label" 2>/dev/null | grep '"LastExitStatus"' | awk -F' = ' '{print $2}' | tr -d '";')
  if [ -n "$pid" ]; then
    echo "  ✅ $label  (PID $pid)"
  else
    if [ "$last_exit" = "0" ]; then
      echo "  ⚠️  $label  (not running, last exit: $last_exit)"
    else
      echo "  ❌ $label  (not running, last exit: $last_exit)"
    fi
  fi
done

# ── Port checks ───────────────────────────────────────────────────────────────
echo ""
echo "▸ PORTS"
for port in 8642 8000 3000; do
  if lsof -i :$port -sTCP:LISTEN &>/dev/null; then
    proc=$(lsof -i :$port -sTCP:LISTEN 2>/dev/null | awk 'NR==2{print $1}')
    echo "  ✅ :$port  ($proc)"
  else
    echo "  ❌ :$port  (nothing listening)"
  fi
done

# ── Recent log tail ───────────────────────────────────────────────────────────
echo ""
echo "▸ WORKER LOG (last 5 lines)"
tail -5 "$NEXUS_DIR/hermes/logs/mac-mini-worker.log" 2>/dev/null | sed 's/^/  /'

echo ""
echo "▸ SIGNAL REVIEW LOG (last 3 lines)"
tail -3 "$NEXUS_DIR/logs/signal_review.log" 2>/dev/null | sed 's/^/  /'

# ── Supabase queue snapshot ───────────────────────────────────────────────────
if [ -n "$SUPABASE_URL" ] && [ -n "$SUPABASE_KEY" ]; then
  echo ""
  echo "▸ QUEUE SNAPSHOT"
  python3 - <<PYEOF
import urllib.request, json, os

url = os.environ['SUPABASE_URL']
key = os.environ['SUPABASE_KEY']

def sb_get(path):
    req = urllib.request.Request(f"{url}/rest/v1/{path}",
        headers={'apikey': key, 'Authorization': f'Bearer {key}'})
    with urllib.request.urlopen(req, timeout=8) as r:
        return json.loads(r.read())

try:
    # Count by status
    for status in ['pending', 'leased', 'retry_wait', 'failed']:
        rows = sb_get(f"job_queue?status=eq.{status}&select=id")
        print(f"  {status:12s}: {len(rows)}")

    # Stale leases
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    stale = sb_get(f"job_queue?status=eq.leased&lease_expires_at=lt.{now}&select=id,job_type")
    if stale:
        print(f"  ⚠️  stale leases: {len(stale)} job(s) — {[s['job_type'] for s in stale]}")
    else:
        print(f"  stale leases : 0")

    # Heartbeat
    hb = sb_get("worker_heartbeats?worker_type=eq.mac-mini-worker&select=worker_id,status,last_heartbeat_at,in_flight_jobs")
    if hb:
        h = hb[0]
        print(f"\n  Heartbeat: {h['status']} | in-flight: {h['in_flight_jobs']} | last seen: {h['last_heartbeat_at']}")
    else:
        print(f"\n  ⚠️  No heartbeat row found for mac-mini-worker")

except Exception as e:
    print(f"  ⚠️  Supabase check failed: {e}")
PYEOF
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
