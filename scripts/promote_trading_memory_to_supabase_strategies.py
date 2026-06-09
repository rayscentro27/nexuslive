#!/usr/bin/env python3
from __future__ import annotations

import argparse
import glob
import json
import os
import ssl
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error, request

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from lib.trading_fallback_logger import latest_jsonl
from lib.trading_market_data import fetch_oanda_candles
from lib.trading_safety_gate import seed_safe_trading_env_from_launch_agent
import strategy_paper_bridge as spb


ARTIFACT_FILE = ROOT / "logs" / "trading_memory_supabase_promotion_latest.json"
SUMMARY_FILE = ROOT / "logs" / "trading_memory_supabase_promotion_latest.md"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _stable_uuid(label: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"nexus-trading::{label}"))


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
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY") or ""
    return {
        "Content-Type": "application/json",
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Prefer": "resolution=merge-duplicates,return=representation",
    }


def _sb_get(path: str) -> list[dict[str, Any]]:
    url = (os.getenv("SUPABASE_URL", "") or "").rstrip("/")
    if not url:
        return []
    req = request.Request(f"{url}/rest/v1/{path}", headers=_headers())
    try:
        with request.urlopen(req, timeout=20, context=_ssl_context()) as resp:
            return json.loads(resp.read())
    except error.HTTPError as exc:
        if exc.code in {400, 404}:
            return []
        raise


def _sb_post(table: str, rows: list[dict[str, Any]], dry_run: bool) -> dict[str, Any]:
    if dry_run:
        return {"table": table, "prepared": len(rows), "written": 0, "dry_run": True}
    if not rows:
        return {"table": table, "prepared": 0, "written": 0, "dry_run": False}
    url = (os.getenv("SUPABASE_URL", "") or "").rstrip("/")
    req = request.Request(
        f"{url}/rest/v1/{table}",
        data=json.dumps(rows).encode(),
        headers=_headers(),
        method="POST",
    )
    with request.urlopen(req, timeout=20, context=_ssl_context()) as resp:
        body = json.loads(resp.read() or b"[]")
    return {"table": table, "prepared": len(rows), "written": len(body) if isinstance(body, list) else len(rows), "dry_run": False}


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def _load_latest_vibe() -> tuple[dict[str, Any], str | None]:
    paths = sorted(glob.glob(str(ROOT / "integrations" / "vibe_trading" / "reports" / "vibe_strategy_review_*.json")))
    if not paths:
        return {}, None
    path = paths[-1]
    with open(path, encoding="utf-8") as handle:
        return json.load(handle), path


def _latest_vibe_markdown_path() -> str | None:
    paths = sorted(glob.glob(str(ROOT / "integrations" / "vibe_trading" / "reports" / "vibe_strategy_review_*.md")))
    return paths[-1] if paths else None


def _load_recent_jsonl(kind: str, limit: int = 200) -> list[dict[str, Any]]:
    rows = latest_jsonl(kind, limit=limit)
    if rows:
        return rows
    file_prefix = {
        "strategy_scores": "nexus_strategy_scores_*.jsonl",
        "trades": "nexus_paper_trades_*.jsonl",
        "signals": "nexus_trading_signals_*.jsonl",
    }.get(kind)
    if not file_prefix:
        return []
    paths = sorted((ROOT / "logs").glob(file_prefix))
    if not paths:
        return []
    all_rows: list[dict[str, Any]] = []
    for path in paths[-3:]:
        try:
            for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
                line = line.strip()
                if not line:
                    continue
                payload = json.loads(line)
                if isinstance(payload, dict):
                    all_rows.append(payload)
        except Exception:
            continue
    return all_rows[-limit:]


def _load_local_memory() -> dict[str, Any]:
    tournament = _load_json(ROOT / "logs" / "nexus_trading_tournament_latest.json")
    hermes_candidates = _load_json(ROOT / "logs" / "hermes_supabase_strategy_candidates_latest.json")
    vibe, vibe_path = _load_latest_vibe()
    return {
        "tournament": tournament,
        "hermes_candidates": hermes_candidates,
        "vibe": vibe,
        "vibe_path": vibe_path,
        "vibe_markdown_path": _latest_vibe_markdown_path(),
        "strategy_scores": _load_recent_jsonl("strategy_scores", limit=200),
        "paper_trades": _load_recent_jsonl("trades", limit=200),
        "signals": _load_recent_jsonl("signals", limit=200),
    }


