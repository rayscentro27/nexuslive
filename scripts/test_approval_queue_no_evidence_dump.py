"""
test_approval_queue_no_evidence_dump.py
Tests: no Phase 6C approval command ever produces an evidence dump,
       HERMES REPORT wrapper, or ═══ separator.
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


print("=== test_approval_queue_no_evidence_dump ===\n")

from hermes_command_router.router import run_command

ALL_COMMANDS = [
    # show queue
    ("show approval queue",                       "APPROVAL QUEUE"),
    ("what needs my approval",                     "APPROVAL QUEUE"),
    ("pending approvals",                          "APPROVAL QUEUE"),
    ("approval needed",                            "APPROVAL QUEUE"),
    ("what approvals are pending",                 "APPROVAL QUEUE"),
    ("approval queue",                             "APPROVAL QUEUE"),
    # item detail
    ("show approval item 1",                       "APPROVAL ITEM"),
    ("approval item detail 1",                     "APPROVAL ITEM"),
    ("tell me about approval item 1",              "APPROVAL ITEM"),
    # approve
    ("approve item 1",                             "APPROVAL"),
    ("approve this item 1",                        "APPROVAL"),
    # reject
    ("reject item 1",                              "APPROVAL"),
    ("reject this item 1",                         "APPROVAL"),
    # impact
    ("what happens if i approve item 1",           "IF APPROVED"),
    ("what happens if i reject item 1",            "IF REJECTED"),
    ("simulate approval item 1",                   "IF APPROVED"),
    ("simulate rejection item 1",                  "IF REJECTED"),
    # stale cleanup
    ("clear stale approvals",                      "STALE APPROVAL CLEANUP"),
    ("clean up stale approvals",                   "STALE APPROVAL CLEANUP"),
    ("archive old approvals",                      "STALE APPROVAL CLEANUP"),
    # bulk approve
    ("bulk approve",                               "BULK APPROVE"),
    ("approve all safe items",                     "BULK APPROVE"),
]

print("-- all Phase 6C commands: no dump, correct header --")
for phrase, expected_header in ALL_COMMANDS:
    resp = run_command(phrase, source="cli")
    check(f"[{phrase[:50]}] starts with '{expected_header}'",
          resp.startswith(expected_header) or expected_header in resp[:60])
    check(f"[{phrase[:50]}] no dump markers", no_dump(resp))
    check(f"[{phrase[:50]}] no HERMES REPORT", not resp.strip().startswith("HERMES REPORT"))
    check(f"[{phrase[:50]}] no ═══", "═══" not in resp)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
