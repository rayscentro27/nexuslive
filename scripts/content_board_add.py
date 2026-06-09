#!/usr/bin/env python3
"""
content_board_add.py — add a card to the Content Workspace Board, or MERGE into an existing one.

Writes only reports/content_engine/content_board.jsonl. No DB, no paid API, no network,
no publishing. Safe to run repeatedly:
  * if no card matches (by --board-id / --content-id): a new card is created with sensible defaults;
  * if a card already exists: only the fields you explicitly pass on this run are overwritten —
    existing data (previews, approvals, notes, etc.) is preserved (no accidental clobber).

Example:
  python scripts/content_board_add.py \
    --content-id fcf087ea-... --title "3 Business Credit Myths" \
    --status "Needs Ray Review" --content-type "YouTube Short" \
    --platform "YouTube Shorts" --preview reports/tool_lab/hyperframes_renders/..._v1.mp4 \
    --approval-required --publish-risk "external/public"
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lib.content_board import new_card, load_board, find, upsert, STATUSES, _now  # noqa: E402


def _split(vals: list[str] | None) -> list[str]:
    out: list[str] = []
    for v in vals or []:
        out.extend([x.strip() for x in v.split(",") if x.strip()])
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Add or merge a Content Board card")
    # All defaults are None so we can tell "explicitly provided" from "omitted" and merge safely.
    ap.add_argument("--content-id", required=True)
    ap.add_argument("--board-id", default=None)
    ap.add_argument("--campaign-id", default=None)
    ap.add_argument("--title", default=None)
    ap.add_argument("--topic", default=None)
    ap.add_argument("--status", default=None, choices=STATUSES)
    ap.add_argument("--priority", default=None, choices=["low", "normal", "high"])
    ap.add_argument("--content-type", default=None)
    ap.add_argument("--platform", action="append", help="repeatable or comma-separated")
    ap.add_argument("--source", action="append")
    ap.add_argument("--artifact", action="append")
    ap.add_argument("--preview", action="append")
    ap.add_argument("--approval-required", action="store_true", default=None)
    ap.add_argument("--approval-id", default=None)
    ap.add_argument("--approval-status", default=None,
                    choices=["none", "pending", "approved", "rejected"])
    ap.add_argument("--compliance-status", default=None, choices=["unknown", "pass", "fail"])
    ap.add_argument("--disclosure-present", action="store_true", default=None)
    ap.add_argument("--publish-risk", default=None, choices=["internal", "external/public", "high"])
    ap.add_argument("--next-action", default=None)
    ap.add_argument("--owner", default=None)
    ap.add_argument("--telegram-summary", default=None)
    ap.add_argument("--performance-status", default=None)
    ap.add_argument("--notes", default=None)
    args = ap.parse_args()

    cards = load_board()
    existing = find(cards, args.board_id or args.content_id)

    # Base card: the existing one (merge) or a fresh default card (create).
    if existing:
        card = dict(existing)
        created = False
    else:
        card = new_card(content_id=args.content_id, board_id=args.board_id)
        created = True

    # Map of CLI value -> card field; apply only when explicitly provided (not None / not empty list).
    explicit = {
        "campaign_id": args.campaign_id, "title": args.title, "topic": args.topic,
        "status": args.status, "priority": args.priority, "content_type": args.content_type,
        "approval_id": args.approval_id, "approval_status": args.approval_status,
        "compliance_status": args.compliance_status, "publish_risk_level": args.publish_risk,
        "recommended_next_action": args.next_action, "owner_agent": args.owner,
        "telegram_summary": args.telegram_summary, "performance_check_status": args.performance_status,
        "notes": args.notes,
        "approval_required": args.approval_required, "disclosure_present": args.disclosure_present,
    }
    for k, v in explicit.items():
        if v is not None:
            card[k] = v
    for field, vals in (("platform_targets", args.platform), ("source_paths", args.source),
                        ("artifact_paths", args.artifact), ("preview_paths", args.preview)):
        if vals:  # only override the list when provided
            card[field] = _split(vals)

    card["content_id"] = args.content_id
    card["updated_at"] = _now()
    saved, _is_new = upsert(card)
    print(("CREATED " if created else "MERGED  ") + f"{saved['board_id']} · {saved['status']} · {saved['title']}")
    print(json.dumps(saved, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
