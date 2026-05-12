#!/usr/bin/env python3
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from lib import client_funding_intelligence as cfi


def check(label: str, ok: bool) -> bool:
    print(f"{'[PASS]' if ok else '[FAIL]'} {label}")
    return ok


def main() -> int:
    ok = True
    summary = cfi.build_client_funding_intelligence_summary()
    ok &= check("funding intelligence enabled flag", isinstance(summary.get("enabled"), bool))
    ok &= check("funding intelligence review-only", summary.get("review_only") is True)
    ok &= check("funding next action exists", isinstance(summary.get("next_best_funding_action"), str))
    ok &= check("capital ladder summary exists", isinstance(summary.get("capital_ladder_recommendation"), list))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
