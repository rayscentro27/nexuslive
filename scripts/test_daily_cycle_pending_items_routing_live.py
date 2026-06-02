"""
test_daily_cycle_pending_items_routing_live.py
Tests: "what is still pending from today?" and related phrases route to
pending_daily_items — never to evidence dump, next_best_move, or generic fallback.
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
]


def check(label: str, cond: bool):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else:    FAIL += 1; print(f"  FAIL  {label}")


def no_dump(text: str) -> bool:
    return not any(m in text for m in DUMP_MARKERS)


print("=== test_daily_cycle_pending_items_routing_live ===\n")

from hermes_command_router.intake import classify_intent
from hermes_command_router.router import run_command
from lib.hermes_daily_cycle_state import save_daily_cycle_state

save_daily_cycle_state({
    "date": "2026-06-02",
    "top_priority": "Finalize lead magnet",
    "blockers": [{"blocker": "Open knowledge gaps: external_info_question",
                  "category": "knowledge", "fix": "Send sources via Telegram"}],
    "approval_items": [],
    "safe_next_actions": [
        "Review and score latest source intake records",
        "Update internal action queue with current status",
        "Research top content asset improvement opportunities",
        "Log any new knowledge gaps found during review",
    ],
    "memory_v2_count": 5, "goals_count": 2, "action_count": 3,
})

# ── phrase classification ─────────────────────────────────────────────────────
print("-- phrase classification → pending_daily_items --")
PHRASES = [
    "what is still pending from today",
    "what's still pending from today",
    "whats still pending from today",
    "what is pending from today",
    "show pending daily items",
    "show pending items",
    "what is left from today",
    "what still needs to be done today",
    "what is unfinished from today",
    "what is still open today",
    "pending daily items",
    "what is still pending",
]
for phrase in PHRASES:
    intent, _, _ = classify_intent(phrase)
    check(f"classify_intent({repr(phrase[:55])}) == pending_daily_items",
          intent == "pending_daily_items")

# ── response header and no dump ───────────────────────────────────────────────
print("\n-- run_command response format --")
for phrase in ["what is still pending from today", "show pending items"]:
    resp = run_command(phrase, source="cli")
    check(f"'{phrase[:50]}' → starts with PENDING DAILY ITEMS",
          resp.startswith("PENDING DAILY ITEMS"))
    check(f"'{phrase[:50]}' → no dump markers", no_dump(resp))
    check(f"'{phrase[:50]}' → no HERMES REPORT", not resp.strip().startswith("HERMES REPORT"))
    check(f"'{phrase[:50]}' → no ═══", "═══" not in resp)

# ── never routes to evidence dump intents ────────────────────────────────────
print("\n-- phrases do not route to evidence dump intents --")
EVIDENCE_DUMP_INTENTS = {"next_best_move", "nexus_status", "handoff_check", "unknown"}
for phrase in ["what is still pending from today", "what is still pending"]:
    intent, _, _ = classify_intent(phrase)
    check(f"'{phrase[:50]}' NOT in evidence dump intents",
          intent not in EVIDENCE_DUMP_INTENTS)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