def _normalize_symbol(symbol: str) -> str:
    return str(symbol or "").upper().replace("_", "")


def _parse_json_field(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if not value:
        return {}
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}
    return {}


def _existing_maps() -> tuple[set[str], set[str], set[str]]:
    proposals = _sb_get("reviewed_signal_proposals?select=id,trace_id&asset_type=eq.forex&limit=500")
    risks = _sb_get("risk_decisions?select=id,trace_id&asset_type=eq.forex&limit=500")
    variants = _sb_get("strategy_variants?select=id,strategy_id,variant_name&limit=500")
    proposal_trace_ids = {str(row.get("trace_id") or "") for row in proposals}
    risk_trace_ids = {str(row.get("trace_id") or "") for row in risks}
    variant_keys = {f"{row.get('strategy_id')}::{row.get('variant_name')}" for row in variants}
    return proposal_trace_ids, risk_trace_ids, variant_keys


def _infer_zero_trade_reasons(tournament: dict[str, Any], strategy_id: str) -> list[str]:
    for row in tournament.get("strategies") or []:
        if row.get("strategy_id") == strategy_id:
            reasons = list(row.get("analysis_reasons") or [])
            if reasons:
                return reasons
    fallback: list[str] = []
    if "london_breakout" in strategy_id:
        fallback.extend(
            [
                "breakout_threshold_or_confirmation_too_strict",
                "session_window_or_range_definition_too_narrow",
                "volatility_filter_under-specified",
            ]
        )
    if "trend_pullback" in strategy_id:
        fallback.extend(
            [
                "pullback_trigger_did_not_rebound_within_lookback_window",
                "trend_lookback_may_be_misaligned_with_current_move",
            ]
        )
    return fallback or ["zero_trade_strategy_requires_variant_expansion"]


