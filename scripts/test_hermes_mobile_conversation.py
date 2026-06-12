#!/usr/bin/env python3
"""Track B dry-run: exercise the parallel Hermes Mobile Conversation bot.
Read-only. Compares command-bot style vs conversational Hermes for each message,
and writes a before/after results report."""
from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lib import hermes_mobile_conversation as HM   # noqa: E402
from lib import nexus_telegram_ops as TG           # noqa: E402

MESSAGES = [
    "Status",
    "What is Nexus doing right now?",
    "What needs my attention?",
    "What did the scouts produce?",
    "Explain the continuous operations report in plain English.",
    "What should I approve from my phone?",
    "How do we make money in 30 days?",
    "Turn this into a task for TheChoseone.",
    "What is the weakest part of Nexus?",
    "Give me the command to approve the credit package with notes.",
]

# rough mapping to a command-bot equivalent (for before/after)
CMD_EQUIV = {
    0: "status", 1: "status", 2: "what needs approval", 3: "status credit scout",
    4: "daily report", 5: "what needs approval", 6: None,
    7: "approve all assets in package proof_credit with notes: ...", 8: None, 9: None,
}


def main() -> int:
    assert HM.CAPABILITIES["write_nexus"] is False, "bot must be read-only"
    assert HM.CAPABILITIES["send_email"] is False and HM.CAPABILITIES["execute_commands"] is False
    rows = []
    for i, msg in enumerate(MESSAGES):
        resp = HM.respond(msg)
        tg = HM.format_for_telegram(resp)
        ce = CMD_EQUIV.get(i)
        cmd_before = TG.command_report(ce) if ce and "..." not in ce else (ce or "—(no command-bot equivalent)")
        print(f"\n{'='*70}\n[{i+1}] {msg}\n{'-'*70}")
        print("COMMAND BOT (before):")
        print((cmd_before or "")[:280])
        print("\nHERMES MOBILE (after):")
        print(tg[:600])
        rows.append((msg, cmd_before, tg, resp))
        # safety asserts per response
        assert resp["read_only"] is True
        assert resp["command_draft"] is None or isinstance(resp["command_draft"], str)

    # write before/after report
    rp = ROOT / "reports" / "showroom" / "hermes_mobile_test_results.md"
    lines = ["# Hermes Mobile — Dry-Run Test Results", "_read-only · proposes, never executes_", ""]
    for msg, before, after, resp in rows:
        lines += [f"## {msg}", "**Command bot (before):**", "```", str(before)[:400], "```",
                  "**Hermes Mobile (after):**", "```", after[:600], "```",
                  f"_intent: {resp['intent']} · proposed: {resp['proposed_action']}_", ""]
    rp.write_text("\n".join(lines))
    print(f"\n=== {len(MESSAGES)} messages tested · read-only verified · wrote {rp.relative_to(ROOT)} ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
