#!/usr/bin/env python3
"""Hermes Advisor command knowledge: drafts exact commands, never executes."""
from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lib import hermes_mobile_conversation as HM  # noqa: E402

CASES = [
    ("How do I approve the credit package?",
     lambda r: r["command_draft"] and "approve all assets in package proof_credit" in r["command_draft"]
               and "manual use" in r["command_draft"].lower()),
    ("What command should I send TheChoseone to run monetization scout?",
     lambda r: r["command_draft"] and ("web research" in r["command_draft"] or "monetization" in r["command_draft"].lower())),
    ("Can TheChoseone run Codex?",
     lambda r: "bridge is off" in r["answer"].lower() and r["command_draft"] and r["command_draft"].startswith("task for codex")),
    ("Research affiliate offers for funding checklist.",
     lambda r: r["command_draft"] and r["command_draft"].startswith("run web research")),
    ("How do I stop trading?",
     lambda r: r["command_draft"] == "stop trading"),
    ("What can TheChoseone do?",
     lambda r: "what needs approval" in r["answer"].lower() or r.get("proposed_action")),
]


def main() -> int:
    fails = 0
    for msg, check in CASES:
        r = HM.respond(msg)              # deterministic path (no model needed)
        ok = bool(check(r))
        # advisor must NEVER claim execution + must remain read-only
        ans = (r["answer"] + " " + (r.get("proposed_action") or "")).lower()
        no_exec = not any(p in ans for p in ("i approved", "i executed", "i ran", "i sent the", "i'll approve"))
        ok = ok and no_exec and r["read_only"] is True
        fails += (not ok)
        print(f"\n{'✓' if ok else '✗FAIL'} :: {msg}")
        print("   answer:", r["answer"][:150])
        if r.get("command_draft"):
            print("   draft :", r["command_draft"][:140])

    assert HM.CAPABILITIES["execute_commands"] is False
    print(f"\n=== {len(CASES)} cases · {fails} failures · advisor cannot execute ===")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
