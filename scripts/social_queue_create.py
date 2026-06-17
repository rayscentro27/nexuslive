#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lib import social_queue  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Create a local social queue item.")
    ap.add_argument("--platform", required=True, choices=sorted(social_queue.VALID_PLATFORMS))
    ap.add_argument("--channel", default="")
    ap.add_argument("--offer", default="Credit/Funding Readiness Starter Review - $97")
    ap.add_argument("--title", required=True)
    ap.add_argument("--caption", required=True)
    ap.add_argument("--content-path", required=True)
    ap.add_argument("--media-path", default="")
    ap.add_argument("--cta", required=True)
    ap.add_argument("--source", default="manual")
    ap.add_argument("--source-report", default="")
    ap.add_argument("--scheduled-for", default="")
    args = ap.parse_args()
    item = social_queue.create_item(
        platform=args.platform,
        channel=args.channel,
        offer=args.offer,
        title=args.title,
        caption=args.caption,
        content_path=args.content_path,
        media_path=args.media_path,
        cta=args.cta,
        source=args.source,
        source_report=args.source_report,
        scheduled_for=args.scheduled_for,
    )
    print(json.dumps(item, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
