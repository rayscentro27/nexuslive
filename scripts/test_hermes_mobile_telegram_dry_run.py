#!/usr/bin/env python3
"""Dry-run the Hermes Mobile Telegram handler. No live connection, no sends.
Verifies read-only behavior, command drafting (not execution), and routing."""
from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lib import hermes_mobile_telegram as TGM   # noqa: E402
from lib import hermes_mobile_conversation as HM  # noqa: E402

MESSAGES = [
    "What is Nexus doing right now?",
    "What needs my attention?",
    "How do we make money in the next 30 days?",
    "Explain the daily report in plain English.",
    "Tell TheChoseone to run monetization scout.",
    "Approve all credit assets with notes: looks good.",
    "What is the weakest part of Nexus?",
    "Research Postiz and tell me if we should use it.",
]


def main() -> int:
    # hard read-only guarantees
    assert HM.CAPABILITIES["write_nexus"] is False
    assert HM.CAPABILITIES["execute_commands"] is False
    assert HM.CAPABILITIES["send_email"] is False and HM.CAPABILITIES["send_dm"] is False
    st = TGM.status()
    print("=== telegram status ===")
    print(f"  token_present={st['token_present']} mode={st['mode']} "
          f"reuses_thechoseone_token={st['reuses_thechoseone_token']} read_only={st['read_only']}")
    if not st["token_present"]:
        print("  (dry-run — dedicated HERMES_MOBILE_BOT_TOKEN not configured)")

    print("\n=== dry-run handling ===")
    for msg in MESSAGES:
        res = TGM.handle_message(msg, chat_id="dry_run")
        assert res["executed"] is False, "must never execute"
        if res["will_reply"]:
            print(f"\n[Hermes Mobile] :: {msg}")
            print("  provider:", res.get("provider"), "| fallback:", res.get("used_fallback"))
            print("  reply:", (res["reply_text"][:300]).replace("\n", " ⏎ "))
            if res.get("command_draft"):
                print("  command_draft (NOT executed):", res["command_draft"])
        else:
            print(f"\n[routed -> {res['routed_to']}] :: {msg}")
            print("  (Hermes Mobile silent; command goes to TheChoseone; executed:", res["executed"], ")")
    print("\n=== dry-run OK · nothing executed/sent ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
