#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib.trading_fallback_logger import append_jsonl, latest_jsonl


OUTPUT_JSON = ROOT / "logs" / "practice_trade_memory_latest.json"
OUTPUT_MD = ROOT / "logs" / "practice_trade_memory_latest.md"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _normalize_symbol(value: Any) -> str:
    return str(value or "unknown").upper().replace("_", "")


def _asset_class_for_symbol(symbol: str) -> str:
    if symbol in {"EURUSD", "USDJPY", "GBPUSD"}:
        return "forex"
    if symbol in {"BTC", "ETH", "BTCUSD", "ETHUSD"}:
        return "crypto"
    if symbol in {"SPY", "QQQ"}:
        return "stocks_options"
    return "unknown"


def _family(strategy_id: str) -> str:
    text = strategy_id.lower()
    if "news" in text or "cpi" in text or "nfp" in text or "fomc" in text:
        return "news_event"
    if "open" in text or "breakout" in text:
        return "session_open"
    if "liquidity" in text or "sweep" in text:
        return "liquidity_sweep"
    if "mean_reversion" in text or "bollinger" in text:
        return "mean_reversion"
    if "trend" in text or "pullback" in text or "ema" in text or "macd" in text:
        return "trend_following"
    return "technical_indicator"


def _trigger(strategy_id: str, family: str) -> str:
    if family == "news_event":
        return "news_calendar_event"
    if family in {"session_open", "breakout"}:
        return "scheduled_session"
    if family == "liquidity_sweep":
        return "liquidity_sweep"
    return "continuous_indicator"


