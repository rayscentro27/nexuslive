"""
test_revenue_asset_packet_no_evidence_dump.py
Tests: no Phase 6D command ever produces an evidence dump, HERMES REPORT wrapper,
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


print("=== test_revenue_asset_packet_no_evidence_dump ===\n")

from hermes_command_router.router import run_command

ALL_COMMANDS = [
    ("build revenue asset packet",           "REVENUE ASSET PACKET CREATED"),
    ("create revenue asset packet",          "REVENUE ASSET PACKET CREATED"),
    ("show revenue asset packet",            "NEXUS REVENUE ASSET PACKET"),
    ("show latest revenue packet",           "NEXUS REVENUE ASSET PACKET"),
    ("show launch-ready assets",             "LAUNCH-READY ASSETS"),
    ("show content awaiting approval",       "CONTENT AWAITING APPROVAL"),
    ("show cta options",                     "CTA OPTIONS"),
    ("show launch checklist",                "LAUNCH CHECKLIST"),
    ("show approval checklist",              "APPROVAL CHECKLIST"),
    ("generate approval candidates",         "APPROVAL CANDIDATES GENERATED"),
    ("create approval items from packet",    "APPROVAL CANDIDATES GENERATED"),
]

print("-- all Phase 6D commands: no dump, correct header --")
for phrase, expected_header in ALL_COMMANDS:
    resp = run_command(phrase, source="cli")
    check(f"[{phrase[:50]}] starts with '{expected_header}'",
          resp.startswith(expected_header) or expected_header in resp[:80])
    check(f"[{phrase[:50]}] no dump markers", no_dump(resp))
    check(f"[{phrase[:50]}] no HERMES REPORT", not resp.strip().startswith("HERMES REPORT"))
    check(f"[{phrase[:50]}] no ═══", "═══" not in resp)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
