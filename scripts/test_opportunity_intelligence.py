#!/usr/bin/env python3
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from lib.opportunity_intelligence import build_opportunity_intelligence_summary


def check(label: str, ok: bool) -> bool:
    print(f"{'[PASS]' if ok else '[FAIL]'} {label}")
    return ok


def main() -> int:
    ok = True
    summary = build_opportunity_intelligence_summary()
    ok &= check("opportunity intelligence review-only", summary.get("review_only") is True)
    ok &= check("opportunity requires approval", summary.get("actions_require_approval") is True)
    ok &= check("opportunity next action exists", isinstance(summary.get("opportunity_next_action"), str))
    ok &= check("opportunity categories exist", isinstance(summary.get("categories"), list) and len(summary.get("categories") or []) >= 3)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