def _base_candidate_definitions(memory: dict[str, Any]) -> list[dict[str, Any]]:
    tournament = memory["tournament"]
    vibe = memory["vibe"]
    recommendations = vibe.get("recommendations") or []
    vibe_source = memory.get("vibe_path") or "vibe_local_review"
    tournament_path = str(ROOT / "logs" / "nexus_trading_tournament_latest.json")
    zero_trade_map = {
        "eurusd_london_breakout": _infer_zero_trade_reasons(tournament, "eurusd_london_breakout"),
        "usdjpy_trend_pullback": _infer_zero_trade_reasons(tournament, "usdjpy_trend_pullback"),
    }
    return [
        {
            "strategy_id": "eurusd_london_breakout_tighter_range",
            "parent_strategy_id": "eurusd_london_breakout",
            "variant_name": "tighter_range_breakout",
            "asset_class": "forex",
            "symbol": "EURUSD",
            "timeframe": "H1",
            "preferred_side": "BUY",
            "entry_rules": "Trigger on a break of the prior candle high/low with a small negative entry buffer to reduce missed entries.",
            "exit_rules": "Exit at 1.5R or if the next candle fully rejects the breakout.",
            "stop_loss_rules": "Stop beyond the prior 3-candle swing.",
            "take_profit_rules": "Take profit at 1.5x risk.",
            "risk_rules": "1 unit max, paper/demo only, zero-trade variants stay blocked from promotion.",
            "data_source": "local_memory_plus_vibe",
            "data_quality": "local_fallback_plus_oanda_review",
            "test_status": "untested",
            "hypothesis": "The base London breakout likely missed entries because its confirmation threshold was too strict.",
            "source_artifact": vibe_source,
            "source_references": [tournament_path, vibe_source],
            "analysis_reasons": zero_trade_map["eurusd_london_breakout"] + ["variant: tighter threshold"],
            "risk_score": 68,
            "confidence": 0.70,
        },
        {
            "strategy_id": "eurusd_london_breakout_wider_session",
            "parent_strategy_id": "eurusd_london_breakout",
            "variant_name": "wider_session_breakout",
            "asset_class": "forex",
            "symbol": "EURUSD",
            "timeframe": "H1",
            "preferred_side": "BUY",
            "entry_rules": "Use a 3-candle session range for breakout detection instead of a single prior bar.",
            "exit_rules": "Exit at 1.6R or failed follow-through.",
            "stop_loss_rules": "Stop beyond the 3-candle session low/high.",
            "take_profit_rules": "Take profit at 1.6x risk.",
            "risk_rules": "1 unit max, candidate only until simulated trades exist.",
            "data_source": "local_memory_plus_vibe",
            "data_quality": "local_fallback_plus_oanda_review",
            "test_status": "untested",
            "hypothesis": "A wider session definition may fit the current EURUSD structure better than the narrow prior-bar trigger.",
            "source_artifact": vibe_source,
            "source_references": [tournament_path, vibe_source],
            "analysis_reasons": zero_trade_map["eurusd_london_breakout"] + ["variant: wider session"],
            "risk_score": 67,
            "confidence": 0.69,
        },
        {
            "strategy_id": "eurusd_london_breakout_volatility_filter",
            "parent_strategy_id": "eurusd_london_breakout",
            "variant_name": "volatility_filtered_breakout",
            "asset_class": "forex",
            "symbol": "EURUSD",
            "timeframe": "H1",
            "preferred_side": "BUY",
            "entry_rules": "Require breakout plus above-average candle expansion before entry.",
            "exit_rules": "Exit at 1.4R or on immediate volatility fade.",
            "stop_loss_rules": "Use the latest 3-candle swing.",
            "take_profit_rules": "Target 1.4x risk.",
            "risk_rules": "Keep paper/demo only and suppress weak breakout conditions.",
            "data_source": "local_memory_plus_vibe",
            "data_quality": "local_fallback_plus_oanda_review",
            "test_status": "untested",
            "hypothesis": "The original rules lacked an explicit volatility regime gate, producing no valid breakout candidate.",
            "source_artifact": vibe_source,
            "source_references": [tournament_path, vibe_source],
            "analysis_reasons": zero_trade_map["eurusd_london_breakout"] + ["variant: explicit volatility gate"],
            "risk_score": 66,
            "confidence": 0.71,
        },
        {
            "strategy_id": "usdjpy_trend_pullback_short_lookback",
            "parent_strategy_id": "usdjpy_trend_pullback",
            "variant_name": "short_lookback_pullback",
            "asset_class": "forex",
            "symbol": "USDJPY",
            "timeframe": "H1",
            "preferred_side": "BUY",
            "entry_rules": "Use a shorter trend confirmation window and allow shallower pullbacks.",
            "exit_rules": "Exit at 1.5R or failed rebound candle.",
            "stop_loss_rules": "Stop beyond the pullback swing low/high.",
            "take_profit_rules": "Take profit at 1.5x risk.",
            "risk_rules": "Respect JPY pip scale and maintain paper/demo only routing.",
            "data_source": "local_memory_plus_vibe",
            "data_quality": "local_fallback_plus_oanda_review",
            "test_status": "untested",
            "hypothesis": "The base pullback needed a shallower trigger to catch current USDJPY trend pauses.",
            "source_artifact": vibe_source,
            "source_references": [tournament_path, vibe_source],
            "analysis_reasons": zero_trade_map["usdjpy_trend_pullback"] + ["variant: shorter lookback"],
            "risk_score": 67,
            "confidence": 0.70,
        },
        {
            "strategy_id": "usdjpy_trend_pullback_long_lookback",
            "parent_strategy_id": "usdjpy_trend_pullback",
            "variant_name": "long_lookback_pullback",
            "asset_class": "forex",
            "symbol": "USDJPY",
            "timeframe": "H1",
            "preferred_side": "BUY",
            "entry_rules": "Require a clearer 3-candle trend before pullback entry.",
            "exit_rules": "Exit at 1.7R or when rebound stalls.",
            "stop_loss_rules": "Stop beyond the recent swing using 3-candle context.",
            "take_profit_rules": "Take profit at 1.7x risk.",
            "risk_rules": "Candidate only until Oanda-data tournament confirms at least one simulated trade.",
            "data_source": "local_memory_plus_vibe",
            "data_quality": "local_fallback_plus_oanda_review",
            "test_status": "untested",
            "hypothesis": "The base trend definition may be under-specified; a longer lookback makes trend bias explicit.",
            "source_artifact": vibe_source,
            "source_references": [tournament_path, vibe_source],
            "analysis_reasons": zero_trade_map["usdjpy_trend_pullback"] + ["variant: longer lookback"],
            "risk_score": 65,
            "confidence": 0.68,
        },
        {
            "strategy_id": "eurusd_trend_following_momentum_continuation",
            "parent_strategy_id": "eurusd_london_breakout",
            "variant_name": "momentum_continuation",
            "asset_class": "forex",
            "symbol": "EURUSD",
            "timeframe": "H1",
            "preferred_side": "BUY",
            "entry_rules": "Three directional closes plus fresh range expansion.",
            "exit_rules": "Exit at 1.5R or after momentum failure.",
            "stop_loss_rules": "Stop beyond the latest momentum swing.",
            "take_profit_rules": "Take profit at 1.5x risk.",
            "risk_rules": "Momentum-only candidate; paper/demo only.",
            "data_source": "local_memory_plus_vibe",
            "data_quality": "local_fallback_plus_oanda_review",
            "test_status": "untested",
            "hypothesis": "If classic London breakout never triggers, momentum continuation can still capture the move.",
            "source_artifact": vibe_source,
            "source_references": [tournament_path, vibe_source],
            "analysis_reasons": zero_trade_map["eurusd_london_breakout"] + ["variant: momentum continuation"],
            "risk_score": 64,
            "confidence": 0.69,
        },
        {
            "strategy_id": "gbpusd_session_breakout_candidate",
            "parent_strategy_id": "eurusd_london_breakout",
            "variant_name": "gbpusd_session_breakout",
            "asset_class": "forex",
            "symbol": "GBPUSD",
            "timeframe": "H1",
            "preferred_side": "BUY",
            "entry_rules": "Session breakout using recent 3-candle range with small buffer reduction.",
            "exit_rules": "Exit at 1.5R or when breakout closes back inside the range.",
            "stop_loss_rules": "Stop beyond the session range opposite edge.",
            "take_profit_rules": "Take profit at 1.5x risk.",
            "risk_rules": "Use only if market data is available; never mark sample fallback as live.",
            "data_source": "local_memory_plus_vibe",
            "data_quality": "candidate_requires_market_data_check",
            "test_status": "untested",
            "hypothesis": "GBPUSD may provide a cleaner session-breakout test bed if EURUSD stays dormant.",
            "source_artifact": vibe_source,
            "source_references": [tournament_path, vibe_source],
            "analysis_reasons": ["symbol expansion for additional forex candidate coverage"],
            "risk_score": 62,
            "confidence": 0.66,
        },
        {
            "strategy_id": "eurusd_mean_reversion_fade",
            "parent_strategy_id": "eurusd_london_breakout",
            "variant_name": "mean_reversion_fade",
            "asset_class": "forex",
            "symbol": "EURUSD",
            "timeframe": "H1",
            "preferred_side": "SELL",
            "entry_rules": "Fade significant deviation from a short rolling mean after stretch candles.",
            "exit_rules": "Exit back toward mean or at 1.2R.",
            "stop_loss_rules": "Stop beyond the stretch candle extreme.",
            "take_profit_rules": "Take profit at mean reversion or 1.2x risk.",
            "risk_rules": "Experimental forex candidate; must remain candidate until tested.",
            "data_source": "local_memory_plus_vibe",
            "data_quality": "local_fallback_plus_oanda_review",
            "test_status": "untested",
            "hypothesis": "If breakout conditions stay dormant, current EURUSD may reward fades more than continuation.",
            "source_artifact": vibe_source,
            "source_references": [tournament_path, vibe_source],
            "analysis_reasons": zero_trade_map["eurusd_london_breakout"] + ["variant: mean reversion alternative"],
            "risk_score": 61,
            "confidence": 0.65,
        },
        {
            "strategy_id": "eurusd_london_breakout_replay_memory",
            "parent_strategy_id": "eurusd_london_breakout",
            "variant_name": "replay_memory_calibrated",
            "asset_class": "forex",
            "symbol": "EURUSD",
            "timeframe": "H1",
            "preferred_side": "BUY",
            "entry_rules": "Retain breakout structure but tighten entry to the live-memory price band seen in local signal artifacts.",
            "exit_rules": "Exit at 1.3R or early rejection.",
            "stop_loss_rules": "Stop beyond recent swing low.",
            "take_profit_rules": "Take profit at 1.3x risk.",
            "risk_rules": "Paper/demo only and only promotable after at least one simulated trade.",
            "data_source": "local_signal_memory",
            "data_quality": "verified_local_signal_artifact",
            "test_status": "untested",
            "hypothesis": "Recent local signal memory suggests the breakout needs tighter price anchoring than the base rule set.",
            "source_artifact": tournament_path,
            "source_references": [tournament_path, vibe_source],
            "analysis_reasons": zero_trade_map["eurusd_london_breakout"] + ["variant: local signal memory calibration"],
            "risk_score": 64,
            "confidence": 0.67,
        },
    ]


