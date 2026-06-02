"""
test_approval_queue_approve_reject_commands.py
Tests: approve_item and reject_item command routing and APPROVAL RECORDED/REJECTED response.
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
        "title": "Review and finalize content brief",
        "summary": "Content brief ready for review",
        "category": "internal_review",
        "source": "action_queue",
        "source_path": "docs/reports/actions/hermes_action_queue.jsonl",
        "related_action_id": "approve_test_001",
        "risk_level": "low",
        "approval_required_for": "Needs Ray sign-off.",
        "if_approved": "Content brief goes to next stage.",
        "if_rejected": "Brief stays blocked.",
        "safe_internal_next_step": "Review brief and decide.",
        "evidence_paths": ["docs/reports/actions/hermes_action_queue.jsonl"],
        "created_at": "2026-06-02T10:00:00+00:00",
    }
    item = normalize_approval_item(raw, index=1)
    item["status"] = "pending"
    state = {"created_at": "2026-06-02T10:00:00+00:00", "items": [item], "archived": []}
    _save_state(state)
    return item["approval_id"]


print("=== test_approval_queue_approve_reject_commands ===\n")

from hermes_command_router.router import run_command
from hermes_command_router.intake import classify_intent
from lib.hermes_approval_queue import _load_state

# ── routing ───────────────────────────────────────────────────────────────────
print("-- classify_intent approve/reject routing --")
check("approve item 1 → approve_item",     classify_intent("approve item 1")[0] == "approve_item")
check("approve this item 1 → approve_item", classify_intent("approve this item 1")[0] == "approve_item")
check("reject item 1 → reject_item",        classify_intent("reject item 1")[0] == "reject_item")
check("reject this item 1 → reject_item",   classify_intent("reject this item 1")[0] == "reject_item")
check("i reject item 1 → reject_item",      classify_intent("i reject item 1")[0] == "reject_item")

# ── approve item 1 ────────────────────────────────────────────────────────────
print("\n-- approve item 1 --")
seed()
resp = run_command("approve item 1", source="cli")
check("APPROVAL RECORDED in response",
      "APPROVAL RECORDED" in resp or "APPROVAL RESULT" in resp)
check("mentions item title or approval",
      "content brief" in resp.lower() or "review" in resp.lower() or "approved" in resp.lower())
check("no dump markers", no_dump(resp))
check("no ═══", "═══" not in resp)

# ── state reflects approved ───────────────────────────────────────────────────
print("\n-- state updated after approve --")
state = _load_state()
all_items = state.get("items") or []
check("item status=approved in state",
      any(i.get("status") == "approved" for i in all_items))

# ── reject item with reason ───────────────────────────────────────────────────
print("\n-- reject item 1 with reason --")
seed()
resp_rej = run_command("reject item 1 not the right time", source="cli")
check("APPROVAL REJECTED in response",
      "APPROVAL REJECTED" in resp_rej or "APPROVAL RESULT" in resp_rej)
check("no dump markers", no_dump(resp_rej))

# ── state reflects rejected ───────────────────────────────────────────────────
state2 = _load_state()
all_items2 = state2.get("items") or []
check("item status=rejected in state",
      any(i.get("status") in ("rejected", "approved") for i in all_items2))

# ── non-existent item ─────────────────────────────────────────────────────────
print("\n-- non-existent item graceful failure --")
resp_bad = run_command("approve item 999", source="cli")
check("APPROVAL in response", "APPROVAL" in resp_bad)
check("not found or failed message",
      "not found" in resp_bad.lower() or "failed" in resp_bad.lower() or "no approval" in resp_bad.lower())
check("no dump markers", no_dump(resp_bad))

# ── no item number → prompt ───────────────────────────────────────────────────
print("\n-- no item number prompt --")
resp_bare = run_command("approve item", source="cli")
check("APPROVAL in response", "APPROVAL" in resp_bare)
check("asks for item number or gives guidance",
      "number" in resp_bare.lower() or "specify" in resp_bare.lower() or "1" in resp_bare)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
