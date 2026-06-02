"""
test_tomorrow_plan_routing.py
Verifies tomorrow/plan questions return TOMORROW PLAN, not artifact dumps.
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
    "I can answer from verified artifacts", "Strategic context from evidence",
    "Quality escalation fallback", "═══", "HERMES REPORT",
]


def check(label: str, cond: bool):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else:    FAIL += 1; print(f"  FAIL  {label}")


def no_dump(resp: str) -> bool:
    return not any(m in resp for m in DUMP_MARKERS)


print("=== test_tomorrow_plan_routing ===\n")

from hermes_command_router.intake import classify_intent
from hermes_command_router.router import run_command

print("-- Intent classification --")
for phrase in ["what do you have planned for tomorrow", "what are we doing tomorrow",
               "tomorrow plan", "plan for tomorrow",
               "what should we work on tomorrow", "what's planned for tomorrow"]:
    intent, _, _ = classify_intent(phrase)
    check(f"classify_intent({phrase!r}) == tomorrow_plan", intent == "tomorrow_plan")

print("\n-- 'what do you have planned for tomorrow' response --")
resp = run_command("what do you have planned for tomorrow", source="cli")
print(f"  output: {resp[:200]!r}")
check("response non-empty", bool(resp))
check("contains TOMORROW PLAN", "TOMORROW PLAN" in resp)
check("contains numbered recommendations", "1." in resp or "2." in resp)
check("mentions approval policy",
      "approval" in resp.lower() or "without Ray" in resp)
check("no HERMES REPORT wrapper", "HERMES REPORT" not in resp)
check("no evidence dump", no_dump(resp))
check("no artifact_inventory", "artifact_inventory" not in resp)

print("\n-- 'tomorrow plan' response --")
resp2 = run_command("tomorrow plan", source="cli")
check("response non-empty", bool(resp2))
check("contains TOMORROW PLAN", "TOMORROW PLAN" in resp2)
check("no evidence dump", no_dump(resp2))

print("\n-- No stale Executive Memory --")
for label, r in [("tomorrow full", resp), ("tomorrow plan", resp2)]:
    check(f"{label!r}: no stale Executive Memory", "Executive Memory" not in r)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