def _augment_from_local_artifacts(candidates: list[dict[str, Any]], memory: dict[str, Any]) -> list[dict[str, Any]]:
    score_by_strategy = {str(row.get("strategy_id")): row for row in memory["strategy_scores"] if row.get("strategy_id")}
    last_trade_by_strategy = {str(row.get("strategy_id")): row for row in memory["paper_trades"] if row.get("strategy_id")}
    last_signal_by_strategy = {str(row.get("strategy_id")): row for row in memory["signals"] if row.get("strategy_id")}
    vibe = memory["vibe"]
    vibe_recommendations = vibe.get("recommendations") or []
    for candidate in candidates:
        parent_score = score_by_strategy.get(candidate["parent_strategy_id"]) or score_by_strategy.get(candidate["strategy_id"]) or {}
        last_trade = last_trade_by_strategy.get(candidate["parent_strategy_id"]) or {}
        last_signal = last_signal_by_strategy.get(candidate["parent_strategy_id"]) or {}
        candidate["memory_context"] = {
            "parent_score_summary": {
                "data_source": parent_score.get("data_source"),
                "data_quality": parent_score.get("data_quality"),
                "trades_count": parent_score.get("trades_count"),
                "win_rate": parent_score.get("win_rate"),
                "profit_factor": parent_score.get("profit_factor"),
                "analysis_summary": parent_score.get("analysis_summary"),
            },
            "last_trade_status": last_trade.get("status"),
            "last_trade_failure_reason": last_trade.get("failure_reason"),
            "last_signal_payload": last_signal.get("signal_payload"),
            "vibe_recommendations": vibe_recommendations,
        }
    return candidates


