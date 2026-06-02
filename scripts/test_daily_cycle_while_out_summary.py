"""
test_daily_cycle_while_out_summary.py
Tests: while_out_summary intent routes correctly and returns WHILE YOU WERE OUT header.
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

DUMP_MARKERS = ["artifact_inventory", "handoff dump", "Executive Memory", "═══", "HERMES REPORT"]


def check(label: str, cond: bool):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else:    FAIL += 1; print(f"  FAIL  {label}")


def no_dump(text: str) -> bool:
    return not any(m in text for m in DUMP_MARKERS)


print("=== test_daily_cycle_while_out_summary ===\n")

from hermes_command_router.intake import classify_intent
from hermes_command_router.router import run_command, _PLAIN_INTENTS
from lib.hermes_daily_cycle_state import save_daily_cycle_state

save_daily_cycle_state({
    "date": "2026-06-02",
    "top_priority": "Finalize lead magnet",
    "safe_next_actions": ["Review source intake", "Score opportunities"],
    "blockers": [{"blocker": "CTA not drafted", "category": "operational", "fix": "Draft CTA"}],
    "approval_items": [],
    "memory_v2_count": 5, "goals_count": 2, "action_count": 3,
})

# ── intent in _PLAIN_INTENTS ──────────────────────────────────────────────────
print("-- while_out_summary in _PLAIN_INTENTS --")
check("while_out_summary in _PLAIN_INTENTS", "while_out_summary" in _PLAIN_INTENTS)

# ── phrase classification ─────────────────────────────────────────────────────
print("\n-- phrase classification --")
PHRASES = [
    "what did you do while i was out",
    "what happened while i was out",
    "while i was out",
    "while i was away",
    "while i was gone",
    "what have you been doing",
    "what did you work on",
]
for phrase in PHRASES:
    intent, _, _ = classify_intent(phrase)
    check(f"classify_intent({repr(phrase[:50])}) == while_out_summary",
          intent == "while_out_summary")

# ── response structure ────────────────────────────────────────────────────────
print("\n-- run_command response structure --")
resp = run_command("while i was out", source="cli")
check("non-empty", bool(resp))
check("starts with WHILE YOU WERE OUT", resp.startswith("WHILE YOU WERE OUT"))
check("no dump markers", no_dump(resp))
check("no HERMES REPORT", not resp.strip().startswith("HERMES REPORT"))
check("no ═══", "═══" not in resp)
check("contains 'last plan'", "last plan" in resp.lower())
check("no old executive memory", "old executive memory" not in resp.lower())
check("contains 'hermes run daily operating cycle' hint",
      "hermes run daily operating cycle" in resp.lower() or "run daily operating cycle" in resp.lower())

# ── no-state fallback ─────────────────────────────────────────────────────────
print("\n-- while_out_summary fallback (no state) --")
from lib.hermes_daily_cycle_state import _OP_STATE_FILE
import shutil
backup = _OP_STATE_FILE.with_suffix(".bak")
if _OP_STATE_FILE.exists():
    shutil.copy(_OP_STATE_FILE, backup)
    _OP_STATE_FILE.unlink()

resp_no_state = run_command("while i was out", source="cli")
check("fallback starts with WHILE YOU WERE OUT", resp_no_state.startswith("WHILE YOU WERE OUT"))
check("fallback mentions 'no saved daily plan'", "no saved daily plan" in resp_no_state.lower())

if backup.exists():
    shutil.copy(backup, _OP_STATE_FILE)
    backup.unlink()

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
