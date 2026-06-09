#!/usr/bin/env python3
"""
content_board_update.py — update fields on an existing Content Board card.

Reads/writes reports/content_engine/content_board.jsonl only. No network, no publishing.
Safe to run repeatedly.

SAFETY GUARD: moving a card into a Ray-only status (Approved for Unlisted / Approved
Public / Published) requires --ray-approved AND, for Published, an --approval-id. This
keeps the engine from "self-approving" external/public actions. Even then, this script
NEVER uploads — Published is just a board state; the actual post still requires
social_publish_executor.py with its own enable flag + scoped approval.

Examples:
  python scripts/content_board_update.py --id card-fcf087ea --status "Improve / Retry" \
      --next-action "Add b-roll/texture, then re-render"
  python scripts/content_board_update.py --id fcf087ea --approval-id ab12 --approval-status pending
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lib.content_board import (  # noqa: E402
    load_board, save_board, find, STATUSES, RAY_ONLY_STATUSES, _now,
)


def _split(v: str | None) -> list[str] | None:
    if v is None:
        return None
    return [x.strip() for x in v.split(",") if x.strip()]


def main() -> int:
    ap = argparse.ArgumentParser(description="Update a Content Board card")
    ap.add_argument("--id", required=True, help="board_id or content_id (prefix ok)")
    ap.add_argument("--status", default=None, choices=STATUSES)
    ap.add_argument("--priority", default=None, choices=["low", "normal", "high"])
    ap.add_argument("--approval-id", default=None)
    ap.add_argument("--approval-status", default=None,
                    choices=["none", "pending", "approved", "rejected"])
    ap.add_argument("--compliance-status", default=None, choices=["unknown", "pass", "fail"])
    ap.add_argument("--disclosure-present", dest="disclosure_present", action="store_true", default=None)
    ap.add_argument("--publish-risk", default=None, choices=["internal", "external/public", "high"])
    ap.add_argument("--next-action", default=None)
    ap.add_argument("--telegram-summary", default=None)
    ap.add_argument("--performance-status", default=None)
    ap.add_argument("--add-artifact", default=None, help="comma-separated paths to append")
    ap.add_argument("--add-preview", default=None, help="comma-separated paths to append")
    ap.add_argument("--notes", default=None)
    ap.add_argument("--ray-approved", action="store_true",
                    help="required to move into Approved/Published statuses (Ray's explicit decision)")
    args = ap.parse_args()

    cards = load_board()
    card = find(cards, args.id)
    if not card:
        print(f"ERROR: no card matching '{args.id}'", file=sys.stderr)
        return 2

    if args.status in RAY_ONLY_STATUSES and not args.ray_approved:
        print(f"REFUSED: '{args.status}' is a Ray-only status. Re-run with --ray-approved "
              f"(this represents Ray's explicit decision; it does NOT upload).", file=sys.stderr)
        return 3
    if args.status == "Published" and not (args.approval_id or card.get("approval_id")):
        print("REFUSED: moving to 'Published' requires an --approval-id (scoped approval).", file=sys.stderr)
        return 3

    def setif(key, val):
        if val is not None:
            card[key] = val

    setif("status", args.status)
    setif("priority", args.priority)
    setif("approval_id", args.approval_id)
    setif("approval_status", args.approval_status)
    setif("compliance_status", args.compliance_status)
    setif("disclosure_present", args.disclosure_present)
    setif("publish_risk_level", args.publish_risk)
    setif("recommended_next_action", args.next_action)
    setif("telegram_summary", args.telegram_summary)
    setif("performance_check_status", args.performance_status)
    setif("notes", args.notes)
    if args.add_artifact:
        card["artifact_paths"] = list(dict.fromkeys((card.get("artifact_paths") or []) + _split(args.add_artifact)))
    if args.add_preview:
        card["preview_paths"] = list(dict.fromkeys((card.get("preview_paths") or []) + _split(args.add_preview)))

    card["updated_at"] = _now()
    save_board(cards)
    print(f"UPDATED {card['board_id']} · {card['status']} · {card['title']}")
    print(json.dumps(card, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
