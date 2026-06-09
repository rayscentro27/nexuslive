#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "trading-engine"))
sys.path.insert(0, str(ROOT))

from backtest.backtester import Backtester
from lib.trading_fallback_logger import append_jsonl
from lib.trading_market_data import generate_strategy_signals_from_candles, get_market_data_bundle
from lib.trading_safety_gate import evaluate_trading_safety
from hermes_supabase_strategy_search import search_candidates


STATUS_FILE = ROOT / "logs" / "trading_engine_status.json"
TOURNAMENT_FILE = ROOT / "logs" / "nexus_trading_tournament_latest.json"
RECEIVER_URL = "http://127.0.0.1:5000/signal"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _strategy_samples() -> list[dict[str, Any]]:
    return [
        {
            "strategy_id": "eurusd_london_breakout",
            "strategy_name": "EURUSD London Breakout paper strategy",
            "symbol": "EURUSD",
            "asset_class": "forex",
            "data_quality": "sample",
            "recommended_signal": {
                "symbol": "EURUSD",
                "action": "BUY",
                "entry_price": 1.1012,
                "stop_loss": 1.0972,
                "take_profit": 1.1098,
                "timeframe": "H1",
                "strategy": "eurusd_london_breakout",
                "confidence": 78,
            },
            "signals": [
                {"symbol": "EURUSD", "action": "BUY", "entry_price": 1.0950, "stop_loss": 1.0910, "take_profit": 1.1030, "exit_price": 1.1030, "timestamp": "2026-06-01T07:00:00", "position_size": 0.01},
                {"symbol": "EURUSD", "action": "BUY", "entry_price": 1.0975, "stop_loss": 1.0935, "take_profit": 1.1055, "exit_price": 1.1015, "timestamp": "2026-06-02T07:00:00", "position_size": 0.01},
                {"symbol": "EURUSD", "action": "SELL", "entry_price": 1.1040, "stop_loss": 1.1080, "take_profit": 1.0960, "exit_price": 1.0960, "timestamp": "2026-06-03T07:00:00", "position_size": 0.01},
                {"symbol": "EURUSD", "action": "BUY", "entry_price": 1.1000, "stop_loss": 1.0960, "take_profit": 1.1080, "exit_price": 1.0960, "timestamp": "2026-06-04T07:00:00", "position_size": 0.01},
                {"symbol": "EURUSD", "action": "BUY", "entry_price": 1.0990, "stop_loss": 1.0950, "take_profit": 1.1070, "exit_price": 1.1070, "timestamp": "2026-06-05T07:00:00", "position_size": 0.01},
            ],
        },
        {
            "strategy_id": "usdjpy_trend_pullback",
            "strategy_name": "USDJPY Trend Pullback paper strategy",
            "symbol": "USDJPY",
            "asset_class": "forex",
            "data_quality": "sample",
            "recommended_signal": {
                "symbol": "USDJPY",
                "action": "BUY",
                "entry_price": 149.20,
                "stop_loss": 148.80,
                "take_profit": 150.00,
                "timeframe": "H1",
                "strategy": "usdjpy_trend_pullback",
                "confidence": 72,
            },
            "signals": [
                {"symbol": "USDJPY", "action": "BUY", "entry_price": 148.60, "stop_loss": 148.10, "take_profit": 149.60, "exit_price": 149.00, "timestamp": "2026-06-01T10:00:00", "position_size": 0.01},
                {"symbol": "USDJPY", "action": "BUY", "entry_price": 149.10, "stop_loss": 148.70, "take_profit": 149.90, "exit_price": 149.90, "timestamp": "2026-06-02T10:00:00", "position_size": 0.01},
                {"symbol": "USDJPY", "action": "SELL", "entry_price": 149.80, "stop_loss": 150.20, "take_profit": 149.00, "exit_price": 150.20, "timestamp": "2026-06-03T10:00:00", "position_size": 0.01},
                {"symbol": "USDJPY", "action": "BUY", "entry_price": 149.40, "stop_loss": 149.00, "take_profit": 150.20, "exit_price": 149.60, "timestamp": "2026-06-04T10:00:00", "position_size": 0.01},
            ],
        },
        {
            "strategy_id": "btcusd_trend_following",
            "strategy_name": "BTC Trend Following local paper strategy",
            "symbol": "BTCUSD",
            "asset_class": "crypto",
            "data_quality": "sample",
            "recommended_signal": {
                "symbol": "BTCUSD",
                "action": "BUY",
                "entry_price": 68400.0,
                "stop_loss": 67100.0,
                "take_profit": 70800.0,
                "timeframe": "H1",
                "strategy": "btcusd_trend_following",
                "confidence": 69,
            },
            "signals": [
                {"symbol": "BTCUSD", "action": "BUY", "entry_price": 65000.0, "stop_loss": 64000.0, "take_profit": 67000.0, "exit_price": 66000.0, "timestamp": "2026-06-01T12:00:00", "position_size": 0.01},
                {"symbol": "BTCUSD", "action": "BUY", "entry_price": 66200.0, "stop_loss": 65200.0, "take_profit": 68200.0, "exit_price": 65200.0, "timestamp": "2026-06-02T12:00:00", "position_size": 0.01},
                {"symbol": "BTCUSD", "action": "SELL", "entry_price": 67000.0, "stop_loss": 68000.0, "take_profit": 65000.0, "exit_price": 65000.0, "timestamp": "2026-06-03T12:00:00", "position_size": 0.01},
                {"symbol": "BTCUSD", "action": "BUY", "entry_price": 67500.0, "stop_loss": 66500.0, "take_profit": 69500.0, "exit_price": 68500.0, "timestamp": "2026-06-04T12:00:00", "position_size": 0.01},
            ],
        },
    ]


