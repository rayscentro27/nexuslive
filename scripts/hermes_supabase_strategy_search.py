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
sys.path.insert(0, str(ROOT / "scripts"))

from lib.trading_fallback_logger import append_jsonl, latest_jsonl
import strategy_paper_bridge as spb


LATEST_FILE = ROOT / "logs" / "hermes_supabase_strategy_candidates_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _label_strategy_name(strategy_id: str) -> str:
    return strategy_id.replace("_", " ").title()


def _dedupe(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str]] = set()
    deduped: list[dict[str, Any]] = []
    for row in rows:
        key = (str(row.get("strategy_id") or ""), str(row.get("source_id") or ""))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
    return deduped


def _infer_symbol(strategy_id: str, parameter_set: dict[str, Any]) -> str:
    symbol = str(parameter_set.get("symbol") or "").upper()
    if symbol:
        return symbol
    slug = strategy_id.upper()
    for candidate in ("EURUSD", "USDJPY", "GBPUSD", "BTCUSD", "ETHUSD", "SPY", "QQQ"):
        if candidate in slug:
            return candidate
    return "EURUSD"


def _synthetic_exit(proposal: dict[str, Any], replay_outcome: str) -> float:
    entry = float(proposal.get("entry_price") or 1.0)
    tp = proposal.get("take_profit")
    sl = proposal.get("stop_loss")
    side = str(proposal.get("side") or "BUY").upper()
    if replay_outcome in {"tp_hit", "win"} and tp not in (None, ""):
        return float(tp)
    if replay_outcome in {"loss", "sl_hit"} and sl not in (None, ""):
        return float(sl)
    drift = 0.002 if side == "BUY" else -0.002
    return round(entry + drift, 6)


