"""
test_approval_queue_high_risk_guard.py
Tests: high-risk categories correctly identified; bulk approve skips them;
       approve_approval_item still works on individual high-risk items (Ray decides).
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


print("=== test_approval_queue_high_risk_guard ===\n")

from lib.hermes_approval_queue import (
    HIGH_RISK_CATEGORIES, _infer_category, _infer_risk,
    _save_state, normalize_approval_item, _load_state,
    approve_approval_item,
)
from hermes_command_router.router import run_command

# ── HIGH_RISK_CATEGORIES completeness ────────────────────────────────────────
print("-- HIGH_RISK_CATEGORIES ──")
EXPECTED_HIGH_RISK = {
    "content_publish", "subscriber_email", "client_facing_content",
    "affiliate_signup", "payment_or_stripe", "paid_tool",
    "production_deploy", "live_trading",
}
for cat in EXPECTED_HIGH_RISK:
    check(f"'{cat}' in HIGH_RISK_CATEGORIES", cat in HIGH_RISK_CATEGORIES)
check("internal_review NOT high-risk", "internal_review" not in HIGH_RISK_CATEGORIES)
check("lesson_approval NOT high-risk", "lesson_approval" not in HIGH_RISK_CATEGORIES)
check("asset_review NOT high-risk", "asset_review" not in HIGH_RISK_CATEGORIES)

# ── _infer_category detects high-risk titles ─────────────────────────────────
print("\n-- _infer_category detects high-risk --")
check("'publish post' → content_publish", _infer_category("publish post") == "content_publish")
check("'email subscriber list' → subscriber_email", _infer_category("email subscriber list") == "subscriber_email")
check("'deploy to production' → production_deploy", _infer_category("deploy to production") == "production_deploy")
check("'live trading order' → live_trading", _infer_category("live trading order") == "live_trading")
check("'affiliate signup program' → affiliate_signup", _infer_category("affiliate signup program") == "affiliate_signup")
check("'stripe payment' → payment_or_stripe", _infer_category("stripe payment") == "payment_or_stripe")
check("'review content asset' → asset_review or internal_review",
      _infer_category("review content asset") in ("asset_review", "internal_review"))

# ── bulk approve skips high-risk ──────────────────────────────────────────────
print("\n-- bulk approve skips high-risk items --")
high_risk_items = []
for i, (title, cat) in enumerate([
    ("Send newsletter", "subscriber_email"),
    ("Deploy to production", "production_deploy"),
    ("Run live trading", "live_trading"),
], start=1):
    raw = {
        "_source_type": "daily_cycle", "title": title,
        "summary": "", "category": cat, "source": "daily_cycle_state",
        "source_path": "docs/test", "related_action_id": f"high_risk_{i:03d}",
        "risk_level": "high", "approval_required_for": "High risk — Ray only.",
        "if_approved": "Proceeds.", "if_rejected": "Stays blocked.",
        "safe_internal_next_step": "Wait for Ray.", "evidence_paths": [],
        "created_at": "2026-06-02T10:00:00+00:00",
    }
    item = normalize_approval_item(raw, index=i)
    item["status"] = "pending"
    high_risk_items.append(item)

_save_state({"created_at": "2026-06-02T10:00:00+00:00", "items": high_risk_items, "archived": []})
resp = run_command("bulk approve", source="cli")
check("starts with BULK APPROVE", resp.startswith("BULK APPROVE"))
check("no safe items eligible",
      "no safe" in resp.lower() or "not eligible" in resp.lower() or "individual" in resp.lower())

state = _load_state()
for item in state.get("items", []):
    check(f"'{item['title']}' NOT bulk-approved (still pending)",
          item.get("status") == "pending")

# ── individual approve on high-risk works (Ray's explicit choice) ─────────────
print("\n-- individual approve high-risk item allowed (explicit Ray decision) --")
result = approve_approval_item(1)
check("approve_approval_item success=True", result.get("success") == True)
state2 = _load_state()
first_item = state2["items"][0]
check("first item now approved", first_item.get("status") == "approved")

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
