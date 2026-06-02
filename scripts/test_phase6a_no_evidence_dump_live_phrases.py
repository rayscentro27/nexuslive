"""
test_phase6a_no_evidence_dump_live_phrases.py
Tests: expanded phrase set (apostrophe-free, hermes-prefixed, money phrases)
produces clean output — no evidence dump, no HERMES REPORT.
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
    "artifact_inventory",
    "handoff dump",
    "Executive Memory",
    "I can answer from verified artifacts",
    "Strategic context from evidence",
    "Quality escalation fallback",
    "═══",
    "HERMES REPORT",
]


def check(label: str, cond: bool):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else:    FAIL += 1; print(f"  FAIL  {label}")


def no_dump(text: str) -> bool:
    return not any(m in text for m in DUMP_MARKERS)


print("=== test_phase6a_no_evidence_dump_live_phrases ===\n")

from hermes_command_router.router import run_command

EXPANDED_PHRASES = [
    # apostrophe-free variants
    "todays nexus plan",
    "todays plan",
    "todays blockers",
    "todays top revenue move",
    "todays top money move",
    # new money phrases
    "what can make money today",
    "how do we make money today",
    # new focus phrases
    "what should i focus on today",
    "what should we focus on today",
    # new approval phrases
    "what needs my approval",
    "pending approvals",
    "approval needed",
    # new continue phrases
    "continue while i am gone",
    "work while i am out",
    # blockers
    "blockers today",
]

print("-- expanded phrases: no evidence dump --")
for phrase in EXPANDED_PHRASES:
    resp = run_command(phrase, source="cli")
    check(f"'{phrase[:50]}': non-empty",    bool(resp))
    check(f"'{phrase[:50]}': no dump",      no_dump(resp))
    check(f"'{phrase[:50]}': no ═══",       "═══" not in resp)
    check(f"'{phrase[:50]}': no HERMES REPORT", not resp.strip().startswith("HERMES REPORT"))

print("\n-- expanded phrases: correct output headers --")
HEADER_MAP = [
    ("todays nexus plan",          "TODAY'S NEXUS PLAN"),
    ("what can make money today",  "TODAY'S TOP MONEY MOVE"),
    ("what needs my approval",     "APPROVAL NEEDED"),
    ("pending approvals",          "APPROVAL NEEDED"),
    ("blockers today",             "TODAY'S BLOCKERS"),
    ("todays blockers",            "TODAY'S BLOCKERS"),
    ("continue while i am gone",   "CONTINUE WHILE YOU ARE OUT"),
]
for phrase, header in HEADER_MAP:
    resp = run_command(phrase, source="cli")
    check(f"'{phrase[:45]}': starts with '{header}'", resp.startswith(header))

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
