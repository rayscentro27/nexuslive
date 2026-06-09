#!/usr/bin/env python3
"""
content_board_list.py — list Content Workspace Board cards (read-only).

Reads reports/content_engine/content_board.jsonl. No writes, no network, no publishing.

Examples:
  python scripts/content_board_list.py                      # all cards (table)
  python scripts/content_board_list.py --status "Needs Ray Review"
  python scripts/content_board_list.py --needs-review       # Ray decision queue
  python scripts/content_board_list.py --json               # machine-readable
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lib.content_board import load_board, STATUSES, RAY_REVIEW_STATUSES  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="List Content Board cards")
    ap.add_argument("--status", default=None, choices=STATUSES)
    ap.add_argument("--needs-review", action="store_true", help="only items awaiting Ray review")
    ap.add_argument("--content-id", default=None, help="filter by content_id (prefix ok)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    cards = load_board()
    if args.status:
        cards = [c for c in cards if c.get("status") == args.status]
    if args.needs_review:
        cards = [c for c in cards if c.get("status") in RAY_REVIEW_STATUSES]
    if args.content_id:
        cards = [c for c in cards if str(c.get("content_id", "")).startswith(args.content_id)]

    if args.json:
        print(json.dumps(cards, indent=2, ensure_ascii=False))
        return 0

    if not cards:
        print("(no matching cards)")
        return 0

    order = {s: i for i, s in enumerate(STATUSES)}
    cards.sort(key=lambda c: (order.get(c.get("status"), 99), c.get("updated_at", "")))
    print(f"{'BOARD_ID':<16} {'STATUS':<20} {'RISK':<15} {'APPR':<9} TITLE")
    print("-" * 92)
    for c in cards:
        appr = "yes" if c.get("approval_required") else "no"
        appr += f"/{c.get('approval_status')}" if c.get("approval_status", "none") != "none" else ""
        print(f"{c.get('board_id',''):<16} {c.get('status',''):<20} "
              f"{c.get('publish_risk_level',''):<15} {appr:<9} {c.get('title','')}")
    print("-" * 92)
    print(f"{len(cards)} card(s). Use --json for full detail, --needs-review for the Ray queue.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
