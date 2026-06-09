#!/usr/bin/env python3
"""
create_content_approval_card.py — generate a DRAFT approval card from a board item.

Reads a card from reports/content_engine/content_board.jsonl and writes a human-readable
approval card markdown to reports/content_engine/approval_cards/. The card asks Ray to make
an explicit, scoped decision (default: REVIEW / UNLISTED only). It does NOT approve anything,
does NOT enable the executor, does NOT upload, does NOT post, does NOT mark public-approved.

Generating an approval card = "authorization only" request, never execution.

Example:
  python scripts/create_content_approval_card.py --id fcf087ea \
      --scope unlisted --out reports/content_engine/approval_cards/fcf087ea_hyperframes_review_approval.md
"""
from __future__ import annotations
import argparse, sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lib.content_board import load_board, find  # noqa: E402

CARD_DIR = ROOT / "reports" / "content_engine" / "approval_cards"


def render_card(c: dict, scope: str) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%MZ")
    preview = (c.get("preview_paths") or ["(no preview)"])[0]
    platforms = ", ".join(c.get("platform_targets") or []) or "(none)"
    cid = c.get("content_id", "")
    short = cid.split("-")[0] if cid else c.get("board_id", "")

    if scope == "unlisted":
        approving = ("Permission to upload this draft as an **UNLISTED** video for private review only "
                     f"on {platforms}. Unlisted = not searchable, not public, not posted to feeds.")
        scope_status = "Approved for Unlisted"
    elif scope == "public":
        approving = f"Permission to publish this content **PUBLICLY** on {platforms}."
        scope_status = "Approved Public"
    else:  # review
        approving = ("Acknowledgement that this draft is ready for Ray's review. No upload of any kind — "
                     "this only moves the card forward in the board.")
        scope_status = "(stays Needs Ray Review until Ray chooses unlisted/public/improve)"

    return f"""# Approval Card — {c.get('title','(untitled)')}
# DRAFT REQUEST · generated {now} · board_id `{c.get('board_id')}`
# THIS CARD DOES NOT EXECUTE ANYTHING. It requests an explicit Ray decision.

## Item
- **Title:** {c.get('title','')}
- **content_id:** `{cid}`
- **Campaign:** {c.get('campaign_id','') or '(none)'}
- **Content type:** {c.get('content_type','')}
- **Platform target:** {platforms}
- **Preview path:** `{preview}`
- **Risk level:** {c.get('publish_risk_level','')}
- **Compliance:** {c.get('compliance_status','unknown')} · disclosure_present={c.get('disclosure_present')}

## What Ray is approving (scope: {scope})
{approving}

## What is explicitly NOT approved by this card
- ❌ Public posting (unless scope=public is explicitly chosen by Ray)
- ❌ Scheduling / autoposting
- ❌ Enabling `NEXUS_PUBLISH_EXECUTOR_ENABLED`
- ❌ Sending emails / newsletters
- ❌ Spending money or using paid APIs / paid tools
- ❌ Changing credentials
- ❌ Any change to `scripts/social_publish_executor.py` gates
- ❌ Touching existing v1/v2/v3/v4 videos or prior YouTube uploads

## Safety gates that remain in force
1. `social_publish_executor.py` is the ONLY upload path and is **disabled by default**
   (`NEXUS_PUBLISH_EXECUTOR_ENABLED` unset). This card does not change that.
2. Any future upload requires ALL of: this scoped approval + the executor enable flag set in a
   SEPARATE explicit step + exact `--content-id`/`--platform`/`--video` match + the file existing.
3. Approval = authorization only. It is never execution. High-risk content is never bulk-approved.
4. Drafts default to unlisted; v4 stays unlisted only; nothing is auto-public.

## Exact next command IF Ray approves (scope: {scope})
> Reviewed only — no command runs automatically. Ray (or Hermes on Ray's explicit instruction) runs:

```
# 1) record Ray's decision on the board (does NOT upload):
python scripts/content_board_update.py --id {short} --ray-approved \\
    --status "{scope_status if scope!='review' else 'Needs Ray Review'}" --approval-status approved

# 2) (UNLISTED upload only, later, separate explicit step — still gated and disabled by default)
#    Requires NEXUS_PUBLISH_EXECUTOR_ENABLED=true to be set in its own step.
python scripts/social_publish_executor.py \\
    --approval-id <APPROVAL_ID> --content-id {cid} \\
    --platform youtube --video {preview}
#    (dry-run unless --apply; refuses unless the executor is explicitly enabled)
```

## Audit message
`content_approval_card_generated · board={c.get('board_id')} · content_id={cid} · scope={scope} · `
`risk={c.get('publish_risk_level','')} · no_execution=true · executor_enabled=false · generated={now}`

---
**Recommended decision for this item:** {c.get('recommended_next_action','review and decide')}
"""


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate a draft approval card from a board item")
    ap.add_argument("--id", required=True, help="board_id or content_id (prefix ok)")
    ap.add_argument("--scope", default="review", choices=["review", "unlisted", "public"],
                    help="what the card requests (default: review — safest)")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    cards = load_board()
    c = find(cards, args.id)
    if not c:
        print(f"ERROR: no card matching '{args.id}'", file=sys.stderr)
        return 2

    md = render_card(c, args.scope)
    CARD_DIR.mkdir(parents=True, exist_ok=True)
    short = (c.get("content_id") or c.get("board_id") or "card").split("-")[0]
    out = Path(args.out) if args.out else CARD_DIR / f"{short}_content_approval_{args.scope}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(md, encoding="utf-8")
    print(f"wrote approval card: {out}")
    print(f"scope: {args.scope} · NO execution · executor stays disabled · no upload/post/schedule")
    return 0


if __name__ == "__main__":
    sys.exit(main())
