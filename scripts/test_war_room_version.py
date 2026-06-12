#!/usr/bin/env python3
"""war room version diagnostic + generic-intro discipline (Task 1 & 5)."""
from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lib import hermes_command_reporter as R       # noqa: E402
from lib import nexus_war_room_router as RT         # noqa: E402
from lib import hermes_mobile_conversation as HM    # noqa: E402

fails = 0
def check(name, cond):
    global fails
    print(f"  {'✓' if cond else '✗FAIL'} {name}")
    fails += (not cond)

print("=== TASK 1: TheChoseone 'war room version' ===")
out = R.report("war room version")
check("routes to TheChoseone", RT.route("war room version")["target"] == "thechoseone")
check("has Git commit", out is not None and "Git commit:" in out)
check("has Router version", "Router version:" in out)
check("has reporter version", "reporter version:" in out)
check("read-only diagnostic note", "no execution" in out.lower())

print("\n=== TASK 1: Hermes 'war room version' reports its own ===")
h = HM.respond("war room version")
check("Hermes version intent", h["intent"] == "version")
check("Hermes reports git commit", "git commit" in h["answer"].lower())
check("Hermes points to TheChoseone for command-bot version", "thechoseone" in h["answer"].lower())

print("\n=== TASK 5: generic intro ONLY for help/who-are-you ===")
for p in ["help", "what can you do", "who are you", "start"]:
    r = HM.respond(p)
    check(f"{p!r} -> help intro allowed", r["intent"] == "help" and "read-only nexus advisor" in r["answer"].lower())

INTRO_MARK = "conversation-side hermes"
for p in ["show package proof_credit", "what needs approval", "pending approvals", "scout status",
          "details package proof_credit", "status"]:
    r = HM.respond(p)
    check(f"{p!r} -> NO generic intro (handoff)", INTRO_MARK not in r["answer"].lower() and r["intent"] == "op_handoff")

# open/unknown conversational -> NOT the identity blurb
r = HM.respond("what do you recommend we do today")
check("open question -> no identity blurb", INTRO_MARK not in r["answer"].lower())

print("\n=== safety ===")
check("Hermes cannot execute", HM.CAPABILITIES["execute_commands"] is False)
print(f"\n=== {fails} failures ===")
sys.exit(1 if fails else 0)
