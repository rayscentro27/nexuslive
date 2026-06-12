#!/usr/bin/env python3
"""War-room alias normalization tests (approval + scout status).
Proves TheChoseone's reporter handles every alias, the router routes them, and
Hermes hands off operational commands instead of inventing state."""
from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lib import hermes_command_reporter as R     # noqa: E402
from lib import nexus_war_room_router as RT       # noqa: E402
from lib import hermes_mobile_conversation as HM  # noqa: E402

fails = 0
def check(name, cond):
    global fails
    print(f"  {'✓' if cond else '✗FAIL'} {name}")
    fails += (not cond)

print("=== BUG 1: approval aliases -> TheChoseone canonical handler ===")
for p in ["what needs to be approved", "what needs approval", "what do I need to approve",
          "what needs my approval", "approvals", "approval queue", "show approvals",
          "pending approvals", "what assets need review", "what packages need review",
          "review queue", "showroom queue"]:
    out = R.report(p)
    ok = out is not None and "approve all assets in package" in out and "manual use" in out.lower()
    check(f"report({p!r}) -> approval queue (not 'verified state unavailable')", ok)
    check(f"router routes {p!r} -> thechoseone", RT.route(p)["target"] == "thechoseone")

print("\n=== BUG 2: scout aliases -> TheChoseone scouts status ===")
for p in ["scout status", "scouts status", "scout statuses", "scouts", "scout report",
          "scout reports", "status scouts", "status scout"]:
    out = R.report(p)
    ok = out is not None and ("scout" in out.lower())
    check(f"report({p!r}) -> scouts status", ok)
    check(f"router routes {p!r} -> thechoseone", RT.route(p)["target"] == "thechoseone")

print("\n=== BUG 3: Hermes hands off operational commands (no invented state) ===")
HANDOFFS = {"status": "status", "raw status": "raw status", "scout status": "scouts status",
            "scouts status": "scouts status", "what did nexus produce": "what did nexus produce",
            "trading status": "status", "safety status": "status", "worker bridge status": "status"}
for phrase, canonical in HANDOFFS.items():
    r = HM.respond(phrase)
    ok = (r["intent"] == "op_handoff" and r.get("command_draft") == canonical
          and "thechoseone" in r["answer"].lower()
          and "test mode" not in r["answer"].lower() and "one_shot" not in r["answer"].lower())
    check(f"Hermes {phrase!r} -> handoff '{canonical}' (no invented state)", ok)

# @Hermes approval ask -> drafts 'what needs approval'
r = HM.respond("what needs to be approved")
check("Hermes 'what needs to be approved' -> drafts 'what needs approval'",
      r.get("command_draft") == "what needs approval")

# 'explain status' must NOT hand off — it's conversational
r = HM.respond("explain the status report")
check("'explain the status report' is NOT an op handoff", r["intent"] != "op_handoff")

print("\n=== TASK 1: typo-tolerant approval aliases ===")
for p in ["pending aprrovals", "pending approval", "pending approvals", "pending aprovals",
          "pending apprrovals", "aprrovals", "aprovals", "approvals", "approval",
          "approve queue", "approval que", "approval cue", "review que", "review cue"]:
    out = R.report(p)
    ok = out is not None and "approve all assets in package" in out
    check(f"report({p!r}) -> approval queue", ok)
    check(f"router routes {p!r} -> thechoseone", RT.route(p)["target"] == "thechoseone")

print("\n=== TASK 2: Hermes stays silent on commands (looks_like_command) ===")
for p in ["what needs to be approved", "scout status", "pending aprrovals", "status",
          "scouts status", "review queue", "what did nexus produce"]:
    check(f"looks_like_command({p!r}) True -> Hermes skips in group", RT.looks_like_command(p) is True)
# advisory questions are NOT commands -> Hermes answers
for p in ["what should I do next", "how do we make money in 30 days", "explain the status report"]:
    check(f"looks_like_command({p!r}) False -> Hermes answers", RT.looks_like_command(p) is False)

print("\n=== TASK 3: explain the status report -> plain English (no handoff) ===")
e = HM.respond("explain the status report")
check("explain is conversational (not op_handoff)", e["intent"] != "op_handoff")
check("explain mentions review queue / Credit-Funding / $97",
      ("review" in e["answer"].lower() or "showroom" in e["answer"].lower())
      and "credit/funding" in e["answer"].lower() and "$97" in e["answer"])

print("\n=== safety ===")
check("Hermes cannot execute", HM.CAPABILITIES["execute_commands"] is False)

print(f"\n=== {fails} failures ===")
sys.exit(1 if fails else 0)
