"""
test_approval_queue_bulk_approve.py
Tests: bulk_approve_blocked command — safe items approved, high-risk skipped.
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


def check(label: str, cond: bool):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else:    FAIL += 1; print(f"  FAIL  {label}")


print("=== test_approval_queue_bulk_approve ===\n")

from lib.hermes_approval_queue import _load_state, HIGH_RISK_CATEGORIES
from lib.hermes_daily_cycle_state import save_daily_cycle_state
from hermes_command_router.router import run_command
from hermes_command_router.intake import classify_intent


def seed_mixed():
    """Seed daily cycle state with one safe + one high-risk approval item."""
    save_daily_cycle_state({
        "date": "2026-06-02",
        "top_priority": "Test",
        "blockers": [],
        "approval_items": [
            {
                "item": "Review content brief internally",
                "category": "internal_review",
                "why": "Internal review needed.",
                "next_if_approved": "Proceeds to next stage.",
                "risk_if_skipped": "Work stays blocked.",
            },
            {
                "item": "Send newsletter to subscribers",
                "category": "subscriber_email",
                "why": "Newsletter is ready.",
                "next_if_approved": "Newsletter sent.",
                "risk_if_skipped": "Delayed send.",
            },
        ],
        "safe_next_actions": [],
        "memory_v2_count": 0, "goals_count": 0, "action_count": 0,
    })


def seed_high_risk_only():
    """Seed daily cycle state with only high-risk approval items."""
    save_daily_cycle_state({
        "date": "2026-06-02",
        "top_priority": "Test",
        "blockers": [],
        "approval_items": [
            {
                "item": "Deploy to production",
                "category": "production_deploy",
                "why": "Production deploy needed.",
                "next_if_approved": "Deployed.",
                "risk_if_skipped": "Not deployed.",
            },
            {
                "item": "Run live trading",
                "category": "live_trading",
                "why": "Trade needed.",
                "next_if_approved": "Trade runs.",
                "risk_if_skipped": "No trade.",
            },
        ],
        "safe_next_actions": [],
        "memory_v2_count": 0, "goals_count": 0, "action_count": 0,
    })


# ── routing ───────────────────────────────────────────────────────────────────
print("-- classify_intent routes to bulk_approve_blocked --")
check("bulk approve → bulk_approve_blocked",
      classify_intent("bulk approve")[0] == "bulk_approve_blocked")
check("approve all safe items → bulk_approve_blocked",
      classify_intent("approve all safe items")[0] == "bulk_approve_blocked")

# ── mixed safe + high-risk ────────────────────────────────────────────────────
print("\n-- bulk approve with mixed items (safe + high-risk) --")
seed_mixed()
resp = run_command("bulk approve", source="cli")
check("starts with BULK APPROVE", resp.startswith("BULK APPROVE"))
check("mentions approved items",
      "approved" in resp.lower() or "review content brief" in resp.lower())
check("mentions high-risk skipped or individual approval required",
      "skipped" in resp.lower() or "high-risk" in resp.lower()
      or "require individual" in resp.lower() or "individual approval" in resp.lower())
check("mentions safety guarantee",
      "no content published" in resp.lower() or "no emails sent" in resp.lower()
      or "safety" in resp.lower() or "no money" in resp.lower())
check("mentions evidence path", "hermes_approval_queue_state.json" in resp)
check("no ═══", "═══" not in resp)

# ── state after bulk approve ──────────────────────────────────────────────────
print("\n-- state after bulk approve: safe approved, high-risk pending --")
state = _load_state()
items = state.get("items") or []
statuses = {i["title"][:30]: i.get("status") for i in items}

safe_approved = any(
    i.get("status") == "approved" and i.get("category") not in HIGH_RISK_CATEGORIES
    for i in items
)
high_risk_pending = all(
    i.get("status") == "pending"
    for i in items if i.get("category") in HIGH_RISK_CATEGORIES
)
check("safe item(s) approved in state", safe_approved)
check("high-risk item(s) still pending in state", high_risk_pending)

# ── high-risk only: no safe items to bulk-approve ────────────────────────────
print("\n-- only high-risk items present: none bulk-approvable --")
seed_high_risk_only()
resp_risky = run_command("bulk approve", source="cli")
check("starts with BULK APPROVE", resp_risky.startswith("BULK APPROVE"))
check("no safe items eligible or individual approval required",
      "no safe" in resp_risky.lower() or "not eligible" in resp_risky.lower()
      or "individual" in resp_risky.lower() or "require" in resp_risky.lower())
check("mentions high-risk categories or individual approval",
      "high-risk" in resp_risky.lower() or "individual" in resp_risky.lower()
      or "deploy" in resp_risky.lower() or "trading" in resp_risky.lower())

# ── empty queue ───────────────────────────────────────────────────────────────
print("\n-- empty queue: no items to bulk-approve --")
save_daily_cycle_state({
    "date": "2026-06-02", "top_priority": "Test",
    "blockers": [], "approval_items": [], "safe_next_actions": [],
    "memory_v2_count": 0, "goals_count": 0, "action_count": 0,
})
resp_empty = run_command("bulk approve", source="cli")
check("starts with BULK APPROVE", resp_empty.startswith("BULK APPROVE"))
check("no items message",
      "no pending" in resp_empty.lower() or "no approval" in resp_empty.lower()
      or "not found" in resp_empty.lower())

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
