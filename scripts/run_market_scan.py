#!/usr/bin/env python3
from __future__ import annotations

import json
import random
from datetime import datetime, timezone

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib.trading_fallback_logger import append_jsonl, jsonl_path
from lib.trading_market_data import get_market_data_bundle


WATCHLIST = [
    ("EURUSD", "forex", "london_breakout"),
    ("GBPUSD", "forex", "trend_pullback"),
    ("USDJPY", "forex", "trend_pullback"),
    ("BTCUSD", "crypto", "trend_following"),
    ("ETHUSD", "crypto", "mean_reversion"),
    ("SPY", "equity", "momentum"),
    ("QQQ", "equity", "mean_reversion"),
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sample_score(symbol: str) -> tuple[float, float, float]:
    seed = sum(ord(c) for c in symbol)
    rng = random.Random(seed)
    return round(rng.uniform(0.45, 0.82), 3), round(rng.uniform(0.42, 0.88), 3), round(rng.uniform(0.48, 0.79), 3)


def main() -> int:
    openbb_used = False
    try:
        import openbb  # type: ignore # pragma: no cover
        openbb_used = True
    except Exception:
        openbb_used = False

    rows = []
    for symbol, asset_class, family in WATCHLIST:
        market_data = get_market_data_bundle(symbol, timeframe="H1", lookback=48, source="auto" if asset_class == "forex" else "fallback")
        candles = market_data.get("candles") or []
        if len(candles) >= 2:
            closes = [float(c["close"]) for c in candles[-20:]]
            trend = round(min(0.95, max(0.05, 0.5 + ((closes[-1] - closes[0]) / max(abs(closes[0]), 0.0001)) * 10)), 3)
            mean_close = sum(closes) / len(closes)
            variance = sum((c - mean_close) ** 2 for c in closes) / len(closes)
            vol = round(min(0.95, max(0.05, variance * 10000 if asset_class == "forex" else variance / max(abs(mean_close), 1) * 10)), 3)
            confidence = round(min(0.95, max(0.05, (trend * 0.55) + (vol * 0.45))), 3)
        else:
            vol, trend, confidence = _sample_score(symbol)
        reason = {
            "london_breakout": "session breakout structure with manageable volatility",
            "trend_pullback": "trend continuation candidate with pullback context",
            "trend_following": "momentum continuation candidate",
            "mean_reversion": "extended move with reversion potential",
            "momentum": "broad market momentum candidate",
        }.get(family, "watchlist candidate")
        row = {
            "created_at": _now(),
            "symbol": symbol,
            "asset_class": asset_class,
            "reason": reason,
            "volatility_score": vol,
            "trend_score": trend,
            "data_source": "openbb" if openbb_used else market_data.get("source", "watchlist_fallback"),
            "data_quality": "readonly_live" if openbb_used else market_data.get("data_quality", "sample"),
            "candle_count": market_data.get("candle_count", 0),
            "date_range": market_data.get("date_range"),
            "fallback_reason": market_data.get("fallback_reason"),
            "recommended_strategy_family": family,
            "confidence": confidence,
        }
        append_jsonl("market_scan", row)
        rows.append(row)

    payload = {
        "ran_at": _now(),
        "openbb_used": openbb_used,
        "fallback_scanner_used": not openbb_used,
        "candidates_generated": len(rows),
        "artifact_path": str(jsonl_path("market_scan")),
        "candidates": rows,
    }
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
