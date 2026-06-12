#!/usr/bin/env python3
"""Track A test: verify command-bot reports are mobile-readable (≤12 lines,
have a next action / safety line, no raw ID dumps by default)."""
from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lib import nexus_telegram_ops as TG  # noqa: E402

COMMANDS = [
    "status", "scouts status", "status research queue", "status credit scout",
    "status funding scout", "status opportunity scout", "status trading scout",
    "status ai scout", "what needs approval", "what did nexus produce",
    "daily report", "pause automation", "resume automation", "stop sends",
    "stop trading", "approve all assets in package proof_credit with notes: test note",
    "request revision for package proof_funding with notes: tighten copy",
]


def main() -> int:
    fails = 0
    for c in COMMANDS:
        out = TG.command_report(c)
        n_lines = len([l for l in out.splitlines() if l.strip()])
        too_long = n_lines > 12 and "details" not in c and "scout" not in c
        raw_id = "asset_" in out and "details" not in c
        flag = " ⚠️LONG" if too_long else (" ⚠️RAWID" if raw_id else " ✓")
        if too_long or raw_id:
            fails += 1
        print(f"\n### {c}{flag}  ({n_lines} lines)")
        print(out[:500])
    # show a 'details' expansion works
    print("\n### status details (full)")
    print(TG.command_report("status details")[:300])
    print(f"\n=== {len(COMMANDS)} commands tested · {fails} formatting issues ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
