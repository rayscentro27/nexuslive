#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lib import social_queue  # noqa: E402
from lib.social_publishers import DryRunPublisher  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Dry-run publish an approved social queue item.")
    ap.add_argument("--item-id", required=True)
    args = ap.parse_args()
    item = social_queue.find_item(args.item_id)
    if not item:
        raise SystemExit(f"queue item not found: {args.item_id}")
    if not item.get("approved_by_ray"):
        raise SystemExit("item must be approved_by_ray before dry-run publish")
    result = DryRunPublisher().publish(item)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
