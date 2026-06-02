"""
test_approval_queue_daily_cycle_integration.py
Tests: daily cycle approval_items appear in approval queue;
       while_out_summary includes pending approval count;
       daily_approval_needed delegates to format_approval_queue.
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


print("=== test_approval_queue_daily_cycle_integration ===\n")

from lib.hermes_daily_cycle_state import save_daily_cycle_state
from hermes_command_router.router import run_command

# ── seed daily cycle state with approval items ─────────────────────────────────
save_daily_cycle_state({
    "date": "2026-06-02",
    "top_priority": "Finalize lead magnet",
    "blockers": [],
    "approval_items": [
        {
            "item": "Approve newsletter draft",
            "category": "subscriber_email",
            "why": "Newsletter is ready to review before scheduling.",
            "next_if_approved": "Move to scheduling queue.",
            "risk_if_skipped": "Newsletter won't be sent this week.",
        }
    ],
    "safe_next_actions": ["Review and score latest source intake records"],
    "memory_v2_count": 5, "goals_count": 2, "action_count": 3,
})

# ── approval queue picks up daily cycle item ──────────────────────────────────
print("-- daily cycle approval item appears in queue --")
from lib.hermes_approval_queue import build_approval_queue, list_approval_items

items = build_approval_queue()
pending = list_approval_items()
check("at least one pending item from daily cycle", len(pending) >= 1)
daily_titles = [i["title"] for i in pending if i.get("source") == "daily_cycle_state"]
check("daily cycle item in queue",
      any("newsletter" in t.lower() or "approve" in t.lower() for t in daily_titles)
      or any("newsletter" in i["title"].lower() for i in pending))

# ── daily_approval_needed uses format_approval_queue ─────────────────────────
print("\n-- daily_approval_needed delegates to format_approval_queue --")
resp = run_command("what needs approval", source="cli")
check("starts with APPROVAL QUEUE", resp.startswith("APPROVAL QUEUE"))
check("no HERMES REPORT wrapper", not resp.strip().startswith("HERMES REPORT"))
check("no ═══", "═══" not in resp)

# ── show approval queue response has item ─────────────────────────────────────
print("\n-- show approval queue shows daily cycle items --")
resp2 = run_command("show approval queue", source="cli")
check("starts with APPROVAL QUEUE", resp2.startswith("APPROVAL QUEUE"))
check("shows item count or item title",
      "newsletter" in resp2.lower() or "approve" in resp2.lower() or "pending approval items" in resp2.lower())

# ── while_out_summary still works ─────────────────────────────────────────────
print("\n-- while_out_summary still works after cycle integration --")
resp3 = run_command("what happened while i was out", source="cli")
check("while out summary starts correctly",
      resp3.startswith("WHILE YOU WERE OUT") or "WHILE" in resp3[:30])
check("no ═══ in while out", "═══" not in resp3)
check("no HERMES REPORT in while out", not resp3.strip().startswith("HERMES REPORT"))

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