def _last_price(symbol: str, timeframe: str) -> float | None:
    market = fetch_oanda_candles(symbol, timeframe=timeframe, lookback=8)
    candles = market.get("candles") or []
    if not candles:
        return None
    return float(candles[-1]["close"])


def _fallback_price(symbol: str) -> float:
    symbol = _normalize_symbol(symbol)
    if symbol == "EURUSD":
        return 1.10
    if symbol == "USDJPY":
        return 145.0
    if symbol == "GBPUSD":
        return 1.27
    return 1.00


def _proposal_row(variant: dict[str, Any]) -> dict[str, Any]:
    proposal_id = _stable_uuid(f"proposal::{variant['strategy_id']}")
    trace_id = f"strategy_variant::{variant['strategy_id']}"
    entry_price = _last_price(variant["symbol"], variant["timeframe"])
    if entry_price is None:
        entry_price = _fallback_price(variant["symbol"])
    pip = 0.0001 if "JPY" not in variant["symbol"] else 0.01
    if str(variant["preferred_side"]).upper() == "BUY":
        stop_loss = entry_price - (12 * pip)
        take_profit = entry_price + (24 * pip)
    else:
        stop_loss = entry_price + (12 * pip)
        take_profit = entry_price - (24 * pip)
    research_context = {
        "parent_strategy_id": variant["parent_strategy_id"],
        "variant_name": variant["variant_name"],
        "asset_class": variant["asset_class"],
        "hypothesis": variant["hypothesis"],
        "source_artifact": variant["source_artifact"],
        "source_references": variant["source_references"],
        "analysis_reasons": variant["analysis_reasons"],
        "memory_context": variant["memory_context"],
        "data_source": variant["data_source"],
        "data_quality": variant["data_quality"],
        "test_status": variant["test_status"],
    }
    recommendation = (
        f"Candidate variant derived from {variant['parent_strategy_id']}. "
        f"Hypothesis: {variant['hypothesis']} "
        f"Test status: {variant['test_status']}. "
        f"Data provenance: {variant['data_source']} / {variant['data_quality']}."
    )
    return {
        "id": proposal_id,
        "signal_id": None,
        "symbol": variant["symbol"],
        "side": variant["preferred_side"],
        "timeframe": variant["timeframe"],
        "strategy_id": variant["strategy_id"],
        "strategy_type": "strategy_variant_candidate",
        "asset_type": "forex",
        "entry_price": round(float(entry_price), 5),
        "stop_loss": round(float(stop_loss), 5),
        "take_profit": round(float(take_profit), 5),
        "ai_confidence": variant["confidence"],
        "market_context": variant["entry_rules"],
        "research_context": json.dumps(research_context, ensure_ascii=True),
        "risk_notes": variant["risk_rules"],
        "recommendation": recommendation,
        "status": "proposed",
        "trace_id": trace_id,
    }


