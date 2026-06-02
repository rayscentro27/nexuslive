"""
test_date_time_question_routing.py
Verifies date/time questions return clean date responses, not artifact dumps.
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


print("=== test_date_time_question_routing ===\n")

from hermes_command_router.intake import classify_intent
from hermes_command_router.router import run_command
from datetime import date

TODAY = date.today().strftime("%Y")  # at minimum the year should appear

print("-- Intent classification --")
for phrase in ["what is today's date", "what is todays date", "what day is it",
               "what is the date", "what time is it", "what's the date"]:
    intent, _, _ = classify_intent(phrase)
    check(f"classify_intent({phrase!r}) == date_time_question",
          intent == "date_time_question")

print("\n-- 'what is todays date' response --")
resp = run_command("what is todays date", source="cli")
print(f"  output: {resp[:200]!r}")
check("response non-empty", bool(resp))
check("contains 'Today is'", "Today is" in resp or "today" in resp.lower())
check("contains the year", TODAY in resp)
check("no HERMES REPORT wrapper", "HERMES REPORT" not in resp)
check("no evidence dump", no_dump(resp))
check("no artifact_inventory", "artifact_inventory" not in resp)
check("mentions memory v2 or nexus context", "memory" in resp.lower() or "nexus" in resp.lower())

print("\n-- 'what day is it' response --")
resp2 = run_command("what day is it", source="cli")
check("response non-empty", bool(resp2))
check("contains the year", TODAY in resp2)
check("no evidence dump", no_dump(resp2))

print("\n-- 'what time is it' response --")
resp3 = run_command("what time is it", source="cli")
check("response non-empty", bool(resp3))
check("mentions device clock or system date", "device" in resp3.lower() or "clock" in resp3.lower() or "system" in resp3.lower())
check("no evidence dump", no_dump(resp3))

print("\n-- No stale Executive Memory --")
for label, r in [("todays date", resp), ("what day is it", resp2), ("what time is it", resp3)]:
    check(f"{label!r}: no stale Executive Memory", "Executive Memory" not in r)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
