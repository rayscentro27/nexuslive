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
    ap = argparse.ArgumentParser(description="Approve a social queue item without publishing it.")
    ap.add_argument("--item-id", required=True)
    ap.add_argument("--ray-approved", action="store_true", help="required explicit approval flag")
    args = ap.parse_args()
    item = social_queue.approve_item(args.item_id, ray_approved=args.ray_approved)
    print(json.dumps(item, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
