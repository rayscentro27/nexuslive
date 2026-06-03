"""
test_revenue_packet_improvement_no_evidence_dump.py
Tests: no Phase 6E command produces an evidence dump, HERMES REPORT wrapper,
       or ═══ separator.
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
    "Quality escalation", "═══", "HERMES REPORT",
    "old executive memory", "executive memory snapshot",
]


def check(label: str, cond: bool):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else:    FAIL += 1; print(f"  FAIL  {label}")


def no_dump(text: str) -> bool:
    return not any(m in text for m in DUMP_MARKERS)


print("=== test_revenue_packet_improvement_no_evidence_dump ===\n")

from hermes_command_router.router import run_command

ALL_COMMANDS = [
    ("show revenue packet gaps",        "REVENUE PACKET READINESS GAPS"),
    ("show readiness gaps",             "REVENUE PACKET READINESS GAPS"),
    ("revenue packet gaps",             "REVENUE PACKET READINESS GAPS"),
    ("improve revenue asset packet",    "REVENUE PACKET IMPROVED"),
    ("improve packet score",            "REVENUE PACKET IMPROVED"),
    ("raise packet readiness",          "REVENUE PACKET IMPROVED"),
    ("show improved cta options",       "IMPROVED CTA OPTIONS"),
    ("improved cta options",            "IMPROVED CTA OPTIONS"),
    ("show offer bridge",               "OFFER BRIDGE"),
    ("offer bridge",                    "OFFER BRIDGE"),
    ("funnel model",                    "OFFER BRIDGE"),
    ("show packet improvement plan",    "PACKET IMPROVEMENT PLAN"),
    ("packet improvement plan",         "PACKET IMPROVEMENT PLAN"),
    ("rescore revenue packet",          "REVENUE PACKET RESCORED"),
    ("rescore packet",                  "REVENUE PACKET RESCORED"),
    ("show final review checklist",     "FINAL REVIEW CHECKLIST"),
    ("final review checklist",          "FINAL REVIEW CHECKLIST"),
    ("final checklist",                 "FINAL REVIEW CHECKLIST"),
]

print("-- all Phase 6E commands: no dump, correct header --")
for phrase, expected_header in ALL_COMMANDS:
    resp = run_command(phrase, source="cli")
    check(f"[{phrase[:50]}] starts with '{expected_header}'",
          resp.startswith(expected_header) or expected_header in resp[:80])
    check(f"[{phrase[:50]}] no dump markers", no_dump(resp))
    check(f"[{phrase[:50]}] no HERMES REPORT", not resp.strip().startswith("HERMES REPORT"))
    check(f"[{phrase[:50]}] no ═══", "═══" not in resp)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
