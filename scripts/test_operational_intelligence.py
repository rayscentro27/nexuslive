#!/usr/bin/env python3
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from lib import operational_intelligence as oi


def check(label: str, ok: bool) -> bool:
    print(f"{'[PASS]' if ok else '[FAIL]'} {label}")
    return ok


def main() -> int:
    ok = True
    orig_select = oi._safe_select
    rows = {
        "job_queue": [
            {"status": "pending"},
            {"status": "queued"},
            {"status": "completed"},
        ]
    }
    oi._safe_select = lambda path, timeout=8: rows.get(path.split("?")[0], [])
    try:
        snap = oi.build_operational_intelligence_snapshot(mode="detailed")
        ok &= check("operational snapshot has queue pressure", isinstance(snap.get("queue_pressure"), dict))
        ok &= check("operational snapshot has executive summary", isinstance(snap.get("executive_summary"), str))
        compact = oi.build_operational_intelligence_snapshot(mode="compact")
        ok &= check("compact mode stable", isinstance(compact.get("recommended_next_action"), str))
    finally:
        oi._safe_select = orig_select
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
