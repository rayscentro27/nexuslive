#!/usr/bin/env python3
"""
content_board_digest.py — build a Telegram-ready digest from the Content Board.

Reads reports/content_engine/content_board.jsonl and writes a digest markdown to
reports/content_engine/telegram_digests/content_engine_digest_latest.md (+ a timestamped copy).

By DEFAULT it only writes the file. With --send it attempts a Telegram send that REUSES the
existing, gated path: it sends ONLY if TELEGRAM_AUTO_REPORTS_ENABLED=true and a bot token +
chat id are set in the environment. It never prints secrets, never uploads content, never posts
to social platforms — it is a status notification to Ray's own chat.

No DB, no paid API, no publishing of content. Safe to run repeatedly.
"""
from __future__ import annotations
import argparse, os, sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lib.content_board import (  # noqa: E402
    load_board, counts_by_status, STATUSES, RAY_REVIEW_STATUSES,
)

DIGEST_DIR = ROOT / "reports" / "content_engine" / "telegram_digests"


def build_digest(cards: list[dict]) -> tuple[str, str]:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%MZ")
    counts = counts_by_status(cards)
    total = len(cards)
    review = [c for c in cards if c.get("status") in RAY_REVIEW_STATUSES]

    # top recommended next action = highest-priority review item, else any review item
    pri = {"high": 0, "normal": 1, "low": 2}
    review_sorted = sorted(review, key=lambda c: pri.get(c.get("priority", "normal"), 1))
    top = review_sorted[0] if review_sorted else None

    lines = [f"📋 *Nexus Content Engine — Board Digest* ({now})", ""]
    lines.append(f"*Cards:* {total} total")
    for s in STATUSES:
        if counts.get(s):
            lines.append(f"  • {s}: {counts[s]}")
    lines.append("")
    lines.append(f"*Needs Ray Review:* {len(review)}")
    for c in review_sorted:
        prev = (c.get("preview_paths") or ["(no preview)"])[0]
        lines.append(f"  • `{c.get('board_id')}` — {c.get('title')} "
                     f"[{c.get('publish_risk_level')}]")
        lines.append(f"      preview: {prev}")
        if c.get("recommended_next_action"):
            lines.append(f"      next: {c['recommended_next_action']}")
    lines.append("")
    if top:
        lines.append(f"*Top next action:* {top.get('title')} — {top.get('recommended_next_action') or 'review and decide'}")
    else:
        lines.append("*Top next action:* none waiting on Ray.")
    lines.append("")
    lines.append("*Safety:* no upload · no post · no schedule · executor disabled · "
                 "no paid APIs · no publish actions taken.")

    md = "\n".join(lines)
    # plain text variant for the file header context
    return md, now


def maybe_send(md: str) -> dict:
    """Reuse the existing gated Telegram path. Sends ONLY if explicitly enabled."""
    enabled = os.getenv("TELEGRAM_AUTO_REPORTS_ENABLED", "false").lower() == "true"
    if not enabled:
        return {"sent": False, "reason": "TELEGRAM_AUTO_REPORTS_ENABLED!=true (no send)"}
    token = os.getenv("HERMES_BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CHAT_ID") or os.getenv("HERMES_CHAT_ID", "")
    if not (token and chat_id):
        return {"sent": False, "reason": "bot token or chat id not set"}
    try:
        import requests
        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": md, "parse_mode": "Markdown"},
            timeout=15,
        ).json()
        return {"sent": bool(r.get("ok")), "message_id": r.get("result", {}).get("message_id")}
    except Exception as exc:  # never raise; never print secrets
        return {"sent": False, "reason": f"send error: {type(exc).__name__}"}


def main() -> int:
    ap = argparse.ArgumentParser(description="Build (and optionally send) the Content Board digest")
    ap.add_argument("--send", action="store_true", help="attempt gated Telegram send (default: write file only)")
    args = ap.parse_args()

    cards = load_board()
    md, now = build_digest(cards)
    DIGEST_DIR.mkdir(parents=True, exist_ok=True)
    latest = DIGEST_DIR / "content_engine_digest_latest.md"
    stamp = DIGEST_DIR / f"content_engine_digest_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.md"
    latest.write_text(md + "\n", encoding="utf-8")
    stamp.write_text(md + "\n", encoding="utf-8")
    print(md)
    print("\n---")
    print(f"written: {latest}")
    if args.send:
        result = maybe_send(md)
        print(f"telegram: {result}")
    else:
        print("telegram: not sent (default). Pass --send to attempt the gated send.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
