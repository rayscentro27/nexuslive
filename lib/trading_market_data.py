from __future__ import annotations

import json
import math
import os
import ssl
from datetime import datetime, timezone
from typing import Any
from urllib import parse, request

from lib.trading_safety_gate import seed_safe_trading_env_from_launch_agent


def _ssl_context():
    cert_file = os.getenv("SSL_CERT_FILE", "")
    if not cert_file:
        try:
            import certifi
            cert_file = certifi.where()
        except Exception:
            cert_file = ""
    if cert_file:
        return ssl.create_default_context(cafile=cert_file)
    return None


def _headers() -> dict[str, str]:
    token = os.getenv("OANDA_ACCESS_TOKEN", "") or os.getenv("OANDA_API_KEY", "")
    return {"Authorization": f"Bearer {token}"} if token else {}


def normalize_instrument(symbol: str) -> str:
    symbol = symbol.upper()
    if "_" in symbol:
        return symbol
    if len(symbol) == 6:
        return f"{symbol[:3]}_{symbol[3:]}"
    return symbol


def normalize_symbol(symbol: str) -> str:
    return normalize_instrument(symbol).replace("_", "")


def _granularity(timeframe: str) -> str:
    return {
        "M5": "M5",
        "M15": "M15",
        "M30": "M30",
        "H1": "H1",
        "H4": "H4",
        "D1": "D",
    }.get(str(timeframe).upper(), "H1")


def fetch_oanda_candles(symbol: str, timeframe: str = "H1", lookback: int = 120) -> dict[str, Any]:
    seed_safe_trading_env_from_launch_agent()
    api_url = (os.getenv("OANDA_API_URL", "") or "").rstrip("/")
    account_id = os.getenv("OANDA_ACCOUNT_ID", "")
    token = os.getenv("OANDA_ACCESS_TOKEN", "") or os.getenv("OANDA_API_KEY", "")
    instrument = normalize_instrument(symbol)
    normalized_symbol = normalize_symbol(symbol)
    if not api_url or not account_id or not token:
        return {
            "ok": False,
            "source": "oanda_practice",
            "data_quality": "unavailable",
            "fallback_reason": "missing_oanda_env",
            "symbol": normalized_symbol,
            "instrument": instrument,
            "requested_symbol": symbol,
            "requested_timeframe": timeframe,
            "requested_candle_count": lookback,
            "candles": [],
        }
    try:
        params = parse.urlencode(
            {
                "count": max(10, min(int(lookback), 500)),
                "price": "MBA",
                "granularity": _granularity(timeframe),
            }
        )
        url = f"{api_url}/v3/instruments/{instrument}/candles?{params}"
        req = request.Request(url, headers=_headers())
        with request.urlopen(req, timeout=15, context=_ssl_context()) as resp:
            payload = json.loads(resp.read())
        candles: list[dict[str, Any]] = []
        for row in payload.get("candles", []):
            mid = row.get("mid") or {}
            bid = row.get("bid") or {}
            ask = row.get("ask") or {}
            try:
                candles.append(
                    {
                        "time": row.get("time"),
                        "open": float(mid.get("o") or bid.get("o") or ask.get("o")),
                        "high": float(mid.get("h") or bid.get("h") or ask.get("h")),
                        "low": float(mid.get("l") or bid.get("l") or ask.get("l")),
                        "close": float(mid.get("c") or bid.get("c") or ask.get("c")),
                        "volume": int(row.get("volume") or 0),
                        "complete": bool(row.get("complete")),
                    }
                )
            except Exception:
                continue
        if not candles:
            return {
                "ok": False,
                "source": "oanda_practice",
                "data_quality": "unavailable",
                "fallback_reason": "no_candles_returned",
                "symbol": normalized_symbol,
                "instrument": instrument,
                "requested_symbol": symbol,
                "requested_timeframe": timeframe,
                "requested_candle_count": lookback,
                "candles": [],
            }
        return {
            "ok": True,
            "source": "oanda_practice",
            "data_quality": "oanda_practice_market_data",
            "symbol": normalized_symbol,
            "instrument": instrument,
            "requested_symbol": symbol,
            "timeframe": timeframe,
            "requested_timeframe": timeframe,
            "candle_count": len(candles),
            "requested_candle_count": lookback,
            "date_range": {"start": candles[0]["time"], "end": candles[-1]["time"]},
            "candles": candles,
        }
    except Exception as exc:
        return {
            "ok": False,
            "source": "oanda_practice",
            "data_quality": "unavailable",
            "fallback_reason": str(exc),
            "symbol": normalized_symbol,
            "instrument": instrument,
            "requested_symbol": symbol,
            "requested_timeframe": timeframe,
            "requested_candle_count": lookback,
            "candles": [],
        }


