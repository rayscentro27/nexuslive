#!/usr/bin/env python3
"""Regression tests for Hermes Advisor answer quality + approval routing.
Deterministic (no model). Proves: routing of status/scouts/approvals, CEO-level
30-day answer, no vague 'analyze' filler, web -> research handoff."""
from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lib import hermes_mobile_conversation as HM   # noqa: E402
from lib import nexus_war_room_router as RT        # noqa: E402

VAGUE = ["analyze the assets", "analyze ai_improvement", "analyze trading",
         "analyze the risk assessment", "shaky foundations", "analyze the risk"]


def _no_vague(r: dict) -> bool:
    blob = (r["answer"] + " " + (r.get("proposed_action") or "") + " " + (r.get("summary") or "")).lower()
    return not any(v in blob for v in VAGUE)


def main() -> int:
    fails = 0

    def check(name, cond):
        nonlocal fails
        print(f"  {'✓' if cond else '✗FAIL'} {name}")
        fails += (not cond)

    print("=== routing ===")
    check("status -> TheChoseone", RT.route("status")["target"] == "thechoseone")
    check("scouts status -> TheChoseone", RT.route("scouts status")["target"] == "thechoseone")
    for p in ["what needs to be approved", "what do I need to approve", "approval queue",
              "pending approvals", "what assets need review", "what packages need review"]:
        check(f"{p!r} -> TheChoseone", RT.route(p)["target"] == "thechoseone")

    print("\n=== greeting ===")
    g = HM.respond("good morning")
    check("greeting is short + concrete (no long identity)", "good morning" in g["answer"].lower()
          and "approvals" in g["answer"].lower() and len(g["answer"]) < 320)
    check("greeting offers the command", g.get("command_draft") == "what needs approval")

    print("\n=== 30-day money ===")
    m = HM.respond("how do we make money in 30 days")
    a = m["answer"].lower()
    check("prioritizes Credit/Funding Readiness", "credit/funding readiness" in a)
    check("has the 3 concrete actions", "what needs approval" in a and "$97" in a and "manual" in a)
    check("does NOT lead with AI_improvement/trading", not a.strip().startswith(("analyze", "trading", "ai_improvement")))
    check("trading only secondary", "trading stays secondary" in a or "secondary" in a)
    check("no vague analyze filler", _no_vague(m))

    print("\n=== attention ===")
    at = HM.respond("what needs my attention")
    check("review queue first", "review queue first" in at["answer"].lower())
    check("includes exact command", at.get("command_draft") == "what needs approval")
    check("no vague filler", _no_vague(at))

    print("\n=== approval queue routed to command ===")
    ap = HM.respond("what needs to be approved")
    check("drafts 'what needs approval'", ap.get("command_draft") == "what needs approval")
    check("says it's a TheChoseone command", "thechoseone" in ap["answer"].lower())
    check("does not give vague advice", _no_vague(ap))

    print("\n=== what do you think about nexus ===")
    wt = HM.respond("what do you think about the nexus program")
    check("honest+constructive (real value)", "real value" in wt["answer"].lower())
    check("names the gap = execution/monetization", "execution" in wt["answer"].lower())
    check("no 'shaky/fragile' without specifics", "shaky foundations" not in wt["answer"].lower())
    check("no vague filler", _no_vague(wt))

    print("\n=== web search ===")
    w = HM.respond("can you search the web")
    check("drafts research task (no live browsing)", bool(w.get("command_draft"))
          and ("research" in (w.get("command_draft") or "").lower()
               or "browse" in w["answer"].lower() or "live weather" in w["answer"].lower()))

    print("\n=== safety ===")
    check("advisor cannot execute", HM.CAPABILITIES["execute_commands"] is False)

    print(f"\n=== {fails} failures ===")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
