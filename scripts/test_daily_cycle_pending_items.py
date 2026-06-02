"""
test_daily_cycle_pending_items.py
Tests: pending_daily_items intent routes correctly and returns PENDING DAILY ITEMS header.
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

DUMP_MARKERS = ["artifact_inventory", "handoff dump", "Executive Memory", "═══", "HERMES REPORT"]


def check(label: str, cond: bool):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else:    FAIL += 1; print(f"  FAIL  {label}")


def no_dump(text: str) -> bool:
    return not any(m in text for m in DUMP_MARKERS)


print("=== test_daily_cycle_pending_items ===\n")

from hermes_command_router.intake import classify_intent
from hermes_command_router.router import run_command, _PLAIN_INTENTS
from lib.hermes_daily_cycle_state import save_daily_cycle_state, list_pending_cycle_items

save_daily_cycle_state({
    "date": "2026-06-02",
    "top_priority": "Finalize lead magnet",
    "blockers": [
        {"blocker": "CTA not drafted", "category": "operational", "fix": "Draft CTA section"},
    ],
    "approval_items": [
        {"item": "Approve newsletter", "category": "action_queue",
         "why": "Ready to send", "next_if_approved": "Send", "risk_if_skipped": "Delayed"},
    ],
    "memory_v2_count": 5, "goals_count": 2, "action_count": 3,
})

# ── intent in _PLAIN_INTENTS ──────────────────────────────────────────────────
print("-- pending_daily_items in _PLAIN_INTENTS --")
check("pending_daily_items in _PLAIN_INTENTS", "pending_daily_items" in _PLAIN_INTENTS)

# ── phrase classification ─────────────────────────────────────────────────────
print("\n-- phrase classification --")
PHRASES = [
    "show pending items",
    "what is pending",
    "pending cycle items",
    "what needs doing",
    "pending daily items",
    "show pending daily items",
    "what still needs to be done",
]
for phrase in PHRASES:
    intent, _, _ = classify_intent(phrase)
    check(f"classify_intent({repr(phrase[:50])}) == pending_daily_items",
          intent == "pending_daily_items")

# ── list_pending_cycle_items returns expected items ───────────────────────────
print("\n-- list_pending_cycle_items --")
pending = list_pending_cycle_items()
check("pending list is a list", isinstance(pending, list))
check("at least 2 pending items (1 blocker + 1 approval)", len(pending) >= 2)
types = {p["type"] for p in pending}
check("contains 'approval' type", "approval" in types)
check("contains 'blocker' type", "blocker" in types)

# ── response structure ────────────────────────────────────────────────────────
print("\n-- run_command response structure --")
resp = run_command("show pending items", source="cli")
check("non-empty", bool(resp))
check("starts with PENDING DAILY ITEMS", resp.startswith("PENDING DAILY ITEMS"))
check("no dump markers", no_dump(resp))
check("no HERMES REPORT", not resp.strip().startswith("HERMES REPORT"))
check("no ═══", "═══" not in resp)
check("contains approval or blocker info", "approval" in resp.lower() or "block" in resp.lower())
check("no old executive memory", "old executive memory" not in resp.lower())

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