def _summarize() -> dict[str, Any]:
    trades = latest_jsonl("trades", limit=500)
    signals = latest_jsonl("signals", limit=500)
    reports = latest_jsonl("reports", limit=500)
    scoreboard = latest_jsonl("strategy_scores", limit=500)

    wins = losses = rejects = 0
    oanda_accepted = oanda_rejected = fallback_to_local_paper = duplicate_blocked = bug_detected = 0
    needs_strategy_research = needs_data_improvement = promoted_for_next_oanda_cap_reset = 0
    zero_trade_strategies: list[str] = []
    per_lane: list[dict[str, Any]] = []
    duplicate_strategy_pairs: Counter = Counter()
    rotated_candidates: list[dict[str, Any]] = []
    local_paper_reps = 0
    recommended_strategy_research_tasks: list[dict[str, Any]] = []

    lane_map: dict[str, dict[str, Any]] = {}
    for asset_class, symbols, execution_mode in [
        ("forex", ["EURUSD", "USDJPY", "GBPUSD"], "oanda_practice_or_local_paper"),
        ("crypto", ["BTC", "ETH"], "local_paper_only"),
        ("stocks", ["SPY", "QQQ"], "local_paper_only"),
        ("options", ["SPY", "QQQ"], "local_paper_theoretical"),
    ]:
        lane_map[asset_class] = {
            "asset_class": asset_class,
            "symbols": symbols,
            "strategies_tested": set(),
            "data_source": None,
            "data_quality": Counter(),
            "execution_mode": execution_mode,
            "trades_reps": 0,
            "rejects": 0,
            "blockers": [],
            "next_improvement": "collect more reps",
        }

    by_dimension: dict[str, Counter] = defaultdict(Counter)
    for row in scoreboard:
        if int(row.get("trades_count") or 0) == 0:
            zero_trade_strategies.append(str(row.get("strategy_id") or "unknown"))
        if row.get("promotion_decision") == "promoted_for_next_cap_reset":
            promoted_for_next_oanda_cap_reset += 1

    for row in trades:
        signal = row.get("signal") or {}
        symbol = _normalize_symbol(row.get("symbol") or signal.get("symbol"))
        strategy_id = str(row.get("strategy_id") or signal.get("strategy_id") or signal.get("strategy") or "unknown")
        asset_class = str(row.get("asset_class") or _asset_class_for_symbol(symbol))
        result = str((row.get("result") or {}).get("status") or row.get("status") or "unknown").lower()
        family = _family(strategy_id)
        trigger = _trigger(strategy_id, family)
        session = str(signal.get("session_name") or signal.get("session") or row.get("session") or "unspecified")
        data_quality = str(row.get("data_quality") or signal.get("data_quality") or "unknown")
        execution_mode = str(row.get("execution_mode") or row.get("broker_mode") or "local_paper")
        pnl = _safe_float(row.get("pnl") or (row.get("result") or {}).get("pnl"), 0.0)
        if result in {"win", "tp_hit"} or pnl > 0:
            wins += 1
            final_result = "win"
        elif result in {"loss", "sl_hit"} or pnl < 0:
            losses += 1
            final_result = "loss"
        else:
            final_result = result or "flat"
        if execution_mode == "local_paper":
            local_paper_reps += 1

        bucket = lane_map.get(asset_class)
        if bucket:
            bucket["strategies_tested"].add(strategy_id)
            bucket["trades_reps"] += 1
            bucket["data_quality"][data_quality] += 1
            if not bucket["data_source"]:
                bucket["data_source"] = execution_mode
        by_dimension["asset_class"][asset_class] += 1
        by_dimension["symbol"][symbol] += 1
        by_dimension["strategy_family"][family] += 1
        by_dimension["trigger_type"][trigger] += 1
        by_dimension["session"][session] += 1
        by_dimension["data_quality"][data_quality] += 1
        by_dimension["execution_mode"][execution_mode] += 1
        by_dimension["result"][final_result] += 1

    for row in signals:
        symbol = _normalize_symbol(row.get("symbol"))
        strategy_id = str(row.get("strategy_id") or "unknown")
        family = _family(strategy_id)
        trigger = _trigger(strategy_id, family)
        asset_class = str(row.get("asset_class") or _asset_class_for_symbol(symbol))
        rejection = str(row.get("rejection_reason") or "")
        if rejection:
            rejects += 1
            bucket = lane_map.get(asset_class)
            if bucket:
                bucket["rejects"] += 1
            if "duplicate" in rejection:
                duplicate_blocked += 1
                duplicate_strategy_pairs[f"{strategy_id}::{symbol}"] += 1
            if "data" in rejection or "candle" in rejection:
                needs_data_improvement += 1
            if "rules" in rejection or "setup" in rejection:
                needs_strategy_research += 1
            by_dimension["result"]["reject"] += 1
            by_dimension["strategy_family"][family] += 1
            by_dimension["trigger_type"][trigger] += 1

    for row in reports:
        summary = str(row.get("summary") or "")
        report_type = str(row.get("report_type") or "")
        verified = row.get("verified_facts") or {}
        if report_type == "oanda_practice_check":
            if verified.get("practice_order_placed"):
                oanda_accepted += 1
            elif verified.get("blocker"):
                oanda_rejected += 1
        if report_type == "strategy_tournament":
            body = (((verified.get("submission") or {}).get("body")) or {})
            if body.get("execution_mode") == "local_paper" or body.get("fallback_used"):
                fallback_to_local_paper += 1
        if report_type == "nexus_demo_trading_loop":
            for row in verified.get("duplicate_blocked_candidates") or []:
                pair = f"{row.get('strategy_id')}::{_normalize_symbol(row.get('symbol'))}"
                duplicate_strategy_pairs[pair] += 1
                duplicate_blocked += 1
            rotated = verified.get("rotated_to_candidate")
            if rotated:
                rotated_candidates.append({
                    "strategy_id": rotated.get("strategy_id"),
                    "symbol": rotated.get("symbol"),
                    "asset_class": rotated.get("asset_class"),
                })
            if verified.get("local_paper_reps"):
                local_paper_reps += int(verified.get("local_paper_reps") or 0)
            if verified.get("local_paper_fallback_reason"):
                fallback_to_local_paper += 1
            for task in verified.get("recommended_strategy_research_tasks") or []:
                recommended_strategy_research_tasks.append(task)
        if "error" in summary.lower() or "blocked" in summary.lower():
            bug_detected += 1

    for asset_class, row in lane_map.items():
        row["strategies_tested"] = sorted(row["strategies_tested"])
        row["data_quality"] = dict(row["data_quality"])
        if asset_class == "forex":
            row["next_improvement"] = "promote best forex candidate to capped Oanda practice only after clean dry-run"
        elif asset_class == "crypto":
            row["next_improvement"] = "add stronger local_paper crypto signal reps before any adapter work"
        elif asset_class == "stocks":
            row["next_improvement"] = "expand SPY/QQQ local_paper data and watch coverage"
        else:
            row["next_improvement"] = "keep options theoretical until a real paper adapter exists"
        if not row["trades_reps"] and not row["rejects"]:
            row["blockers"].append("no_recent_reps")
        per_lane.append(row)

    summary = {
        "generated_at": _now(),
        "wins": wins,
        "losses": losses,
        "rejects": rejects,
        "zero_trade_strategies": sorted(set(zero_trade_strategies)),
        "oanda_accepted_rejected": {"accepted": oanda_accepted, "rejected": oanda_rejected},
        "fallback_to_local_paper": fallback_to_local_paper,
        "duplicate_blocked": duplicate_blocked,
        "duplicate_signal_count": duplicate_blocked,
        "duplicate_strategy_pairs": dict(duplicate_strategy_pairs),
        "rotated_candidates": rotated_candidates,
        "local_paper_reps": local_paper_reps,
        "bug_detected": bug_detected,
        "needs_strategy_research": needs_strategy_research,
        "needs_data_improvement": needs_data_improvement,
        "promoted_for_next_oanda_cap_reset": promoted_for_next_oanda_cap_reset,
        "recommended_strategy_research_tasks": recommended_strategy_research_tasks,
        "by_dimension": {key: dict(counter) for key, counter in by_dimension.items()},
        "asset_lanes": per_lane,
        "vibe_recommendation": "focus on zero-trade and high-reject strategies before raising caps",
        "hermes_decision": "keep practice_learning active and use capped execute cycles for forex only",
    }
    return summary


