"""
test_phase6a_live_routing_daily_plan.py
Tests: daily_operating_cycle intent routes correctly through classify_intent + run_command.
Covers all expanded phrase variants including apostrophe-free and hermes-prefixed forms.
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


print("=== test_phase6a_live_routing_daily_plan ===\n")

from hermes_command_router.intake import classify_intent
from hermes_command_router.router import run_command

DAILY_PLAN_PHRASES = [
    "run daily operating cycle",
    "hermes run daily operating cycle",
    "daily operating cycle",
    "run daily cycle",
    "what should i work on today",
    "what should we work on today",
    "what should i focus on today",
    "what should we focus on today",
    "show today's nexus plan",
    "show today's plan",
    "show today nexus plan",
    "nexus plan today",
    "today's nexus plan",
    "todays nexus plan",
    "todays plan",
    "show nexus plan",
    "daily plan",
]

print("-- classify_intent: all daily plan phrases → daily_operating_cycle --")
for phrase in DAILY_PLAN_PHRASES:
    intent, _, _ = classify_intent(phrase)
    check(f"classify_intent({repr(phrase[:50])}) == daily_operating_cycle",
          intent == "daily_operating_cycle")

print("\n-- run_command: daily plan output structure --")
for phrase in DAILY_PLAN_PHRASES[:5]:  # spot-check first 5 for speed
    resp = run_command(phrase, source="cli")
    check(f"'{phrase[:45]}': non-empty", bool(resp))
    check(f"'{phrase[:45]}': starts TODAY'S NEXUS PLAN", resp.startswith("TODAY'S NEXUS PLAN"))
    check(f"'{phrase[:45]}': no HERMES REPORT", not resp.strip().startswith("HERMES REPORT"))
    check(f"'{phrase[:45]}': no ═══", "═══" not in resp)

print("\n-- hermes-prefixed phrases also route to daily_operating_cycle --")
for phrase in ["hermes, run daily operating cycle", "hermes run daily operating cycle"]:
    intent, _, _ = classify_intent(phrase)
    check(f"classify_intent({repr(phrase[:60])}) == daily_operating_cycle",
          intent == "daily_operating_cycle")

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
