#!/usr/bin/env python3
"""show package routing: -> TheChoseone, polished package summary, Hermes handoff
when mentioned, no generic intro. Read-only."""
from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lib import nexus_war_room_router as RT       # noqa: E402
from lib import hermes_command_reporter as R       # noqa: E402
from lib import hermes_mobile_conversation as HM   # noqa: E402

fails = 0
def check(name, cond):
    global fails
    print(f"  {'✓' if cond else '✗FAIL'} {name}")
    fails += (not cond)

print("=== TASK 1: routing -> TheChoseone ===")
ROUTE_CASES = {
    "show package proof_credit": "proof_credit",
    "package proof_credit": "proof_credit",
    "view package proof_credit": "proof_credit",
    "details package proof_credit": "proof_credit",
    "show proof_credit": "proof_credit",
    "show credit package": "proof_credit",
    "credit package": "proof_credit",
    "show funding package": "proof_funding",
    "show opportunity package": "proof_opportunity",
    "show trading package": "proof_trading",
    "ai improvement package": "proof_ai_improvement",
}
for phrase, pid in ROUTE_CASES.items():
    r = RT.route(phrase)
    check(f"{phrase!r} -> TheChoseone", r["target"] == "thechoseone")
    check(f"{phrase!r} -> canonical 'show package {pid}'", RT.canonical_command(phrase) == f"show package {pid}")

print("\n=== TASK 2: TheChoseone polished package response ===")
out = R.report("show package proof_credit")
print(out)
print("---")
check("has package id", out is not None and "Package id: proof_credit" in out)
check("has status", "Status:" in out)
check("has assets count", "Assets:" in out)
check("approve command", "approve all assets in package proof_credit with notes: Approved for manual use only." in out)
check("revision command", "request revision for package proof_credit with notes: Make this more specific" in out)
check("details package command", "details package proof_credit" in out)
check("safety note (manual-use, no publish/send/charge)",
      "manual-use review only" in out.lower() and "does not publish, send, charge" in out.lower())
check("not raw JSON", "{" not in out and "asset_id" not in out)

print("\n=== TASK 3: Hermes handoff (mentioned) ===")
h = HM.respond("show package proof_credit")
check("Hermes hands off (op_handoff)", h["intent"] == "op_handoff")
check("draft is exact command", h.get("command_draft") == "show package proof_credit")
check("Showroom-command wording", "showroom command" in h["answer"].lower())
check("offers to help review after", "after thechoseone" in (h.get("proposed_action") or "").lower())
check("does NOT invent package details", "39 assets" not in h["answer"] and "Package id" not in h["answer"])

print("\n=== TASK 4: no generic intro on recognized command ===")
check("not the generic intro", "conversation-side hermes" not in h["answer"].lower())
check("Hermes stays silent in group (looks_like_command)", RT.looks_like_command("show package proof_credit") is True)

print("\n=== safety ===")
check("Hermes cannot execute", HM.CAPABILITIES["execute_commands"] is False)

print(f"\n=== {fails} failures ===")
sys.exit(1 if fails else 0)