def _load_supabase_first_strategies(limit: int = 20, symbols: set[str] | None = None) -> list[dict[str, Any]]:
    sample_map = {row["strategy_id"]: row for row in _strategy_samples()}
    payload = search_candidates(asset_class="all", limit=limit)
    rows = payload.get("candidates") or []
    strategies: list[dict[str, Any]] = []
    for row in rows:
        row_symbol = str(row.get("symbol") or "").upper()
        if symbols and row_symbol not in symbols:
            continue
        sample = sample_map.get(str(row.get("strategy_id") or ""))
        signal = dict(row.get("recommended_signal") or {})
        signal.setdefault("strategy", row.get("strategy_id"))
        signal.setdefault("strategy_id", row.get("strategy_id"))
        signal.setdefault("asset_class", row.get("asset_class"))
        signal.setdefault("position_size", 0.01)
        signal.setdefault("units", 1)
        if sample:
            signal.setdefault("entry_price", sample.get("recommended_signal", {}).get("entry_price"))
            signal.setdefault("stop_loss", sample.get("recommended_signal", {}).get("stop_loss"))
            signal.setdefault("take_profit", sample.get("recommended_signal", {}).get("take_profit"))
        strategies.append(
            {
                "strategy_id": row.get("strategy_id"),
                "strategy_name": row.get("strategy_name"),
                "symbol": row.get("symbol"),
                "asset_class": row.get("asset_class"),
                "data_quality": row.get("data_quality", "historical_data"),
                "strategy_source": row.get("strategy_source", "supabase"),
                "source_id": row.get("source_id"),
                "recommended_signal": signal,
                "signals": row.get("signals") or (sample.get("signals") if sample else []),
                "extracted_rules": row.get("rules_summary") or {},
                "parent_strategy_id": (row.get("rules_summary") or {}).get("parent_strategy_id"),
            }
        )
        if len(strategies) >= limit:
            break
    return strategies