def _fallback_candles(symbol: str, timeframe: str, lookback: int) -> dict[str, Any]:
    normalized_symbol = normalize_symbol(symbol)
    if normalized_symbol.startswith("EURUSD"):
        base = 1.10
    elif normalized_symbol.startswith("USDJPY"):
        base = 149.0
    elif normalized_symbol.startswith("GBPUSD"):
        base = 1.27
    else:
        base = 1.25
    candles = []
    for idx in range(max(20, lookback)):
        angle = idx / 6.0
        drift = math.sin(angle) * 0.002
        open_ = base + drift
        close = base + math.sin(angle + 0.4) * 0.002
        high = max(open_, close) + 0.001
        low = min(open_, close) - 0.001
        candles.append(
            {
                "time": f"sample-{idx}",
                "open": round(open_, 6),
                "high": round(high, 6),
                "low": round(low, 6),
                "close": round(close, 6),
                "volume": 100 + idx,
                "complete": True,
            }
        )
    return {
        "ok": True,
        "source": "fallback_sample",
        "data_quality": "sample",
        "symbol": normalized_symbol,
        "instrument": normalize_instrument(symbol),
        "requested_symbol": symbol,
        "timeframe": timeframe,
        "requested_timeframe": timeframe,
        "candle_count": len(candles),
        "requested_candle_count": lookback,
        "date_range": {"start": candles[0]["time"], "end": candles[-1]["time"]},
        "candles": candles,
        "fallback_reason": "practice_market_data_unavailable",
    }


def get_market_data_bundle(symbol: str, timeframe: str = "H1", lookback: int = 120, source: str = "auto") -> dict[str, Any]:
    if source in {"auto", "oanda_practice"}:
        oanda = fetch_oanda_candles(symbol, timeframe=timeframe, lookback=lookback)
        if oanda.get("ok"):
            return oanda
        if source == "oanda_practice":
            return oanda
    return _fallback_candles(symbol, timeframe, lookback)


def resolve_market_data_bundle(
    symbol: str,
    *,
    timeframe: str = "H1",
    lookback: int = 120,
    preferred_source: str = "auto",
    allow_fallback: bool = True,
) -> dict[str, Any]:
    bundle = get_market_data_bundle(symbol, timeframe=timeframe, lookback=lookback, source=preferred_source)
    if bundle.get("ok") or not allow_fallback or preferred_source != "oanda_practice":
        return bundle
    fallback = _fallback_candles(symbol, timeframe, lookback)
    fallback["requested_source"] = preferred_source
    fallback["fallback_reason"] = bundle.get("fallback_reason") or "oanda_practice_unavailable"
    fallback["upstream_source"] = bundle.get("source")
    fallback["upstream_data_quality"] = bundle.get("data_quality")
    return fallback


