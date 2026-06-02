"""
test_unknown_answer_policy_routing.py
Verifies "what if you don't know" phrases return IF I DON'T KNOW policy, not quality fallback.
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


print("=== test_unknown_answer_policy_routing ===\n")

from hermes_command_router.intake import classify_intent
from hermes_command_router.router import run_command

print("-- Intent classification --")
for phrase in ["what if you don't know", "what if you dont know",
               "what if you dont have the answer",
               "what if you cannot answer", "how do you handle unknowns",
               "what happens if you dont know"]:
    intent, _, _ = classify_intent(phrase)
    check(f"classify_intent({phrase!r}) == unknown_handling",
          intent == "unknown_handling")

print("\n-- 'what if you dont have the answer' response --")
resp = run_command("what if you dont have the answer", source="cli")
print(f"  output: {resp[:200]!r}")
check("response non-empty", bool(resp))
check("contains IF I DON'T KNOW", "IF I DON'T KNOW" in resp or "IF I DON" in resp)
check("says should not guess", "should not guess" in resp or "not guess" in resp)
check("mentions checking artifacts / memory", "artifact" in resp.lower() or "memory" in resp.lower())
check("mentions logging the gap", "gap" in resp.lower() or "log" in resp.lower())
check("no HERMES REPORT wrapper", "HERMES REPORT" not in resp)
check("no evidence dump", no_dump(resp))
check("no Quality escalation fallback", "Quality escalation fallback" not in resp)

print("\n-- 'how do you handle unknowns' response --")
resp2 = run_command("how do you handle unknowns", source="cli")
check("response non-empty", bool(resp2))
check("no HERMES REPORT", "HERMES REPORT" not in resp2)
check("no evidence dump", no_dump(resp2))

print("\n-- 'what if you dont know' response --")
resp3 = run_command("what if you dont know", source="cli")
check("response non-empty", bool(resp3))
check("no evidence dump", no_dump(resp3))

print("\n-- No stale Executive Memory --")
for label, r in [("dont have answer", resp), ("handle unknowns", resp2), ("dont know", resp3)]:
    check(f"{label!r}: no stale Executive Memory", "Executive Memory" not in r)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
