"""
test_small_talk_no_evidence_dump.py
Verifies small talk / greeting phrases return clean plain-language responses.
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


print("=== test_small_talk_no_evidence_dump ===\n")

from hermes_command_router.intake import classify_intent
from hermes_command_router.router import run_command

print("-- Intent classification --")
for phrase in ["did you get enough sleep", "how are you", "good morning",
               "are you awake", "are you online", "you good", "did you sleep",
               "good afternoon", "good evening"]:
    intent, _, _ = classify_intent(phrase)
    check(f"classify_intent({phrase!r}) == small_talk", intent == "small_talk")

print("\n-- 'did you get enough sleep' response --")
resp = run_command("did you get enough sleep", source="cli")
print(f"  output: {resp[:120]!r}")
check("response non-empty", bool(resp))
check("says I don't sleep or I'm online", "sleep" in resp.lower() or "online" in resp.lower())
check("no artifact_inventory", "artifact_inventory" not in resp)
check("no handoff dump", "handoff" not in resp.lower() or "handoff_check" not in resp)
check("no HERMES REPORT wrapper", "HERMES REPORT" not in resp)
check("no evidence dump markers", no_dump(resp))
check("offers to help with nexus / memory / goals", any(w in resp.lower() for w in
      ("nexus", "memory", "goals", "recommend", "plan", "content", "gaps")))

print("\n-- 'how are you' response --")
resp2 = run_command("how are you", source="cli")
check("response non-empty", bool(resp2))
check("no HERMES REPORT", "HERMES REPORT" not in resp2)
check("no evidence dump", no_dump(resp2))

print("\n-- 'good morning' response --")
resp3 = run_command("good morning", source="cli")
check("response non-empty", bool(resp3))
check("mentions today", "today" in resp3.lower() or "morning" in resp3.lower())
check("no evidence dump", no_dump(resp3))

print("\n-- 'are you online' response --")
resp4 = run_command("are you online", source="cli")
check("response non-empty", bool(resp4))
check("no evidence dump", no_dump(resp4))

print("\n-- No stale Executive Memory in any response --")
for label, r in [("did you sleep", resp), ("how are you", resp2),
                 ("good morning", resp3), ("are you online", resp4)]:
    check(f"{label!r}: no stale Executive Memory", "Executive Memory" not in r)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
