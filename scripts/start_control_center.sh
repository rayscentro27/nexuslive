#!/usr/bin/env bash
# Start the Nexus AI Control Center (port 4000, localhost only)
set -uo pipefail
export HOME="/Users/raymonddavis"
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

NEXUS_DIR="/Users/raymonddavis/nexus-ai"
LOG_DIR="$NEXUS_DIR/logs"
mkdir -p "$LOG_DIR"

echo "[$(date)] Starting Nexus Control Center on :4000..."
cd "$NEXUS_DIR"
exec /usr/local/bin/python3 control_center/control_center_server.py \
  >> "$LOG_DIR/control_center.log" 2>&1
