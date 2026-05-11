#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from lib.content_variant_generator import generate_content_variants, variants_as_json


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate draft-only Nexus content variants for short-form platforms."
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview variants without creating records.")
    parser.add_argument("--limit", type=int, default=None, help="Maximum number of content topics to process.")
    parser.add_argument(
        "--platform",
        type=str,
        default=None,
        help="Optional platform filter. Examples: TikTok, Instagram Reels, YouTube Shorts.",
    )
    args = parser.parse_args()

    report = generate_content_variants(
        limit=args.limit,
        dry_run=args.dry_run,
        platform=args.platform,
    )
    print(variants_as_json(report))
    return 0 if not report["generation_failures"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
