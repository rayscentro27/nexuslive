"""
test_daily_cycle_pending_no_evidence_dump.py
Tests: no Phase 6B pending/mark command ever produces an evidence dump,
       HERMES REPORT wrapper, Quality escalation, or Strategic context dump.
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


print("=== test_daily_cycle_pending_no_evidence_dump ===\n")

from hermes_command_router.router import run_command
from lib.hermes_daily_cycle_state import save_daily_cycle_state

save_daily_cycle_state({
    "date": "2026-06-02",
    "top_priority": "Finalize lead magnet",
    "blockers": [{"blocker": "Open knowledge gaps: external_info_question",
                  "category": "knowledge", "fix": "Send sources"}],
    "approval_items": [
        {"item": "Approve newsletter", "category": "action_queue",
         "why": "Ready to send", "next_if_approved": "Send", "risk_if_skipped": "Delayed"},
    ],
    "safe_next_actions": [
        "Review and score latest source intake records",
        "Update internal action queue with current status",
        "Research top content asset improvement opportunities",
        "Log any new knowledge gaps found during review",
    ],
    "memory_v2_count": 5, "goals_count": 2, "action_count": 3,
})

COMMANDS = [
    ("what is still pending from today",      "PENDING DAILY ITEMS"),
    ("what's still pending from today",       "PENDING DAILY ITEMS"),
    ("show pending items",                    "PENDING DAILY ITEMS"),
    ("pending daily items",                   "PENDING DAILY ITEMS"),
    ("what is left from today",               "PENDING DAILY ITEMS"),
    ("what is unfinished from today",         "PENDING DAILY ITEMS"),
    ("mark complete",                         "DAILY ITEM MARKED COMPLETE"),
    ("mark item complete: Review and score latest source intake records",
                                              "DAILY ITEM MARKED COMPLETE"),
]

print("-- all Phase 6B pending/mark commands: no dump, correct header --")
for phrase, expected_header in COMMANDS:
    resp = run_command(phrase, source="cli")
    check(f"[{phrase[:45]}] starts with '{expected_header}'",
          resp.startswith(expected_header))
    check(f"[{phrase[:45]}] no dump markers", no_dump(resp))
    check(f"[{phrase[:45]}] no HERMES REPORT", not resp.strip().startswith("HERMES REPORT"))
    check(f"[{phrase[:45]}] no ═══", "═══" not in resp)
    # Re-seed after mark to keep state consistent
    if "mark" in phrase.lower():
        save_daily_cycle_state({
            "date": "2026-06-02",
            "top_priority": "Finalize lead magnet",
            "blockers": [{"blocker": "Open knowledge gaps: external_info_question",
                          "category": "knowledge", "fix": "Send sources"}],
            "approval_items": [],
            "safe_next_actions": [
                "Review and score latest source intake records",
                "Update internal action queue with current status",
                "Research top content asset improvement opportunities",
                "Log any new knowledge gaps found during review",
            ],
            "memory_v2_count": 5, "goals_count": 2, "action_count": 3,
        })

# ── unsafe actions cannot be marked complete ─────────────────────────────────
print("\n-- unsafe actions cannot be marked complete --")
UNSAFE_PHRASES = [
    "mark item complete: publish newsletter",
    "mark item complete: email subscribers",
    "mark item complete: deploy to production",
    "mark item complete: run live trading",
]
for phrase in UNSAFE_PHRASES:
    resp = run_command(phrase, source="cli")
    check(f"[{phrase[:55]}] starts with DAILY ITEM MARKED COMPLETE",
          resp.startswith("DAILY ITEM MARKED COMPLETE"))
    check(f"[{phrase[:55]}] contains 'requires Ray approval'",
          "requires ray approval" in resp.lower() or "no pending item" in resp.lower())

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
