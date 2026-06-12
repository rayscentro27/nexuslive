#!/usr/bin/env python3
"""Start the Hermes Mobile Advisor Telegram bot — READ-ONLY, test-only.

Locked to the single allowed chat (HERMES_MOBILE_CHAT_ID). Replies conversationally
via the local model and DRAFTS commands for TheChoseone; it never executes, sends
email/DMs, approves assets, trades, deploys, or spends. Uses a dedicated token
(HERMES_MOBILE_BOT_TOKEN) — never TheChoseone's token.

Usage:
  python3 scripts/run_hermes_mobile_telegram.py            # run until stopped
  python3 scripts/run_hermes_mobile_telegram.py --minutes 30
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lib import hermes_mobile_telegram as T   # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--minutes", type=float, default=None,
                    help="stop after N minutes (default: run until killed)")
    args = ap.parse_args()
    if not T.token_present():
        print("BLOCKED: no HERMES_MOBILE_BOT_TOKEN.\n" + T.setup_instructions())
        return 1
    if not T.allowed_chat_id():
        print("BLOCKED: no HERMES_MOBILE_CHAT_ID (allowed chat required).")
        return 1
    max_seconds = int(args.minutes * 60) if args.minutes else None
    return T.run_live(max_seconds=max_seconds)


if __name__ == "__main__":
    raise SystemExit(main())
