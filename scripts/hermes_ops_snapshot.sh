#!/usr/bin/env bash
# =============================================================================
# Hermes Ops Snapshot
# Brief-by-default operator snapshot for Hermes/Telegram.
# Use --full for the older verbose report.
# =============================================================================

set -u

ROOT="/Users/raymonddavis/nexus-ai"
MODE="${1:-brief}"

section() {
  echo
  echo "============================================================"
  echo "$1"
  echo "============================================================"
}

if [[ "$MODE" == "--full" || "$MODE" == "full" ]]; then
  section "Hermes Ops Snapshot — $(date)"

  if [[ -x "$ROOT/scripts/check_autonomy_stack.sh" ]]; then
    "$ROOT/scripts/check_autonomy_stack.sh"
  else
    echo "Missing: scripts/check_autonomy_stack.sh"
  fi

  section "Coordination Summary"
  python3 "$ROOT/nexus_coord.py" summary || echo "coord summary unavailable"

  section "Recent Scheduler"
  if [[ -f "$ROOT/logs/scheduler.err.log" ]]; then
    tail -n 20 "$ROOT/logs/scheduler.err.log"
  else
    echo "missing scheduler.err.log"
  fi

  exit 0
fi

python3 "$ROOT/scripts/autonomy_status.py" --format brief
