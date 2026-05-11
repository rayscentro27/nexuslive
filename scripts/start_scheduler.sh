#!/usr/bin/env bash
# Start the Nexus Operations Scheduler (internal, no launchd)
set -uo pipefail
export HOME="/Users/raymonddavis"
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

NEXUS_DIR="/Users/raymonddavis/nexus-ai"
LOG_DIR="$NEXUS_DIR/logs"
mkdir -p "$LOG_DIR"

echo "[$(date)] Starting Nexus Scheduler..."
cd "$NEXUS_DIR"
exec /usr/local/bin/python3 operations_center/scheduler.py \
  >> "$LOG_DIR/scheduler.log" 2>&1
