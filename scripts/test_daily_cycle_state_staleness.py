"""
test_daily_cycle_state_staleness.py
Tests: is_cycle_state_stale returns correct results for fresh/stale/missing state.
"""
import sys, os, json
from datetime import datetime, timezone, timedelta
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


print("=== test_daily_cycle_state_staleness ===\n")

from lib.hermes_daily_cycle_state import (
    is_cycle_state_stale, save_daily_cycle_state, _OP_STATE_FILE
)

SAMPLE = {
    "date": "2026-06-02",
    "top_priority": "Test",
    "memory_v2_count": 1, "goals_count": 1, "action_count": 1,
}

# ── fresh state is not stale ──────────────────────────────────────────────────
print("-- fresh state (just saved) --")
save_daily_cycle_state(SAMPLE)
check("fresh state not stale (24h)", is_cycle_state_stale(max_age_hours=24) == False)
check("fresh state not stale (1h)", is_cycle_state_stale(max_age_hours=1) == False)

# ── missing state is stale ────────────────────────────────────────────────────
print("\n-- missing state is stale --")
import shutil
backup = _OP_STATE_FILE.with_suffix(".bak")
if _OP_STATE_FILE.exists():
    shutil.copy(_OP_STATE_FILE, backup)
    _OP_STATE_FILE.unlink()
check("missing state file → stale", is_cycle_state_stale() == True)
if backup.exists():
    shutil.copy(backup, _OP_STATE_FILE)
    backup.unlink()

# ── old timestamp is stale ────────────────────────────────────────────────────
print("\n-- old timestamp is stale --")
old_ts = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()
state = json.loads(_OP_STATE_FILE.read_text())
state["created_at"] = old_ts
_OP_STATE_FILE.write_text(json.dumps(state, indent=2))
check("25h old state is stale (24h max)", is_cycle_state_stale(max_age_hours=24) == True)
check("25h old state not stale (48h max)", is_cycle_state_stale(max_age_hours=48) == False)

# ── state with missing created_at is stale ───────────────────────────────────
print("\n-- state with missing created_at is stale --")
state_no_ts = {"date": "2026-06-02", "top_priority": "Test"}
_OP_STATE_FILE.write_text(json.dumps(state_no_ts, indent=2))
check("state with no created_at → stale", is_cycle_state_stale() == True)

# Restore fresh state
save_daily_cycle_state(SAMPLE)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
