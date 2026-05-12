#!/usr/bin/env python3
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from lib.trading_intelligence_lab import build_trading_intelligence_report


def check(label: str, ok: bool) -> bool:
    print(f"{'[PASS]' if ok else '[FAIL]'} {label}")
    return ok


def main() -> int:
    ok = True
    report = build_trading_intelligence_report()
    names = {s.get("strategy_name") for s in (report.get("strategy_templates") or [])}
    ok &= check("trading live execution remains disabled", report.get("trading_live_execution_enabled") is False)
    ok &= check("paper-only enabled", report.get("trading_paper_only") is True)
    ok &= check("launch strategy london breakout present", "London Breakout" in names)
    ok &= check("launch strategy spy continuation present", "SPY Trend Continuation" in names)
    ok &= check("launch strategy btc eth structure present", "BTC/ETH Trend Structure" in names)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
