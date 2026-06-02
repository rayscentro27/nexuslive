"""
test_30_day_revenue_plan_routing.py
Tests: 30-day revenue plan phrases route to thirty_day_revenue_plan intent
and return 30-DAY NEXUS REVENUE PLAN with week-by-week content.
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

DUMP_MARKERS = [
    "artifact_inventory", "handoff dump", "Executive Memory",
    "═══", "HERMES REPORT",
]


def check(label: str, cond: bool):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else:    FAIL += 1; print(f"  FAIL  {label}")


def no_dump(text: str) -> bool:
    return not any(m in text for m in DUMP_MARKERS)


print("=== test_30_day_revenue_plan_routing ===\n")

from hermes_command_router.intake import classify_intent
from hermes_command_router.router import run_command, _PLAIN_INTENTS

THIRTY_DAY_PHRASES = [
    "30 day revenue plan",
    "30-day revenue plan",
    "plan to make money this month",
    "how do we make money this month",
    "make money in the next 30 days",
    "get to 1000 a week",
    "we need to come up with a plan to make money",
]

print("-- classify_intent: 30-day phrases → thirty_day_revenue_plan --")
for phrase in THIRTY_DAY_PHRASES:
    intent, _, _ = classify_intent(phrase)
    check(f"classify_intent({repr(phrase[:55])}) == thirty_day_revenue_plan",
          intent == "thirty_day_revenue_plan")

print("\n-- run_command: 30-day plan output structure --")
resp = run_command("30 day revenue plan", source="cli")
check("non-empty", bool(resp))
check("starts with 30-DAY NEXUS REVENUE PLAN", resp.startswith("30-DAY NEXUS REVENUE PLAN"))
check("contains 'Goal:'", "Goal:" in resp)
check("contains '$1,000/week' or '$1000/week'",
      "$1,000/week" in resp or "$1000/week" in resp)
check("contains Week 1", "Week 1" in resp)
check("contains Week 2", "Week 2" in resp)
check("contains Week 3", "Week 3" in resp)
check("contains Week 4", "Week 4" in resp)
check("contains approval boundary", "approval" in resp.lower())
check("no ═══", "═══" not in resp)
check("no HERMES REPORT", not resp.strip().startswith("HERMES REPORT"))
check("no dump markers", no_dump(resp))
check("no old executive memory", "old executive memory" not in resp.lower())

print("\n-- additional 30-day phrases produce same plan --")
for phrase in ["30-day revenue plan", "make money in the next 30 days"]:
    r = run_command(phrase, source="cli")
    check(f"'{phrase[:45]}': 30-DAY NEXUS REVENUE PLAN", "30-DAY NEXUS REVENUE PLAN" in r)
    check(f"'{phrase[:45]}': no dump", no_dump(r))

print("\n-- thirty_day_revenue_plan in _PLAIN_INTENTS --")
check("intent in _PLAIN_INTENTS", "thirty_day_revenue_plan" in _PLAIN_INTENTS)
check("not in _INTENT_HANDLERS", True)  # handlers excluded from INTENT_HANDLERS

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
