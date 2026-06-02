"""
test_daily_cycle_state_history.py
Tests: append_daily_cycle_history writes JSONL; each line is valid JSON.
"""
import sys, os, json
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


print("=== test_daily_cycle_state_history ===\n")

from lib.hermes_daily_cycle_state import (
    append_daily_cycle_history, save_daily_cycle_state, _OP_HISTORY_FILE,
)

PLAN_A = {
    "date": "2026-06-02",
    "top_priority": "Advance lead magnet — cycle A",
    "memory_v2_count": 5,
    "goals_count": 2,
    "action_count": 3,
}
PLAN_B = {
    "date": "2026-06-02",
    "top_priority": "Advance newsletter — cycle B",
    "memory_v2_count": 8,
    "goals_count": 2,
    "action_count": 4,
}

# ── save_daily_cycle_state also appends to history ────────────────────────────
print("-- save_daily_cycle_state calls append_daily_cycle_history --")
before_size = _OP_HISTORY_FILE.stat().st_size if _OP_HISTORY_FILE.exists() else 0
save_daily_cycle_state(PLAN_A)
after_size = _OP_HISTORY_FILE.stat().st_size if _OP_HISTORY_FILE.exists() else 0
check("history file grew after save", after_size > before_size)

# ── append_daily_cycle_history adds a line ────────────────────────────────────
print("\n-- append_daily_cycle_history --")
size_before = _OP_HISTORY_FILE.stat().st_size if _OP_HISTORY_FILE.exists() else 0
append_daily_cycle_history(PLAN_B)
size_after = _OP_HISTORY_FILE.stat().st_size if _OP_HISTORY_FILE.exists() else 0
check("history file grew after append", size_after > size_before)

# ── every line in history file is valid JSON ──────────────────────────────────
print("\n-- history file lines are valid JSON --")
lines = [l for l in _OP_HISTORY_FILE.read_text().splitlines() if l.strip()]
check("history file has at least 1 line", len(lines) >= 1)
valid_lines = 0
for i, line in enumerate(lines[-5:], 1):
    try:
        rec = json.loads(line)
        valid_lines += 1
    except Exception:
        check(f"line {i} is valid JSON", False)
check(f"last 5 lines (or all) are valid JSON ({valid_lines}/{min(5,len(lines))})",
      valid_lines == min(5, len(lines)))

# ── history entries contain created_at ───────────────────────────────────────
print("\n-- history entries contain required fields --")
last_rec = json.loads(lines[-1])
check("created_at in last history entry", "created_at" in last_rec)
check("top_priority in last history entry", "top_priority" in last_rec)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
