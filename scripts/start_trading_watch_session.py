#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib.trading_live_watch import run_watch_session


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--session", required=True, choices=("new_york_open", "london_open", "tokyo_open", "news_event", "continuous_indicator"))
    parser.add_argument("--symbols", required=True)
    parser.add_argument("--mode", choices=("paper",), default="paper")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--timeframe", default="M15")
    parser.add_argument("--candles", type=int, default=96)
    parser.add_argument("--data-source", choices=("auto", "oanda_practice", "fallback_sample"), default="auto")
    parser.add_argument("--refresh-seconds", type=int, default=0)
    parser.add_argument("--duration-minutes", type=int, default=0)
    args = parser.parse_args()
    payload = run_watch_session(
        session_name=args.session,
        symbols=[part.strip().upper() for part in args.symbols.split(",") if part.strip()],
        mode=args.mode,
        execute=args.execute,
        dry_run=args.dry_run or not args.execute,
        timeframe=args.timeframe,
        candle_count=args.candles,
        data_source=args.data_source,
        refresh_seconds=args.refresh_seconds,
        duration_minutes=args.duration_minutes,
    )
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
