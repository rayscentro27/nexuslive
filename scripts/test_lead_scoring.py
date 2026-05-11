#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from lib.lead_scoring import score_lead


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    sample = score_lead({
        "credit_readiness": 52,
        "business_readiness": 61,
        "funding_intent": 78,
        "engagement_level": 55,
        "subscription_likelihood": 49,
        "commission_opportunity": 33,
        "compliance_sensitivity": 20,
    })
    print(json.dumps({"dry_run": args.dry_run, "sample": sample}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
