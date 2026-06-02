"""
test_approval_queue_module.py
Tests: hermes_approval_queue.py module imports, constants, and basic API surface.
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


print("=== test_approval_queue_module ===\n")

from lib.hermes_approval_queue import (
    HIGH_RISK_CATEGORIES, ALL_CATEGORIES, SAFE_INTERNAL_WORK, APPROVAL_BOUNDARY,
    build_approval_queue, list_approval_items, normalize_approval_item,
    approve_approval_item, reject_approval_item, simulate_approval_impact,
    simulate_rejection_impact, archive_stale_approval_items, get_approval_item,
    explain_approval_item, format_approval_queue, format_approval_item_detail,
    format_approval_impact, format_approval_result,
)

# ── Constants ─────────────────────────────────────────────────────────────────
print("-- constants --")
check("HIGH_RISK_CATEGORIES is frozenset", isinstance(HIGH_RISK_CATEGORIES, frozenset))
check("content_publish in HIGH_RISK", "content_publish" in HIGH_RISK_CATEGORIES)
check("subscriber_email in HIGH_RISK", "subscriber_email" in HIGH_RISK_CATEGORIES)
check("live_trading in HIGH_RISK", "live_trading" in HIGH_RISK_CATEGORIES)
check("production_deploy in HIGH_RISK", "production_deploy" in HIGH_RISK_CATEGORIES)
check("payment_or_stripe in HIGH_RISK", "payment_or_stripe" in HIGH_RISK_CATEGORIES)
check("internal_review NOT in HIGH_RISK", "internal_review" not in HIGH_RISK_CATEGORIES)
check("lesson_approval NOT in HIGH_RISK", "lesson_approval" not in HIGH_RISK_CATEGORIES)
check("APPROVAL_BOUNDARY is str", isinstance(APPROVAL_BOUNDARY, str))
check("APPROVAL_BOUNDARY mentions publish", "publish" in APPROVAL_BOUNDARY.lower())
check("SAFE_INTERNAL_WORK is list", isinstance(SAFE_INTERNAL_WORK, list))
check("SAFE_INTERNAL_WORK not empty", len(SAFE_INTERNAL_WORK) > 0)

# ── build_approval_queue returns list ──────────────────────────────────────────
print("\n-- build_approval_queue --")
items = build_approval_queue()
check("returns list", isinstance(items, list))
check("items have approval_id", all("approval_id" in i for i in items) if items else True)
check("items have status", all("status" in i for i in items) if items else True)
check("items have title", all("title" in i for i in items) if items else True)

# ── list_approval_items only pending ──────────────────────────────────────────
print("\n-- list_approval_items --")
pending = list_approval_items()
check("returns list", isinstance(pending, list))
check("all pending items have status=pending",
      all(i.get("status") == "pending" for i in pending))

# ── normalize_approval_item ───────────────────────────────────────────────────
print("\n-- normalize_approval_item --")
raw = {
    "_source_type": "action_queue",
    "title": "Review action queue",
    "summary": "Check pending actions",
    "category": "internal_review",
    "source": "action_queue",
    "source_path": "docs/reports/actions/hermes_action_queue.jsonl",
    "related_action_id": "test_action_001",
    "risk_level": "low",
    "approval_required_for": "Needs Ray sign-off.",
    "if_approved": "Hermes proceeds.",
    "if_rejected": "Action stays blocked.",
    "safe_internal_next_step": "Review and decide.",
    "evidence_paths": ["docs/reports/actions/hermes_action_queue.jsonl"],
    "created_at": "2026-06-02T10:00:00+00:00",
}
item = normalize_approval_item(raw, index=1)
check("has approval_id", bool(item.get("approval_id")))
check("approval_id starts with apq_", item["approval_id"].startswith("apq_"))
check("stable id: same input → same id",
      normalize_approval_item(raw, 1)["approval_id"] == item["approval_id"])
check("status == pending", item["status"] == "pending")
check("category preserved", item["category"] == "internal_review")
check("approval_boundary set", bool(item.get("approval_boundary")))
check("no raw secrets in item", "_raw" not in item)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
