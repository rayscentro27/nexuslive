#!/usr/bin/env python3
"""
Notify Ray (only) about new reviewable showroom assets.

- Composes a Telegram message: count + titles/types/ids, showroom path, top
  recommended review item, and feedback instructions.
- Default is --dry-run (preview only, nothing sent).
- --send performs a MANUAL Ray-only send (to TELEGRAM_CHAT_ID) via the free
  Telegram Bot API. Honors the safety flags; never sends to anyone else.

No external users, no public posts, no email, no paid APIs, no secrets printed.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lib import showroom_assets as SA  # noqa: E402

PREVIEW = ROOT / "logs" / "showroom_notification_preview_latest.md"
SHOWROOM = "reports/showroom/latest_results_showroom.md"


def _load_env() -> None:
    p = ROOT / ".env"
    if p.exists():
        for line in p.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())


def compose() -> tuple[str, list[dict]]:
    pending = [a for a in SA.recent(50) if a.get("status") in ("new", "needs_review")]
    blockers = []
    postiz_status = ROOT / "reports" / "showroom" / "postiz_status.md"
    hyperframes_status = ROOT / "reports" / "showroom" / "hyperframes_status.md"
    if not postiz_status.exists():
        blockers.append("Postiz status not generated")
    if not hyperframes_status.exists():
        blockers.append("HyperFrames status not generated")
    n = len(pending)
    if n == 0:
        msg = ("Nexus showroom: no new reviewable assets right now.\n"
               f"View: {SHOWROOM}")
        return msg, pending
    lines = [f"Nexus created {n} reviewable asset(s):"]
    for i, a in enumerate(pending[:10], 1):
        lines.append(f"{i}. {a['asset_type']}: {a['asset_id']} — {a['title'][:60]}")
    top = pending[0]
    lines += [
        "", f"View:\n{SHOWROOM}", "",
        "Reply / use:",
        f'  revise {top["asset_id"]} — make the hook stronger',
        f'  approve {pending[min(1,n-1)]["asset_id"]}',
        f'  notes {pending[min(2,n-1)]["asset_id"]} — improve CTA',
        "",
        "CLI feedback:",
        f'  python3 scripts/review_showroom_asset.py --asset-id {top["asset_id"]} '
        f'--status revise --feedback "..."',
        "",
        f"Urgent blockers: {', '.join(blockers) if blockers else 'none'}",
    ]
    return "\n".join(lines), pending


def telegram_send(text: str) -> tuple[bool, str]:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat = os.getenv("TELEGRAM_CHAT_ID", "").strip()  # Ray's chat only
    enabled = os.getenv("TELEGRAM_ENABLED", "false").strip().lower() == "true"
    manual_only = os.getenv("TELEGRAM_MANUAL_ONLY", "false").strip().lower() == "true"
    if not enabled:
        return False, "TELEGRAM_ENABLED is not true"
    if not token or not chat:
        return False, "TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID missing"
    # --send IS the manual trigger; manual_only permits it. (Auto/cron path is blocked elsewhere.)
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = urllib.parse.urlencode({"chat_id": chat, "text": text,
                                   "disable_web_page_preview": "true"}).encode()
    try:
        with urllib.request.urlopen(urllib.request.Request(url, data=data), timeout=12) as r:
            ok = json.loads(r.read()).get("ok", False)
            return (ok, "sent to Ray (TELEGRAM_CHAT_ID)" if ok else "telegram API returned ok=false")
    except Exception as e:
        return False, f"send failed: {str(e)[:80]}"


def main() -> int:
    ap = argparse.ArgumentParser(description="Notify Ray (only) about new showroom assets.")
    ap.add_argument("--dry-run", action="store_true", help="preview only (default if --send not given)")
    ap.add_argument("--send", action="store_true", help="MANUAL Ray-only send via Telegram")
    args = ap.parse_args()
    _load_env()

    text, pending = compose()
    PREVIEW.parent.mkdir(parents=True, exist_ok=True)
    PREVIEW.write_text(f"# Showroom notification preview\n_{datetime.now(timezone.utc).isoformat()}_\n\n"
                       f"```\n{text}\n```\n")
    print("----- MESSAGE PREVIEW (Ray-only) -----")
    print(text)
    print("--------------------------------------")
    print(f"pending reviewable assets: {len(pending)} · preview: {PREVIEW.relative_to(ROOT)}")

    if args.send and not args.dry_run:
        ok, why = telegram_send(text)
        print(f"SEND: {'✓ ' if ok else '✗ '}{why}")
        return 0 if ok else 2
    print("DRY-RUN: nothing sent. Re-run with --send for a manual Ray-only notification.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
