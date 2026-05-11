#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from lib.onboarding_optimizer import evaluate_onboarding


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    sample = evaluate_onboarding([
        "signup completed",
        "email verified",
        "profile started",
        "business setup started",
    ])
    print(json.dumps({"dry_run": args.dry_run, "sample": sample}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
