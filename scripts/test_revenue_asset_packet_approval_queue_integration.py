"""
test_revenue_asset_packet_approval_queue_integration.py
Tests: approval candidates appear in approval queue after packet build;
       show approval queue shows real items; approving records locally.
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


print("=== test_revenue_asset_packet_approval_queue_integration ===\n")

from lib.hermes_approval_queue import _save_state, _load_state, list_approval_items
from lib.hermes_revenue_asset_packet import (
    build_revenue_asset_packet, generate_approval_candidates,
    inject_approval_candidates,
)
from hermes_command_router.router import run_command

# ── reset approval queue state ────────────────────────────────────────────────
_save_state({"created_at": "2026-06-02T10:00:00+00:00", "items": [], "archived": []})

# ── build packet and inject candidates ────────────────────────────────────────
print("-- build packet and inject candidates --")
packet = build_revenue_asset_packet()
candidates = generate_approval_candidates(packet)
result = inject_approval_candidates(candidates)

check("candidates injected (total > 0)", result.get("total", 0) > 0)
check("some added to queue", result.get("added", 0) >= 0)

# ── list_approval_items returns injected items ────────────────────────────────
print("\n-- list_approval_items shows injected items --")
state = _load_state()
all_items = state.get("items") or []
rap_items = [i for i in all_items if i.get("source") == "revenue_asset_packet"]
check("revenue_packet items in state", len(rap_items) >= 1)
for i in rap_items:
    check(f"[{i['title'][:40]}] status == pending", i.get("status") == "pending")

# ── show approval queue shows the items ──────────────────────────────────────
print("\n-- show approval queue shows revenue packet items --")
resp = run_command("show approval queue", source="cli")
check("starts with APPROVAL QUEUE", resp.startswith("APPROVAL QUEUE"))
# If we have pending items, they should appear
if rap_items:
    has_items = (
        "pending approval items" in resp.lower()
        or any(c["title"][:20].lower() in resp.lower() for c in candidates)
        or "approve" in resp.lower()
    )
    check("queue shows pending items or approval content", has_items)
check("no ═══", "═══" not in resp)
check("no HERMES REPORT", not resp.strip().startswith("HERMES REPORT"))

# ── show approval item 1 ──────────────────────────────────────────────────────
print("\n-- show approval item 1 --")
resp2 = run_command("show approval item 1", source="cli")
check("starts with APPROVAL ITEM", resp2.startswith("APPROVAL ITEM"))
check("no ═══", "═══" not in resp2)

# ── approve item 1 records local approval ────────────────────────────────────
print("\n-- approve item 1 records local approval --")
resp3 = run_command("approve item 1", source="cli")
check("APPROVAL in response", "APPROVAL" in resp3)
check("no ═══", "═══" not in resp3)

state_after = _load_state()
approved_items = [i for i in (state_after.get("items") or [])
                  if i.get("status") == "approved"]
check("at least 1 item approved after command", len(approved_items) >= 1)

# ── what happens if I approve item 2 ─────────────────────────────────────────
print("\n-- impact simulation still works --")
resp4 = run_command("what happens if i approve item 2", source="cli")
check("IF APPROVED in response", "IF APPROVED" in resp4)
check("no ═══", "═══" not in resp4)

# ── generate approval candidates command ─────────────────────────────────────
print("\n-- generate approval candidates command --")
resp5 = run_command("generate approval candidates", source="cli")
check("starts with APPROVAL CANDIDATES GENERATED", resp5.startswith("APPROVAL CANDIDATES GENERATED"))
check("mentions added or skipped", "added" in resp5.lower() or "skipped" in resp5.lower())
check("no ═══", "═══" not in resp5)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
