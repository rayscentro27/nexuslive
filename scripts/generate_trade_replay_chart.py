#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib.trading_fallback_logger import latest_jsonl
from lib.trading_market_data import resolve_market_data_bundle
from lib.trading_visuals import render_dashboard_html, render_trade_replay_html


CHART_DIR = ROOT / "logs" / "charts"
LATEST_REPLAY = CHART_DIR / "trade_replay_latest.html"
LATEST_DASHBOARD = CHART_DIR / "trading_dashboard_latest.html"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text())
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _latest_context() -> dict[str, Any]:
    trades = latest_jsonl("trades", limit=20)
    latest_trade = trades[-1] if trades else {}
    watch = _load_json(ROOT / "logs" / "live_watch" / "trading_watch_session_latest.json")
    tournament = _load_json(ROOT / "logs" / "nexus_trading_tournament_latest.json")
    top = tournament.get("top_strategy") or tournament.get("top_candidate_for_next_cap_reset") or {}
    signal = latest_trade.get("signal") or {}
    symbol = str(latest_trade.get("symbol") or signal.get("symbol") or top.get("symbol") or "USDJPY").upper().replace("_", "")
    strategy_id = str(latest_trade.get("strategy_id") or signal.get("strategy_id") or top.get("strategy_id") or "unknown")
    timeframe = str(signal.get("timeframe") or top.get("timeframe") or "M15")
    return {
        "trade": latest_trade,
        "watch": watch,
        "tournament": tournament,
        "symbol": symbol,
        "strategy_id": strategy_id,
        "timeframe": timeframe,
    }


def _infer_family(strategy_id: str) -> str:
    text = strategy_id.lower()
    if "breakout" in text:
        return "breakout"
    if "pullback" in text:
        return "trend_following"
    if "mean_reversion" in text:
        return "mean_reversion"
    return "technical_indicator"


def _infer_trigger(strategy_id: str) -> str:
    return "scheduled_session" if "breakout" in strategy_id.lower() else "continuous_indicator"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--latest", action="store_true")
    parser.add_argument("--symbol", default="")
    parser.add_argument("--strategy-id", default="")
    parser.add_argument("--trade-id", default="")
    parser.add_argument("--session-id", default="")
    parser.add_argument("--data-source", choices=("auto", "oanda_practice", "fallback_sample"), default="auto")
    args = parser.parse_args()
    CHART_DIR.mkdir(parents=True, exist_ok=True)
    context = _latest_context()
    symbol = (args.symbol or context["symbol"]).upper().replace("_", "")
    strategy_id = args.strategy_id or context["strategy_id"]
    timeframe = context["timeframe"]
    preferred_source = "fallback_sample" if args.data_source == "fallback_sample" else args.data_source
    market = resolve_market_data_bundle(
        symbol,
        timeframe=timeframe,
        lookback=96,
        preferred_source=preferred_source,
        allow_fallback=True,
    )
    trade = context["trade"]
    signal = trade.get("signal") or {}
    watch = context["watch"]
    last_check = (watch.get("strategy_checks") or [{}])[-1] if watch else {}
    session_window = watch.get("session_name") if watch else None
    trade_or_order_id = trade.get("trade_id") or signal.get("trade_id") or signal.get("order_id") or trade.get("order_id")
    payload = {
        "generated_at": _now(),
        "symbol": symbol,
        "strategy_id": strategy_id,
        "strategy_family": _infer_family(strategy_id),
        "trigger_type": _infer_trigger(strategy_id),
        "status": trade.get("status") or ("rejected" if last_check and not last_check.get("setup_detected") else "open"),
        "reason": trade.get("reason") or last_check.get("reason") or last_check.get("rejection_reason") or "latest_trade_replay",
        "rejection_reason": last_check.get("rejection_reason"),
        "entry_price": signal.get("entry_price") or trade.get("entry_price") or last_check.get("entry_price"),
        "exit_price": trade.get("exit_price") or last_check.get("exit_price"),
        "stop_loss": signal.get("stop_loss") or trade.get("stop_loss") or last_check.get("stop_loss"),
        "take_profit": signal.get("take_profit") or trade.get("take_profit") or last_check.get("take_profit"),
        "data_source": market.get("source"),
        "data_quality": market.get("data_quality"),
        "fallback_reason": market.get("fallback_reason"),
        "trade_or_order_id": trade_or_order_id,
        "session_window": session_window,
        "candles": market.get("candles") or [],
    }
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    specific = CHART_DIR / f"{symbol}_{strategy_id}_{stamp}.html"
    html = render_trade_replay_html(payload)
    specific.write_text(html)
    LATEST_REPLAY.write_text(html)
    dashboard = render_dashboard_html(
        {
            "rows": [
                {"label": "Latest replay symbol", "value": symbol},
                {"label": "Latest replay strategy", "value": strategy_id},
                {"label": "Replay status", "value": payload["status"]},
                {"label": "Replay data quality", "value": payload["data_quality"]},
                {"label": "Replay data source", "value": payload["data_source"]},
                {"label": "Replay fallback reason", "value": payload.get("fallback_reason") or "none"},
                {"label": "Latest watch file", "value": "logs/live_watch/trading_watch_session_latest.json"},
            ],
            "links": [
                {"label": "Latest replay chart", "href": "trade_replay_latest.html"},
                {"label": "Latest live watch dashboard", "href": "live_watch_dashboard_latest.html"},
            ],
        }
    )
    LATEST_DASHBOARD.write_text(dashboard)
    print(json.dumps({"latest_replay": str(LATEST_REPLAY), "specific_replay": str(specific), "dashboard": str(LATEST_DASHBOARD), "payload": payload}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