def generate_strategy_signals_from_candles(strategy_id: str, symbol: str, timeframe: str, candles: list[dict[str, Any]], limit: int = 8) -> list[dict[str, Any]]:
    strategy_id = str(strategy_id or "").lower()
    rows: list[dict[str, Any]] = []
    normalized_symbol = normalize_symbol(symbol)
    pip = 0.0001 if "JPY" not in normalized_symbol else 0.01
    for idx in range(3, max(3, len(candles) - 1)):
        prev3 = candles[idx - 3]
        prev2 = candles[idx - 2]
        prev = candles[idx - 1]
        cur = candles[idx]
        nxt = candles[idx + 1] if idx + 1 < len(candles) else cur
        action = None
        stop = None
        recent_high = max(prev3["high"], prev2["high"], prev["high"])
        recent_low = min(prev3["low"], prev2["low"], prev["low"])
        avg_prev_range = max(
            pip,
            ((prev["high"] - prev["low"]) + (prev2["high"] - prev2["low"]) + (prev3["high"] - prev3["low"])) / 3.0,
        )
        cur_range = max(pip, cur["high"] - cur["low"])

        if "mean_reversion" in strategy_id:
            rolling_mean = (prev3["close"] + prev2["close"] + prev["close"]) / 3.0
            deviation = cur["close"] - rolling_mean
            threshold = avg_prev_range * 0.65
            if deviation > threshold:
                action = "SELL"
                stop = cur["high"] + (avg_prev_range * 0.35)
            elif deviation < -threshold:
                action = "BUY"
                stop = cur["low"] - (avg_prev_range * 0.35)
        elif "london_breakout" in strategy_id or "session_breakout" in strategy_id:
            high_trigger = prev["high"]
            low_trigger = prev["low"]
            if "wider" in strategy_id or "session" in strategy_id:
                high_trigger = recent_high
                low_trigger = recent_low
            buffer = 0.0
            if "tighter" in strategy_id:
                buffer = -avg_prev_range * 0.10
            elif "wider" in strategy_id:
                buffer = avg_prev_range * 0.05
            elif "session_breakout" in strategy_id:
                buffer = -avg_prev_range * 0.05
            breakout_up = cur["high"] >= high_trigger + buffer and cur["close"] >= prev["close"]
            breakout_down = cur["low"] <= low_trigger - buffer and cur["close"] <= prev["close"]
            if "volatility" in strategy_id:
                if cur_range < avg_prev_range * 1.05:
                    breakout_up = False
                    breakout_down = False
            if breakout_up:
                action = "BUY"
                stop = min(prev["low"], prev2["low"], prev3["low"])
            elif breakout_down:
                action = "SELL"
                stop = max(prev["high"], prev2["high"], prev3["high"])
        elif "trend_pullback" in strategy_id:
            trend_lookback = 2 if "short" in strategy_id else 3 if "long" in strategy_id else 2
            recent_closes = [candles[idx - offset]["close"] for offset in range(trend_lookback, 0, -1)]
            rising = all(a < b for a, b in zip(recent_closes, recent_closes[1:]))
            falling = all(a > b for a, b in zip(recent_closes, recent_closes[1:]))
            shallow_pullback = cur["low"] <= prev["low"] or cur["close"] <= prev["close"]
            if "short" in strategy_id:
                shallow_pullback = shallow_pullback or cur["low"] <= ((prev["low"] + prev2["low"]) / 2.0)
            rebound = nxt["close"] >= cur["close"] or ("short" in strategy_id and nxt["high"] >= cur["high"])
            if rising and shallow_pullback and rebound:
                action = "BUY"
                stop = min(cur["low"], prev["low"], prev2["low"])
            elif falling and (cur["high"] >= prev["high"] or cur["close"] >= prev["close"]) and nxt["close"] <= cur["close"]:
                action = "SELL"
                stop = max(cur["high"], prev["high"], prev2["high"])
        elif "trend_following" in strategy_id or "momentum_continuation" in strategy_id:
            if cur["close"] > prev["close"] > prev2["close"] and cur["high"] >= recent_high:
                action = "BUY"
                stop = min(cur["low"], prev["low"])
            elif cur["close"] < prev["close"] < prev2["close"] and cur["low"] <= recent_low:
                action = "SELL"
                stop = max(cur["high"], prev["high"])
        if not action or stop is None:
            continue
        entry = cur["close"]
        risk = abs(entry - stop)
        if risk <= 0:
            continue
        target = entry + (risk * 2.0 if action == "BUY" else -risk * 2.0)
        exit_price = nxt["close"]
        if action == "BUY":
            if nxt["low"] <= stop:
                exit_price = stop
            elif nxt["high"] >= target:
                exit_price = target
        else:
            if nxt["high"] >= stop:
                exit_price = stop
            elif nxt["low"] <= target:
                exit_price = target
        rows.append(
            {
                "symbol": symbol,
                "action": action,
                "entry_price": round(entry, 6),
                "stop_loss": round(stop, 6),
                "take_profit": round(target, 6),
                "exit_price": round(exit_price, 6),
                "timestamp": cur["time"],
                "position_size": 0.01,
                "timeframe": timeframe,
            }
        )
        if len(rows) >= limit:
            break
    return rows
