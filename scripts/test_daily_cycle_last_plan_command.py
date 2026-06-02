"""
test_daily_cycle_last_plan_command.py
Tests: show_last_daily_plan intent routes correctly and returns LAST DAILY PLAN header.
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


print("=== test_daily_cycle_last_plan_command ===\n")

from hermes_command_router.intake import classify_intent
from hermes_command_router.router import run_command, _PLAIN_INTENTS
from lib.hermes_daily_cycle_state import save_daily_cycle_state

# Seed a saved plan so the command has data
save_daily_cycle_state({
    "date": "2026-06-02",
    "top_priority": "Finalize lead magnet",
    "top_priority_why": "Highest-value asset",
    "blockers": [{"blocker": "CTA not drafted", "category": "operational", "fix": "Draft CTA"}],
    "approval_items": [
        {"item": "Approve newsletter", "category": "action_queue",
         "why": "Ready to send", "next_if_approved": "Send", "risk_if_skipped": "Delayed"},
    ],
    "evidence": ["goal: Build Nexus revenue engine"],
    "memory_v2_count": 5, "goals_count": 2, "action_count": 3,
})

# ── intent in _PLAIN_INTENTS ──────────────────────────────────────────────────
print("-- show_last_daily_plan in _PLAIN_INTENTS --")
check("show_last_daily_plan in _PLAIN_INTENTS", "show_last_daily_plan" in _PLAIN_INTENTS)

# ── phrase classification ─────────────────────────────────────────────────────
print("\n-- phrase classification --")
PHRASES = [
    "show last daily plan",
    "show last plan",
    "what was the last plan",
    "show previous plan",
    "what was yesterday's plan",
    "last nexus plan",
    "previous daily plan",
    "show the last plan",
]
for phrase in PHRASES:
    intent, _, _ = classify_intent(phrase)
    check(f"classify_intent({repr(phrase[:50])}) == show_last_daily_plan",
          intent == "show_last_daily_plan")

# ── response structure ────────────────────────────────────────────────────────
print("\n-- run_command response structure --")
resp = run_command("show last daily plan", source="cli")
check("non-empty", bool(resp))
check("starts with LAST DAILY PLAN", resp.startswith("LAST DAILY PLAN"))
check("no dump markers", no_dump(resp))
check("no HERMES REPORT", not resp.strip().startswith("HERMES REPORT"))
check("no ═══", "═══" not in resp)
check("contains 'top priority'", "top priority" in resp.lower())
check("no old executive memory", "old executive memory" not in resp.lower())

# ── no-state fallback ─────────────────────────────────────────────────────────
print("\n-- summarize_latest_daily_cycle fallback (no state) --")
from lib.hermes_daily_cycle_state import summarize_latest_daily_cycle, _OP_STATE_FILE
import shutil
backup = _OP_STATE_FILE.with_suffix(".bak")
if _OP_STATE_FILE.exists():
    shutil.copy(_OP_STATE_FILE, backup)
    _OP_STATE_FILE.unlink()

fallback = summarize_latest_daily_cycle()
check("fallback starts with LAST DAILY PLAN", fallback.startswith("LAST DAILY PLAN"))
check("fallback mentions 'no saved daily plan'", "no saved daily plan" in fallback.lower())

if backup.exists():
    shutil.copy(backup, _OP_STATE_FILE)
    backup.unlink()

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
