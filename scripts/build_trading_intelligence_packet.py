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
from lib.trading_intelligence_lab import build_trading_intelligence_report
from lib.trading_market_data import resolve_market_data_bundle


OUTPUT_JSON = ROOT / "logs" / "trading_intelligence_packet_latest.json"
OUTPUT_MD = ROOT / "logs" / "trading_intelligence_packet_latest.md"
DEFAULT_LANES = {
    "forex": ["EURUSD", "USDJPY", "GBPUSD"],
    "crypto": ["BTC", "ETH"],
    "stocks": ["SPY", "QQQ"],
    "options": ["SPY", "QQQ"],
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text())
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _score_expected_value(entry: dict[str, Any]) -> dict[str, Any]:
    win_rate = _safe_float(entry.get("win_rate"), 0.0)
    profit_factor = _safe_float(entry.get("profit_factor"), 0.0)
    avg_return = _safe_float(entry.get("avg_return"), 0.0)
    trades_count = int(entry.get("trades_count") or 0)
    rr_bonus = min(2.0, profit_factor) / 2.0
    confidence = min(1.0, trades_count / 10.0)
    ev = round((win_rate * rr_bonus * 100.0) + avg_return, 2)
    return {
        "strategy_id": entry.get("strategy_id"),
        "symbol": entry.get("symbol"),
        "asset_class": entry.get("asset_class"),
        "expected_value_score": ev,
        "confidence_weight": round(confidence, 2),
        "promotion_decision": entry.get("promotion_decision"),
        "trades_count": trades_count,
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "rank": entry.get("rank"),
    }


def _market_snapshot(symbol: str, asset_class: str) -> dict[str, Any]:
    preferred = "oanda_practice" if asset_class == "forex" else "fallback_sample"
    bundle = resolve_market_data_bundle(
        symbol,
        timeframe="M15" if asset_class == "forex" else "H1",
        lookback=48,
        preferred_source=preferred,
        allow_fallback=True,
    )
    candles = bundle.get("candles") or []
    return {
        "symbol": symbol,
        "asset_class": asset_class,
        "data_source": bundle.get("source"),
        "data_quality": bundle.get("data_quality"),
        "candle_count": bundle.get("candle_count", len(candles)),
        "fallback_reason": bundle.get("fallback_reason"),
        "latest_candle_time": candles[-1].get("time") if candles else None,
    }


def build_packet(*, dry_run: bool = False) -> dict[str, Any]:
    tournament = _load_json(ROOT / "logs" / "nexus_trading_tournament_latest.json")
    candidates = _load_json(ROOT / "logs" / "hermes_supabase_strategy_candidates_latest.json")
    discovery = _load_json(ROOT / "logs" / "trading_strategy_discovery_latest.json")
    watch = _load_json(ROOT / "logs" / "live_watch" / "trading_watch_session_latest.json")
    replay = ROOT / "logs" / "charts" / "trade_replay_latest.html"
    vibe_rows = [row for row in latest_jsonl("reports", limit=50) if row.get("report_type") == "strategy_tournament"]
    score_rows = latest_jsonl("strategy_scores", limit=200)

    ev_map: dict[tuple[str, str], dict[str, Any]] = {}
    for row in score_rows:
        scored = _score_expected_value(row)
        key = (str(scored.get("strategy_id") or ""), str(scored.get("symbol") or ""))
        current = ev_map.get(key)
        if current is None or scored["expected_value_score"] > current["expected_value_score"]:
            ev_map[key] = scored
    ev_scores = sorted(ev_map.values(), key=lambda row: (-row["expected_value_score"], int(row.get("rank") or 9999)))
    asset_lanes = []
    for asset_class, symbols in DEFAULT_LANES.items():
        asset_lanes.append(
            {
                "asset_class": asset_class,
                "symbols": symbols,
                "execution_mode": "oanda_practice_or_local_paper" if asset_class == "forex" else "local_paper_only",
                "market_snapshots": [_market_snapshot(symbol, asset_class) for symbol in symbols],
            }
        )

    packet = {
        "generated_at": _now(),
        "dry_run": dry_run,
        "lab_report": build_trading_intelligence_report(),
        "strategy_discovery_summary": {
            "candidates_discovered": discovery.get("candidates_discovered"),
            "candidates_testable": discovery.get("candidates_testable"),
            "artifact": str(ROOT / "logs" / "trading_strategy_discovery_latest.json"),
        },
        "supabase_candidate_summary": {
            "count": len(candidates.get("candidates") or []),
            "fallback_used": candidates.get("fallback_used"),
            "artifact": str(ROOT / "logs" / "hermes_supabase_strategy_candidates_latest.json"),
        },
        "tournament_summary": {
            "top_strategy": tournament.get("top_strategy"),
            "top_candidate_for_next_cap_reset": tournament.get("top_candidate_for_next_cap_reset"),
            "strategies_tested": len(tournament.get("strategies") or []),
            "artifact": str(ROOT / "logs" / "nexus_trading_tournament_latest.json"),
        },
        "expected_value_scores": ev_scores[:20],
        "asset_lanes": asset_lanes,
        "live_watch_summary": {
            "session_name": watch.get("session_name"),
            "setup_detected": watch.get("setup_detected"),
            "artifact": str(ROOT / "logs" / "live_watch" / "trading_watch_session_latest.json"),
        },
        "replay_chart_path": str(replay) if replay.exists() else None,
        "latest_tournament_report": vibe_rows[-1] if vibe_rows else None,
    }
    return packet


def _write_markdown(packet: dict[str, Any]) -> None:
    lines = [
        "# Trading Intelligence Packet",
        "",
        f"- Generated at: `{packet.get('generated_at')}`",
        f"- Dry run: `{'yes' if packet.get('dry_run') else 'no'}`",
        f"- Discovery candidates: `{(packet.get('strategy_discovery_summary') or {}).get('candidates_discovered', 'unknown')}`",
        f"- Supabase candidates: `{(packet.get('supabase_candidate_summary') or {}).get('count', 'unknown')}`",
        f"- Tournament strategies tested: `{(packet.get('tournament_summary') or {}).get('strategies_tested', 'unknown')}`",
        f"- Replay chart: `{packet.get('replay_chart_path') or 'not_generated'}`",
        "",
        "## Top Expected Value",
    ]
    for row in (packet.get("expected_value_scores") or [])[:10]:
        lines.append(
            f"- `{row.get('asset_class')}` `{row.get('symbol')}` `{row.get('strategy_id')}` "
            f"ev=`{row.get('expected_value_score')}` trades=`{row.get('trades_count')}` "
            f"decision=`{row.get('promotion_decision')}`"
        )
    lines.append("")
    lines.append("## Asset Lanes")
    for lane in packet.get("asset_lanes") or []:
        lines.append(
            f"- `{lane.get('asset_class')}` symbols=`{', '.join(lane.get('symbols') or [])}` "
            f"execution_mode=`{lane.get('execution_mode')}`"
        )
    OUTPUT_MD.write_text("\n".join(lines) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    packet = build_packet(dry_run=args.dry_run)
    OUTPUT_JSON.write_text(json.dumps(packet, indent=2, default=str))
    _write_markdown(packet)
    print(json.dumps({"json": str(OUTPUT_JSON), "markdown": str(OUTPUT_MD), "top_ev": (packet.get("expected_value_scores") or [None])[0]}, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
