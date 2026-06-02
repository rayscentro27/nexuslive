"""
test_daily_cycle_no_unsafe_actions.py
Tests:
  - HERMES_DAILY_CYCLE_WRITE_ACTIONS=false guard is default
  - save_daily_cycle_state does NOT interact with action queue
  - no Phase 6B commands trigger live trading, publishing, or external sends
"""
import sys, os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

_env_file = ROOT / ".env"
if _env_file.exists():
    for _line in _env_file.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _, _v = _line.partition("=")
            os.environ.setdefault(_k.strip(), _v.strip())

PASS = 0; FAIL = 0


def check(label: str, cond: bool):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else:    FAIL += 1; print(f"  FAIL  {label}")


print("=== test_daily_cycle_no_unsafe_actions ===\n")

import lib.hermes_daily_cycle_state as _state_mod

# ── HERMES_DAILY_CYCLE_WRITE_ACTIONS default ──────────────────────────────────
print("-- HERMES_DAILY_CYCLE_WRITE_ACTIONS default is false --")
check("_WRITE_ACTIONS_ENABLED default is False",
      _state_mod._WRITE_ACTIONS_ENABLED == False or
      os.environ.get("HERMES_DAILY_CYCLE_WRITE_ACTIONS", "false").lower() != "true")

# ── state module does NOT import action-queue writers ─────────────────────────
print("\n-- state module imports are safe --")
import inspect
src = inspect.getsource(_state_mod)
UNSAFE_IMPORTS = [
    "hermes_action_queue_writer",
    "send_email",
    "publish_content",
    "run_live_trade",
    "stripe",
    "paypal",
]
for unsafe in UNSAFE_IMPORTS:
    check(f"'{unsafe}' not imported in state module", unsafe not in src)

# ── save_daily_cycle_state only writes local files ────────────────────────────
print("\n-- save_daily_cycle_state writes local files only --")
check("_OP_STATE_FILE is under docs/reports/operations",
      "docs/reports/operations" in str(_state_mod._OP_STATE_FILE))
check("_OP_HISTORY_FILE is under docs/reports/operations",
      "docs/reports/operations" in str(_state_mod._OP_HISTORY_FILE))
check("_OP_STATE_FILE is a .json file", str(_state_mod._OP_STATE_FILE).endswith(".json"))
check("_OP_HISTORY_FILE is a .jsonl file", str(_state_mod._OP_HISTORY_FILE).endswith(".jsonl"))

# ── router handlers are pure read + format ────────────────────────────────────
print("\n-- router Phase 6B handlers do not call unsafe functions --")
from hermes_command_router import router as _router
import inspect as _inspect
for fn_name in ("_plain_show_last_daily_plan", "_plain_while_out_summary",
                "_plain_pending_daily_items", "_plain_compare_since_last_plan",
                "_plain_mark_daily_item_complete"):
    fn = getattr(_router, fn_name, None)
    if fn is None:
        check(f"{fn_name} exists", False)
        continue
    fn_src = _inspect.getsource(fn)
    # Check for function call patterns (with parenthesis) to avoid false positives
    # from approval boundary policy text that contains words like "publish" or "trade"
    for unsafe in ("send_email(", "publish(", "trade(", "stripe(", "supabase.table("):
        check(f"{fn_name}: no '{unsafe}' call", unsafe not in fn_src)

# ── env var respected when explicitly set ─────────────────────────────────────
print("\n-- HERMES_DAILY_CYCLE_WRITE_ACTIONS env var respected in source --")
check("_WRITE_ACTIONS_ENABLED reads from env",
      "HERMES_DAILY_CYCLE_WRITE_ACTIONS" in src)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