def _risk_row(variant: dict[str, Any], proposal_id: str) -> dict[str, Any]:
    risk_score = float(variant["risk_score"])
    decision = "approved" if risk_score >= 70 else "manual_review" if risk_score >= 40 else "blocked"
    return {
        "id": _stable_uuid(f"risk::{variant['strategy_id']}"),
        "proposal_id": proposal_id,
        "signal_id": None,
        "symbol": variant["symbol"],
        "side": variant["preferred_side"],
        "asset_type": "forex",
        "decision": decision,
        "risk_score": risk_score,
        "risk_flags": [
            "candidate_variant",
            "paper_demo_only",
            "needs_tournament_validation",
            f"data_quality:{variant['data_quality']}",
        ],
        "rr_ratio": 2.0,
        "daily_pnl_used": None,
        "open_positions_count": None,
        "rr_ok": True,
        "prices_ok": True,
        "daily_pnl_ok": True,
        "positions_ok": True,
        "no_duplicate": True,
        "rejection_reason": None,
        "trace_id": f"strategy_variant::{variant['strategy_id']}",
    }


def _variant_row(variant: dict[str, Any]) -> dict[str, Any]:
    parameter_set = {
        "strategy_id": variant["strategy_id"],
        "parent_strategy_id": variant["parent_strategy_id"],
        "variant_name": variant["variant_name"],
        "asset_class": variant["asset_class"],
        "symbol": variant["symbol"],
        "timeframe": variant["timeframe"],
        "preferred_side": variant["preferred_side"],
        "confidence": variant["confidence"],
        "entry_rules": variant["entry_rules"],
        "exit_rules": variant["exit_rules"],
        "stop_loss_rules": variant["stop_loss_rules"],
        "take_profit_rules": variant["take_profit_rules"],
        "risk_rules": variant["risk_rules"],
        "data_source": variant["data_source"],
        "data_quality": variant["data_quality"],
        "test_status": variant["test_status"],
        "hypothesis": variant["hypothesis"],
        "status": "candidate",
        "source_artifact": variant["source_artifact"],
        "source_references": variant["source_references"],
        "analysis_reasons": variant["analysis_reasons"],
        "memory_context": variant["memory_context"],
    }
    return {
        "id": _stable_uuid(f"variant::{variant['strategy_id']}"),
        "strategy_id": variant["strategy_id"],
        "variant_name": variant["variant_name"],
        "parameter_set": parameter_set,
        "backtest_score": None,
        "replay_score": None,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    seed_safe_trading_env_from_launch_agent()
    memory = _load_local_memory()
    proposal_trace_ids, risk_trace_ids, variant_keys = _existing_maps()
    variants = _augment_from_local_artifacts(_base_candidate_definitions(memory), memory)

    prepared_proposals: list[dict[str, Any]] = []
    prepared_risks: list[dict[str, Any]] = []
    prepared_variants: list[dict[str, Any]] = []
    duplicates_skipped = 0
    duplicates: list[str] = []

    for variant in variants:
        trace_id = f"strategy_variant::{variant['strategy_id']}"
        variant_key = f"{variant['strategy_id']}::{variant['variant_name']}"
        if trace_id in proposal_trace_ids or variant_key in variant_keys:
            duplicates_skipped += 1
            duplicates.append(variant["strategy_id"])
            continue
        proposal = _proposal_row(variant)
        risk = _risk_row(variant, proposal["id"])
        variant_row = _variant_row(variant)
        prepared_proposals.append(proposal)
        if trace_id not in risk_trace_ids:
            prepared_risks.append(risk)
        prepared_variants.append(variant_row)

    summary = {
        "generated_at": _now(),
        "dry_run": args.dry_run,
        "supabase_reachable": not bool(spb.SUPABASE_BLOCKER),
        "source_artifacts": {
            "tournament": str(ROOT / "logs" / "nexus_trading_tournament_latest.json"),
            "hermes_candidates": str(ROOT / "logs" / "hermes_supabase_strategy_candidates_latest.json"),
            "vibe_review_json": memory.get("vibe_path"),
            "vibe_review_md": memory.get("vibe_markdown_path"),
            "strategy_scores_rows": len(memory["strategy_scores"]),
            "paper_trades_rows": len(memory["paper_trades"]),
            "signals_rows": len(memory["signals"]),
        },
        "strategy_proposals_before": len(proposal_trace_ids),
        "strategy_variants_before": len(variant_keys),
        "new_candidates_created": len(prepared_variants),
        "candidates_testable": len(prepared_variants),
        "duplicates_skipped": duplicates_skipped,
        "duplicate_strategy_ids": duplicates,
        "strategy_ids": [row["strategy_id"] for row in prepared_variants],
        "tables": {},
    }

    summary["tables"]["reviewed_signal_proposals"] = _sb_post("reviewed_signal_proposals", prepared_proposals, dry_run=args.dry_run)
    summary["tables"]["risk_decisions"] = _sb_post("risk_decisions", prepared_risks, dry_run=args.dry_run)
    summary["tables"]["strategy_variants"] = _sb_post("strategy_variants", prepared_variants, dry_run=args.dry_run)

    ARTIFACT_FILE.write_text(json.dumps(summary, indent=2, default=str))
    lines = [
        "# Trading Memory Promotion",
        "",
        f"- Generated at: {summary['generated_at']}",
        f"- Dry run: {summary['dry_run']}",
        f"- Supabase reachable: {summary['supabase_reachable']}",
        f"- Strategy proposals before: {summary['strategy_proposals_before']}",
        f"- Strategy variants before: {summary['strategy_variants_before']}",
        f"- New candidates created: {summary['new_candidates_created']}",
        f"- Candidates testable: {summary['candidates_testable']}",
        f"- Duplicates skipped: {summary['duplicates_skipped']}",
        "",
        "## Strategy IDs",
    ]
    lines.extend([f"- {strategy_id}" for strategy_id in summary["strategy_ids"]])
    SUMMARY_FILE.write_text("\n".join(lines) + "\n")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