def _write_markdown(summary: dict[str, Any]) -> None:
    lines = [
        "# Practice Trade Memory",
        "",
        f"- Generated at: `{summary.get('generated_at')}`",
        f"- Wins: `{summary.get('wins')}`",
        f"- Losses: `{summary.get('losses')}`",
        f"- Rejects: `{summary.get('rejects')}`",
        f"- Duplicate blocked: `{summary.get('duplicate_blocked')}`",
        f"- Local paper reps: `{summary.get('local_paper_reps')}`",
        f"- Needs strategy research: `{summary.get('needs_strategy_research')}`",
        f"- Needs data improvement: `{summary.get('needs_data_improvement')}`",
        f"- Promoted for next Oanda cap reset: `{summary.get('promoted_for_next_oanda_cap_reset')}`",
        "",
        "## Asset Lanes",
    ]
    for row in summary.get("asset_lanes") or []:
        lines.append(
            f"- `{row.get('asset_class')}` symbols=`{', '.join(row.get('symbols') or [])}` "
            f"execution=`{row.get('execution_mode')}` reps=`{row.get('trades_reps')}` rejects=`{row.get('rejects')}` "
            f"next=`{row.get('next_improvement')}`"
        )
    if summary.get("rotated_candidates"):
        lines.append("")
        lines.append("## Rotations")
        for row in summary.get("rotated_candidates") or []:
            lines.append(f"- `{row.get('strategy_id')}` `{row.get('symbol')}` `{row.get('asset_class')}`")
    OUTPUT_MD.write_text("\n".join(lines) + "\n")


def main() -> int:
    summary = _summarize()
    OUTPUT_JSON.write_text(json.dumps(summary, indent=2, default=str))
    _write_markdown(summary)
    append_jsonl(
        "reports",
        {
            "created_at": _now(),
            "report_type": "practice_trade_memory",
            "mode": "paper",
            "receiver_status": "n/a",
            "broker_status": "paper_demo_only",
            "live_trading_enabled": False,
            "paper_trading_enabled": True,
            "summary": f"wins={summary['wins']} losses={summary['losses']} rejects={summary['rejects']}",
            "verified_facts": summary,
        },
    )
    supabase_written = False
    local_fallback = True
    try:
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "replay_trading_fallback_logs_to_supabase.py"), "--apply"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=120,
        )
        if proc.returncode == 0:
            supabase_written = True
            local_fallback = False
    except Exception:
        supabase_written = False
    print(json.dumps({"json": str(OUTPUT_JSON), "markdown": str(OUTPUT_MD), "supabase_written": supabase_written, "local_fallback": local_fallback, "summary": summary}, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