def search_candidates(asset_class: str = "forex", limit: int = 20) -> dict[str, Any]:
    proposals, replay_results, risk_decisions, strategy_variants = spb.load_strategy_data()
    snapshot = spb.compute_strategy_snapshot(
        proposals,
        replay_results,
        risk_decisions,
        strategy_variants,
        min_rating=55.0,
        min_confidence=0.5,
        allow_manual_review=True,
        allow_breakeven=True,
    )

    proposals_by_id = {row.get("id"): row for row in proposals if row.get("id")}
    latest_replay = spb.latest_by_key(spb.canonical_replays_by_proposal(replay_results), "proposal_id")
    candidates: list[dict[str, Any]] = []

    for eligible in snapshot.get("eligible_candidates", []):
        proposal = proposals_by_id.get(eligible.get("proposal_id")) or {}
        row_asset = str(proposal.get("asset_type") or eligible.get("asset_type") or "forex").lower()
        if asset_class != "all" and row_asset != asset_class:
            continue
        replay = latest_replay.get(eligible.get("proposal_id"), {})
        strategy_id = str(eligible.get("strategy_id") or "unknown")
        signal_payload = dict(eligible.get("signal_payload") or {})
        signal_payload.setdefault("position_size", 0.01)
        signal_payload.setdefault("units", 1)
        signal_payload.setdefault("asset_class", row_asset)
        signal_payload.setdefault("strategy_id", strategy_id)
        signal_payload.setdefault("entry_reason", "supabase_strategy_candidate")
        synthetic_signal = {
            "symbol": signal_payload.get("symbol"),
            "action": signal_payload.get("action"),
            "entry_price": signal_payload.get("entry_price"),
            "stop_loss": signal_payload.get("stop_loss"),
            "take_profit": signal_payload.get("take_profit"),
            "exit_price": _synthetic_exit(proposal, replay.get("replay_outcome", "breakeven")),
            "timestamp": proposal.get("created_at") or _now(),
            "position_size": signal_payload.get("position_size", 0.01),
        }
        candidates.append(
            {
                "strategy_id": strategy_id,
                "strategy_name": _label_strategy_name(strategy_id),
                "strategy_source": "supabase" if not spb.SUPABASE_BLOCKER else "local",
                "source_id": eligible.get("proposal_id"),
                "data_quality": "historical_data" if not spb.SUPABASE_BLOCKER else "local_fallback_data",
                "asset_class": row_asset,
                "symbol": eligible.get("symbol"),
                "timeframe": signal_payload.get("timeframe", "H1"),
                "confidence": eligible.get("ai_confidence"),
                "score": eligible.get("strategy_rating"),
                "test_status": "tested",
                "promotion_decision": "paper_candidate",
                "rules_summary": {
                    "side": eligible.get("side"),
                    "entry_price": signal_payload.get("entry_price"),
                    "stop_loss": signal_payload.get("stop_loss"),
                    "take_profit": signal_payload.get("take_profit"),
                    "risk_decision": eligible.get("risk_decision"),
                    "replay_outcome": eligible.get("replay_outcome"),
                },
                "recommended_signal": signal_payload,
                "signals": [synthetic_signal],
            }
        )

    latest_risk = spb.latest_by_key(risk_decisions, "proposal_id")
    replay_proposal_ids = {row.get("proposal_id") for row in spb.canonical_replays_by_proposal(replay_results)}
    for proposal_id, proposal in proposals_by_id.items():
        if proposal_id in replay_proposal_ids:
            continue
        row_asset = str(proposal.get("asset_type") or "forex").lower()
        if asset_class != "all" and row_asset != asset_class:
            continue
        decision = (latest_risk.get(proposal_id) or {}).get("decision")
        if decision == "blocked":
            continue
        strategy_id = str(proposal.get("strategy_id") or "unknown")
        signal_payload = {
            "symbol": proposal.get("symbol"),
            "action": str(proposal.get("side") or "BUY").upper(),
            "entry_price": proposal.get("entry_price"),
            "stop_loss": proposal.get("stop_loss"),
            "take_profit": proposal.get("take_profit"),
            "timeframe": proposal.get("timeframe") or "H1",
            "strategy": strategy_id,
            "strategy_id": strategy_id,
            "confidence": int(spb.safe_float(proposal.get("ai_confidence"), 0.65) * 100),
            "entry_reason": "supabase_strategy_proposal",
            "asset_class": row_asset,
            "position_size": 0.01,
            "units": 1,
        }
        candidates.append(
            {
                "strategy_id": strategy_id,
                "strategy_name": _label_strategy_name(strategy_id),
                "strategy_source": "supabase_proposal",
                "source_id": proposal_id,
                "data_quality": "proposal_candidate",
                "asset_class": row_asset,
                "symbol": proposal.get("symbol"),
                "timeframe": proposal.get("timeframe") or "H1",
                "confidence": proposal.get("ai_confidence"),
                "score": spb.safe_float((latest_risk.get(proposal_id) or {}).get("risk_score"), 60.0),
                "test_status": "untested",
                "promotion_decision": "candidate",
                "rules_summary": {
                    "market_context": proposal.get("market_context"),
                    "research_context": proposal.get("research_context"),
                    "risk_notes": proposal.get("risk_notes"),
                    "recommendation": proposal.get("recommendation"),
                    "risk_decision": decision or "pending",
                },
                "recommended_signal": signal_payload,
                "signals": [],
            }
        )

    existing_keys = {(str(row.get("strategy_id") or ""), str(row.get("source_id") or "")) for row in candidates}
    for variant in strategy_variants:
        parameter_set = dict(variant.get("parameter_set") or {})
        row_asset = str(parameter_set.get("asset_class") or "forex").lower()
        if asset_class != "all" and row_asset != asset_class:
            continue
        strategy_id = str(parameter_set.get("strategy_id") or variant.get("strategy_id") or "unknown")
        source_id = str(variant.get("id") or f"{strategy_id}:{variant.get('variant_name')}")
        if (strategy_id, source_id) in existing_keys:
            continue
        symbol = _infer_symbol(strategy_id, parameter_set)
        timeframe = str(parameter_set.get("timeframe") or "H1")
        confidence = spb.safe_float(parameter_set.get("confidence"), 0.68)
        candidates.append(
            {
                "strategy_id": strategy_id,
                "strategy_name": _label_strategy_name(strategy_id),
                "strategy_source": "supabase_variant",
                "source_id": source_id,
                "data_quality": str(parameter_set.get("data_quality") or "variant_candidate"),
                "asset_class": row_asset,
                "symbol": symbol,
                "timeframe": timeframe,
                "confidence": confidence,
                "score": spb.safe_float(variant.get("replay_score"), spb.safe_float(variant.get("backtest_score"), 55.0)),
                "test_status": str(parameter_set.get("test_status") or "untested"),
                "promotion_decision": "candidate",
                "rules_summary": {
                    "variant_name": variant.get("variant_name"),
                    "parent_strategy_id": parameter_set.get("parent_strategy_id"),
                    "hypothesis": parameter_set.get("hypothesis"),
                    "entry_rules": parameter_set.get("entry_rules"),
                    "exit_rules": parameter_set.get("exit_rules"),
                    "stop_loss_rules": parameter_set.get("stop_loss_rules"),
                    "take_profit_rules": parameter_set.get("take_profit_rules"),
                    "risk_rules": parameter_set.get("risk_rules"),
                    "source_artifact": parameter_set.get("source_artifact"),
                },
                "recommended_signal": {
                    "symbol": symbol,
                    "action": str(parameter_set.get("preferred_side") or "BUY").upper(),
                    "timeframe": timeframe,
                    "strategy": strategy_id,
                    "strategy_id": strategy_id,
                    "confidence": int(confidence * 100),
                    "entry_reason": "supabase_strategy_variant",
                    "asset_class": row_asset,
                    "position_size": 0.01,
                    "units": 1,
                },
                "signals": [],
            }
        )

    if not candidates:
        for row in latest_jsonl("strategy_scores", limit=limit * 3):
            row_asset = str(row.get("asset_class") or "forex").lower()
            if asset_class != "all" and row_asset != asset_class:
                continue
            symbol = str(row.get("symbol") or "EURUSD")
            candidates.append(
                {
                    "strategy_id": row.get("strategy_id"),
                    "strategy_name": row.get("strategy_name") or _label_strategy_name(str(row.get("strategy_id") or "local_strategy")),
                    "strategy_source": "local",
                    "source_id": row.get("strategy_id"),
                    "data_quality": row.get("data_quality", "local_sample_data"),
                    "asset_class": row_asset,
                    "symbol": symbol,
                    "timeframe": row.get("timeframe", "H1"),
                    "confidence": row.get("win_rate", 0.5),
                    "score": row.get("stability_score", row.get("profit_factor", 0)),
                    "test_status": "tested",
                    "promotion_decision": "paper_candidate" if row.get("paper_active") else "needs_review",
                    "rules_summary": {
                        "rank": row.get("rank"),
                        "profit_factor": row.get("profit_factor"),
                        "max_drawdown": row.get("max_drawdown"),
                        "win_rate": row.get("win_rate"),
                    },
                    "recommended_signal": {
                        "symbol": symbol,
                        "action": "BUY",
                        "timeframe": row.get("timeframe", "H1"),
                        "strategy": row.get("strategy_id"),
                        "strategy_id": row.get("strategy_id"),
                        "confidence": int(float(row.get("win_rate", 0.5)) * 100),
                        "entry_reason": "local_strategy_score_fallback",
                        "asset_class": row_asset,
                        "position_size": 0.01,
                        "units": 1,
                    },
                    "signals": [],
                }
            )

    candidates = _dedupe(candidates)[:limit]
    result = {
        "generated_at": _now(),
        "supabase_reachable": not bool(spb.SUPABASE_BLOCKER),
        "fallback_used": bool(spb.SUPABASE_BLOCKER),
        "blocker": spb.SUPABASE_BLOCKER,
        "tables_found": [
            "reviewed_signal_proposals",
            "replay_results",
            "risk_decisions",
            "strategy_variants",
        ],
        "strategy_rows_found": {
            "proposals": len(proposals),
            "replays": len(replay_results),
            "risk_decisions": len(risk_decisions),
            "strategy_variants": len(strategy_variants),
        },
        "candidates_extracted": len(candidates),
        "candidates_testable": len([c for c in candidates if c.get("test_status") == "tested"]),
        "candidates": candidates,
        "snapshot_summary": snapshot.get("summary", {}),
        "supabase_logging": snapshot.get("supabase_logging"),
    }
    LATEST_FILE.write_text(json.dumps(result, indent=2, default=str))
    append_jsonl("reports", {
        "created_at": _now(),
        "report_type": "hermes_supabase_strategy_search",
        "mode": "paper",
        "receiver_status": "n/a",
        "broker_status": "demo",
        "live_trading_enabled": False,
        "paper_trading_enabled": True,
        "strategies_tested": result["candidates_testable"],
        "summary": "Hermes Supabase-first strategy search",
        "blockers": [result["blocker"]] if result.get("blocker") else [],
        "verified_facts": {
            "supabase_reachable": result["supabase_reachable"],
            "fallback_used": result["fallback_used"],
            "candidates_extracted": result["candidates_extracted"],
        },
    })
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--asset-class", default="forex")
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()
    result = search_candidates(asset_class=args.asset_class, limit=args.limit)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
