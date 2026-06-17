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
    ap = argparse.ArgumentParser(description="Reject a social queue item.")
    ap.add_argument("--item-id", required=True)
    ap.add_argument("--reason", required=True)
    args = ap.parse_args()
    item = social_queue.reject_item(args.item_id, args.reason)
    print(json.dumps(item, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
