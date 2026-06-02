"""
test_approval_queue_impact_simulation.py
Tests: approval_impact intent routing and IF APPROVED/IF REJECTED response.
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

DUMP_MARKERS = ["artifact_inventory", "═══", "HERMES REPORT", "handoff dump", "Executive Memory"]


def check(label: str, cond: bool):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else:    FAIL += 1; print(f"  FAIL  {label}")


def no_dump(text: str) -> bool:
    return not any(m in text for m in DUMP_MARKERS)


def seed():
    from lib.hermes_approval_queue import _save_state, normalize_approval_item
    raw = {
        "_source_type": "action_queue",
        "title": "Finalize lead magnet PDF",
        "summary": "PDF ready for final review",
        "category": "asset_review",
        "source": "action_queue",
        "source_path": "docs/reports/actions/hermes_action_queue.jsonl",
        "related_action_id": "impact_test_001",
        "risk_level": "medium",
        "approval_required_for": "PDF needs final Ray sign-off.",
        "if_approved": "PDF moves to distribution prep stage.",
        "if_rejected": "PDF stays in draft; no distribution.",
        "safe_internal_next_step": "Review PDF and decide.",
        "evidence_paths": ["docs/reports/actions/hermes_action_queue.jsonl"],
        "created_at": "2026-06-02T10:00:00+00:00",
    }
    item = normalize_approval_item(raw, index=1)
    item["status"] = "pending"
    state = {"created_at": "2026-06-02T10:00:00+00:00", "items": [item], "archived": []}
    _save_state(state)


print("=== test_approval_queue_impact_simulation ===\n")

from hermes_command_router.router import run_command
from hermes_command_router.intake import classify_intent

# ── routing ───────────────────────────────────────────────────────────────────
print("-- classify_intent routes impact phrases to approval_impact --")
IMPACT_PHRASES = [
    "what happens if i approve item 1",
    "what would happen if i approve item 1",
    "if i approve item 1",
    "impact of approving item 1",
    "simulate approval item 1",
    "what happens if i reject item 1",
    "if i reject item 1",
    "impact of rejecting item 1",
    "simulate rejection item 1",
]
for phrase in IMPACT_PHRASES:
    intent, _, _ = classify_intent(phrase)
    check(f"[{phrase[:50]}] → approval_impact", intent == "approval_impact")

# ── approve impact response ───────────────────────────────────────────────────
print("\n-- IF APPROVED response --")
seed()
resp_app = run_command("what happens if i approve item 1", source="cli")
check("starts with IF APPROVED", resp_app.startswith("IF APPROVED"))
check("mentions item", "lead magnet" in resp_app.lower() or "pdf" in resp_app.lower() or "Item" in resp_app)
check("lists things Hermes would NOT do automatically",
      "would not" in resp_app.lower() or "not automatically" in resp_app.lower() or "still would not" in resp_app.lower())
check("mentions boundary", "boundary" in resp_app.lower() or "approval" in resp_app.lower())
check("no dump markers", no_dump(resp_app))
check("no ═══", "═══" not in resp_app)

# ── reject impact response ────────────────────────────────────────────────────
print("\n-- IF REJECTED response --")
resp_rej = run_command("what happens if i reject item 1", source="cli")
check("starts with IF REJECTED", resp_rej.startswith("IF REJECTED"))
check("mentions item", "lead magnet" in resp_rej.lower() or "pdf" in resp_rej.lower() or "Item" in resp_rej)
check("no dump markers", no_dump(resp_rej))
check("no ═══", "═══" not in resp_rej)

# ── non-existent item ─────────────────────────────────────────────────────────
print("\n-- non-existent item ref --")
resp_bad = run_command("what happens if i approve item 999", source="cli")
check("IF APPROVED in response", "IF APPROVED" in resp_bad)
check("not found message", "not found" in resp_bad.lower() or "no item" in resp_bad.lower())
check("no dump markers", no_dump(resp_bad))

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