def _enrich_with_market_data(strategy: dict[str, Any], requested_source: str = "auto") -> dict[str, Any]:
    if str(strategy.get("asset_class") or "").lower() != "forex":
        strategy.setdefault("data_source", "embedded_sample")
        strategy.setdefault("candle_count", len(strategy.get("signals") or []))
        strategy.setdefault("date_range", None)
        strategy.setdefault("historical_flag", "fallback_sample")
        return strategy
    timeframe = (strategy.get("recommended_signal") or {}).get("timeframe", strategy.get("timeframe", "H1"))
    lookback = int(strategy.get("requested_candle_count") or 96)
    market = get_market_data_bundle(strategy.get("symbol", "EURUSD"), timeframe=timeframe, lookback=lookback, source=requested_source)
    strategy["data_source"] = market.get("source")
    strategy["data_quality"] = market.get("data_quality", strategy.get("data_quality"))
    strategy["candle_count"] = market.get("candle_count", 0)
    strategy["date_range"] = market.get("date_range")
    strategy["requested_candle_count"] = market.get("requested_candle_count", lookback)
    strategy["resolved_symbol"] = market.get("symbol", strategy.get("symbol"))
    strategy["instrument"] = market.get("instrument")
    strategy["historical_flag"] = "historical" if market.get("source") == "oanda_practice" else "fallback_sample"
    strategy["fallback_reason"] = market.get("fallback_reason")
    generated = generate_strategy_signals_from_candles(
        strategy.get("strategy_id", ""),
        strategy.get("symbol", "EURUSD"),
        timeframe,
        market.get("candles") or [],
        limit=8,
    )
    if generated:
        strategy["signals"] = generated
        rec = strategy.get("recommended_signal") or {}
        latest = generated[-1]
        rec.update(
            {
                "symbol": latest["symbol"],
                "action": latest["action"],
                "entry_price": latest["entry_price"],
                "stop_loss": latest["stop_loss"],
                "take_profit": latest["take_profit"],
                "timeframe": timeframe,
            }
        )
        strategy["recommended_signal"] = rec
    return strategy


def _safe_float(v: Any) -> float:
    try:
        return float(v)
    except Exception:
        return 0.0


def _score(report: dict[str, Any]) -> dict[str, Any]:
    summary = report["summary"]
    trades_count = int(summary.get("executed", 0))
    win_rate = _safe_float(summary.get("win_rate_pct", 0.0)) / 100.0
    profit_factor = _safe_float(summary.get("profit_factor", 0.0))
    if not profit_factor or profit_factor == float("inf") or profit_factor != profit_factor:
        profit_factor = 0.0
    max_drawdown = _safe_float(summary.get("max_drawdown_pct", 0.0))
    total_return = _safe_float(summary.get("return_pct", 0.0))
    avg_return = (total_return / trades_count) if trades_count else 0.0
    stability_score = (
        max(0.0, min(1.0, (win_rate * 0.45) + min(profit_factor / 3.0, 1.0) * 0.3 + max(0.0, 1.0 - max_drawdown / 20.0) * 0.25))
        if trades_count
        else 0.0
    )
    recommendation = "paper_candidate" if trades_count >= 3 and stability_score >= 0.45 else "needs_review"
    return {
        "trades_count": trades_count,
        "win_rate": round(win_rate, 3),
        "profit_factor": round(profit_factor, 2),
        "max_drawdown": round(max_drawdown, 2),
        "total_return": round(total_return, 2),
        "avg_return": round(avg_return, 2),
        "stability_score": round(stability_score, 3),
        "recommendation": recommendation,
    }


def _parse_strategy_analysis(strategy: dict[str, Any], report: dict[str, Any]) -> tuple[list[str], str]:
    summary = report.get("summary") or {}
    strategy_id = str(strategy.get("strategy_id") or "")
    rules = strategy.get("extracted_rules") or {}
    signals = strategy.get("signals") or []
    reasons: list[str] = []
    if int(summary.get("executed", 0) or 0) == 0:
        reasons.append("no_entries_generated_on_current_market_data")
        if "london_breakout" in strategy_id:
            reasons.append("breakout_threshold_or_confirmation_too_strict")
            reasons.append("session_window_or_range_definition_too_narrow")
            if "volatility" not in strategy_id:
                reasons.append("volatility_filter_under-specified")
        if "trend_pullback" in strategy_id:
            reasons.append("pullback_trigger_did_not_rebound_within_lookback_window")
            reasons.append("trend_lookback_may_be_misaligned_with_current_move")
        if strategy.get("candle_count", 0) <= 0:
            reasons.append("missing_candle_data")
        if not signals:
            reasons.append("signal_generator_returned_zero_candidates")
    else:
        reasons.append("generated_valid_simulated_trades")
    if strategy.get("fallback_reason"):
        reasons.append(f"market_data_fallback:{strategy['fallback_reason']}")
    if rules.get("parent_strategy_id"):
        reasons.append(f"parent_strategy:{rules['parent_strategy_id']}")
    return reasons, "; ".join(reasons)


