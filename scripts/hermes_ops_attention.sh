#!/usr/bin/env bash
# =============================================================================
# Hermes Ops Attention
# Brief-by-default "what needs attention?" view for Hermes/Telegram.
# Use --full for the older verbose report.
# =============================================================================

set -u

ROOT="/Users/raymonddavis/nexus-ai"
CHECK_SCRIPT="$ROOT/scripts/check_autonomy_stack.sh"
MODE="${1:-brief}"

section() {
  echo
  echo "============================================================"
  echo "$1"
  echo "============================================================"
}

if [[ "$MODE" == "--full" || "$MODE" == "full" ]]; then
  section "Needs Attention — $(date)"

  if [[ -x "$CHECK_SCRIPT" ]]; then
    CHECK_OUTPUT="$("$CHECK_SCRIPT" 2>&1)"
    if printf '%s\n' "$CHECK_OUTPUT" | rg -q 'FAIL'; then
      echo "Autonomy stack warnings:"
      printf '%s\n' "$CHECK_OUTPUT" | rg 'FAIL|state='
    else
      echo "Autonomy stack: no immediate FAIL lines."
      printf '%s\n' "$CHECK_OUTPUT" | rg 'PASS|state='
    fi
  else
    echo "Autonomy stack check unavailable."
  fi

  section "Pending Tasks"
  for agent in hermes codex claude-code; do
    echo
    echo "[$agent]"
    python3 "$ROOT/nexus_coord.py" tasks "$agent" || echo "task lookup failed"
  done

  section "Recent Errors"
  if [[ -f "$ROOT/logs/scheduler.err.log" ]]; then
    RECENT_ERRORS="$(tail -n 80 "$ROOT/logs/scheduler.err.log" | rg 'ERROR|WARN|FAIL|Traceback' || true)"
    if [[ -n "$RECENT_ERRORS" ]]; then
      printf '%s\n' "$RECENT_ERRORS"
    else
      echo "No recent scheduler error lines."
    fi
  else
    echo "missing scheduler.err.log"
  fi

  exit 0
fi

python3 "$ROOT/scripts/autonomy_status.py" --format attention
