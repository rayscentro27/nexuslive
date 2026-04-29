#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/raymonddavis/nexus-ai"
LOG_DIR="$ROOT/openclaw/logs"
mkdir -p "$LOG_DIR"

cd "$ROOT"
exec /usr/local/bin/python3 "$ROOT/scripts/run_control_center_wsgi.py"