def _submit_signal(signal_payload: dict[str, Any]) -> dict[str, Any]:
    req = urllib.request.Request(
        RECEIVER_URL,
        data=json.dumps(signal_payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        body = json.loads(resp.read())
    return {
        "status_code": resp.status,
        "body": body,
        "accepted": resp.status < 300,
    }


def _submission_execution_state(submission: dict[str, Any] | None) -> tuple[bool, str | None]:
    if not submission:
        return False, None
    body = submission.get("body") or {}
    engine_result = body.get("engine_result") or {}
    status = str(engine_result.get("status") or "").lower()
    rejection = str(engine_result.get("rejection_reason") or "")
    if status in {"executed_oanda_practice", "approved_demo"}:
        return True, None
    if rejection:
        return False, rejection
    if not submission.get("accepted"):
        return False, str(submission.get("error") or "submission_not_accepted")
    return False, status or "submission_not_executed"


def _update_engine_status(top_strategy: dict[str, Any], submission: dict[str, Any] | None) -> None:
    data: dict[str, Any] = {}
    if STATUS_FILE.exists():
        try:
            data = json.loads(STATUS_FILE.read_text())
        except Exception:
            data = {}
    data["tournament"] = {
        "updated_at": _now(),
        "status": "completed",
        "top_strategy": top_strategy.get("strategy_id"),
        "top_strategy_name": top_strategy.get("strategy_name"),
        "paper_active": top_strategy.get("paper_active", False),
        "submission": submission,
    }
    tmp = STATUS_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2, default=str))
    tmp.replace(STATUS_FILE)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("paper",), default="paper")
    parser.add_argument("--source", choices=("supabase_first", "fallback_sample"), default="fallback_sample")
    parser.add_argument("--data-source", choices=("auto", "oanda_practice", "fallback_sample"), default="auto")
    parser.add_argument("--symbols", default="")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-submit", action="store_true")
    parser.add_argument("--candle-count", type=int, default=96)
    args = parser.parse_args()

    safety = evaluate_trading_safety()
    symbols = {token.strip().upper() for token in args.symbols.split(",") if token.strip()}
    strategies = _load_supabase_first_strategies(symbols=symbols) if args.source == "supabase_first" else _strategy_samples()
    if not strategies:
        strategies = _strategy_samples()
        args.source = "fallback_sample"
    if symbols:
        strategies = [strategy for strategy in strategies if str(strategy.get("symbol") or "").upper() in symbols]
    for strategy in strategies:
        strategy["requested_candle_count"] = args.candle_count
    strategies = [_enrich_with_market_data(dict(strategy), requested_source=args.data_source) for strategy in strategies]
    ranked: list[dict[str, Any]] = []
    for strategy in strategies:
        bt = Backtester(initial_balance=10000.0)
        report = bt.run(strategy["signals"])
        metrics = _score(report)
        analysis_reasons, analysis_summary = _parse_strategy_analysis(strategy, report)
        promotable = metrics["trades_count"] > 0 and metrics["recommendation"] == "paper_candidate"
        if metrics["trades_count"] == 0:
            promotion_decision = "blocked_zero_trades"
        elif promotable and args.dry_run:
            promotion_decision = "promoted_for_next_cap_reset"
        elif promotable:
            promotion_decision = "paper_candidate"
        else:
            promotion_decision = "needs_review"
        row = {
            "created_at": _now(),
            "strategy_id": strategy["strategy_id"],
            "strategy_name": strategy["strategy_name"],
            "asset_class": strategy["asset_class"],
            "symbol": strategy["symbol"],
            "timeframe": strategy["recommended_signal"]["timeframe"],
            "data_quality": strategy["data_quality"],
            "data_source": strategy.get("data_source", args.source),
            "candle_count": strategy.get("candle_count", len(strategy.get("signals") or [])),
            "requested_candle_count": strategy.get("requested_candle_count", args.candle_count),
            "date_range": strategy.get("date_range"),
            "historical_flag": strategy.get("historical_flag", "fallback_sample"),
            "fallback_reason": strategy.get("fallback_reason"),
            "strategy_source": strategy.get("strategy_source", args.source),
            "source_id": strategy.get("source_id"),
            "parent_strategy_id": strategy.get("parent_strategy_id"),
            "extracted_rules": strategy.get("extracted_rules", {}),
            **metrics,
            "paper_active": False,
            "promotion_decision": promotion_decision,
            "ready_for_next_cap_reset": bool(args.dry_run and promotable),
            "analysis_reasons": analysis_reasons,
            "analysis_summary": analysis_summary,
            "recommended_signal": strategy.get("recommended_signal") or {},
            "direction": (strategy.get("recommended_signal") or {}).get("action"),
        }
        ranked.append({**strategy, "backtest_report": report, "metrics": row})

    ranked.sort(
        key=lambda item: (
            item["metrics"]["stability_score"],
            item["metrics"]["profit_factor"],
            item["metrics"]["win_rate"],
            item["metrics"]["total_return"],
        ),
        reverse=True,
    )

    for index, item in enumerate(ranked, start=1):
        item["metrics"]["rank"] = index
        append_jsonl("strategy_scores", item["metrics"])

    top = ranked[0]
    submission: dict[str, Any] | None = None
    submission_blocked_reason: str | None = None
    executed_trade = False
    receiver_rejection_reason: str | None = None
    if safety["safe"] and not args.dry_run and not args.no_submit and top["metrics"]["promotion_decision"] == "paper_candidate":
        try:
            submission = _submit_signal(top["recommended_signal"])
            executed_trade, receiver_rejection_reason = _submission_execution_state(submission)
            top["metrics"]["paper_active"] = executed_trade
        except Exception as exc:
            submission = {
                "accepted": False,
                "error": str(exc),
            }
            receiver_rejection_reason = str(exc)
    elif not args.dry_run and args.no_submit:
        submission_blocked_reason = "submission_disabled_by_no_submit"
    elif not args.dry_run:
        submission_blocked_reason = "top_strategy_not_promotable"
    elif top["metrics"]["promotion_decision"] == "promoted_for_next_cap_reset":
        submission_blocked_reason = "dry_run_cap_exhausted_promoted_for_next_cap_reset"

    append_jsonl("signals", {
        "created_at": _now(),
        "symbol": top["recommended_signal"]["symbol"],
        "asset_class": top["asset_class"],
        "direction": top["recommended_signal"]["action"],
        "confidence": top["recommended_signal"]["confidence"],
        "strategy_id": top["strategy_id"],
        "source": "nexus_trading_tournament",
        "timeframe": top["recommended_signal"]["timeframe"],
        "signal_payload": top["recommended_signal"],
        "status": "accepted" if executed_trade else "generated",
        "rejection_reason": None if executed_trade else receiver_rejection_reason or (submission or {}).get("error") or submission_blocked_reason,
        "safety_mode": "paper_demo_only",
    })
    append_jsonl("reports", {
        "created_at": _now(),
        "report_type": "strategy_tournament",
        "mode": args.mode,
        "receiver_status": "accepted" if executed_trade else "generated_only",
        "broker_status": "demo",
        "live_trading_enabled": False,
        "paper_trading_enabled": True,
        "strategies_tested": len(ranked),
        "trades_opened": 1 if executed_trade else 0,
        "best_strategy_id": top["strategy_id"],
        "summary": f"Top strategy {top['strategy_id']} rank=1 decision={top['metrics']['promotion_decision']}",
        "recommendations": {"next_action": "continue paper evidence collection" if top["metrics"]["trades_count"] == 0 else "prepare next cap reset paper candidate"},
        "verified_facts": {
            "submission": submission,
            "submission_blocked_reason": submission_blocked_reason,
            "receiver_rejection_reason": receiver_rejection_reason,
            "top_strategy": top["metrics"],
        },
    })

    result = {
        "ran_at": _now(),
        "mode": args.mode,
        "source_used": args.source,
        "data_source_requested": args.data_source,
        "symbols": sorted(symbols),
        "dry_run": args.dry_run,
        "no_submit": args.no_submit,
        "safety_gate": safety,
        "receiver_submission": submission,
        "submission_blocked_reason": submission_blocked_reason,
        "receiver_rejection_reason": receiver_rejection_reason,
        "strategies": [item["metrics"] for item in ranked],
        "top_strategy": top["metrics"],
        "top_candidate_for_next_cap_reset": top["metrics"] if top["metrics"]["ready_for_next_cap_reset"] else None,
    }
    TOURNAMENT_FILE.write_text(json.dumps(result, indent=2, default=str))
    _update_engine_status(top["metrics"], submission)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
