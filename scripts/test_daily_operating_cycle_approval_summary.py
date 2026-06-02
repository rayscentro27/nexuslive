"""
test_daily_operating_cycle_approval_summary.py
Tests: format_approval_needed_summary includes approval boundaries and safe internal work.
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


print("=== test_daily_operating_cycle_approval_summary ===\n")

from lib.hermes_daily_operating_cycle import (
    build_daily_operating_plan,
    format_approval_needed_summary,
    find_items_needing_ray_approval,
)

# ── format_approval_needed_summary: structure ──────────────────────────────
print("-- format_approval_needed_summary: structure --")
plan = build_daily_operating_plan()
resp = format_approval_needed_summary(plan)

check("non-empty",                              bool(resp))
check("starts with APPROVAL NEEDED",            resp.startswith("APPROVAL NEEDED"))
check("contains approval boundary section",     "Approval boundary" in resp)
check("contains safe internal work section",    "Safe internal work" in resp)
check("approval boundary mentions publishing",  "ublish" in resp)
check("approval boundary mentions payments",    "payment" in resp.lower() or "paid" in resp.lower())
check("approval boundary mentions live trading","live trading" in resp.lower())
check("contains draft revisions",               "draft" in resp.lower())
check("contains research",                      "research" in resp.lower())
check("contains action queue",                  "action queue" in resp.lower())

# ── no evidence dump ──────────────────────────────────────────────────────
print("\n-- no evidence dump in approval summary --")
DUMP_MARKERS = ["artifact_inventory", "handoff dump", "Executive Memory",
                "I can answer from verified", "═══", "HERMES REPORT"]
check("no evidence dump",
      not any(m in resp for m in DUMP_MARKERS))

# ── routing ────────────────────────────────────────────────────────────────
print("\n-- routing: daily_approval_needed intent --")
from hermes_command_router.router import run_command
from hermes_command_router.intake import classify_intent

for phrase in [
    "show approval queue",
    "show items needing approval",
    "approval queue",
    "what needs ray approval",
]:
    intent, _, _ = classify_intent(phrase)
    check(f"classify_intent({phrase!r}) == daily_approval_needed", intent == "daily_approval_needed")
    resp_r = run_command(phrase, source="cli")
    check(f"'{phrase}': non-empty",                bool(resp_r))
    check(f"'{phrase}': APPROVAL NEEDED",          "APPROVAL NEEDED" in resp_r)
    check(f"'{phrase}': approval boundary present", "Approval boundary" in resp_r)
    check(f"'{phrase}': no evidence dump",
          not any(m in resp_r for m in DUMP_MARKERS))

# ── with pending actions needing approval: items listed ───────────────────
print("\n-- approval items structure --")
items = find_items_needing_ray_approval({"action_queue": [
    {
        "action_id": "act_test1",
        "title": "Publish lead magnet to landing page",
        "status": "needs_ray_approval",
        "requires_ray_approval": True,
        "approval_reason": "Publishing requires Ray sign-off.",
        "next_step": "Upload to landing page.",
    }
], "decisions": []})
check("approval items: is list",              isinstance(items, list))
check("approval items: 1 item found",         len(items) == 1)
check("approval items: has item key",         "item" in items[0])
check("approval items: has why key",          "why" in items[0])
check("approval items: has next_if_approved", "next_if_approved" in items[0])
check("approval items: has risk_if_skipped",  "risk_if_skipped" in items[0])

# Inject this plan and check formatting
plan_with_approval = {
    "date": "2026-06-02",
    "approval_items": items,
    "approval_boundary": "I will not publish, email, or spend money without Ray approval.",
}
resp_with = format_approval_needed_summary(plan_with_approval)
check("item title in response",              "Publish lead magnet" in resp_with)
check("why text in response",                "Publishing requires Ray" in resp_with)

# ── empty approval items ──────────────────────────────────────────────────
print("\n-- empty approval items --")
plan_empty = {"date": "2026-06-02", "approval_items": []}
resp_empty = format_approval_needed_summary(plan_empty)
check("empty: APPROVAL NEEDED header",       "APPROVAL NEEDED" in resp_empty)
check("empty: no items waiting message",     "No items currently waiting" in resp_empty)
check("empty: approval boundary present",    "Approval boundary" in resp_empty)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
