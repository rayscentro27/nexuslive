#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from lib.hook_generator import generate_hooks


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    print(json.dumps({
        "dry_run": args.dry_run,
        "topic": "business credit timing",
        "hooks": generate_hooks("business credit timing", count=10),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
