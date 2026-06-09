#!/usr/bin/env python3
from __future__ import annotations

import argparse
import glob
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib.trading_fallback_logger import latest_jsonl


ARTIFACT_JSON = ROOT / "logs" / "trading_strategy_discovery_latest.json"
ARTIFACT_MD = ROOT / "logs" / "trading_strategy_discovery_latest.md"
INVENTORY_MD = ROOT / "logs" / "trading_strategy_scout_visual_inventory_latest.md"
SOURCE_REGISTRY = ROOT / "configs" / "trading_strategy_sources.json"


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


def _load_json_list(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text())
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _classify(strategy_id: str, summary: str = "") -> tuple[str, str, str]:
    text = f"{strategy_id} {summary}".lower()
    if any(token in text for token in ("cpi", "nfp", "fomc", "news")):
        return "news_event", "news_calendar_event", "event_window"
    if "breakout" in text or "open" in text or "session" in text:
        return "session_open" if "open" in text else "breakout", "scheduled_session", "event_window"
    if "mean_reversion" in text or "bollinger" in text:
        return "mean_reversion", "continuous_indicator", "always_on"
    if "pullback" in text or "trend" in text:
        return "trend_following", "continuous_indicator", "always_on"
    if "hybrid" in text:
        return "hybrid", "manual_review_only", "tournament_only"
    return "technical_indicator", "continuous_indicator", "always_on"


def _symbols_from_text(text: str) -> list[str]:
    out: list[str] = []
    for symbol in ("EURUSD", "USDJPY", "GBPUSD", "BTCUSD", "ETHUSD", "SPY", "QQQ"):
        if symbol in text.upper().replace("_", ""):
            out.append(symbol)
    return out or ["EURUSD"]


def _candidate_key(row: dict[str, Any]) -> tuple[str, str]:
    return (str(row.get("strategy_id") or ""), str(row.get("source_url") or row.get("source_title") or row.get("source_type") or ""))


def _to_candidate(strategy_id: str, *, symbol: str, timeframe: str, source_type: str, source_url: str, source_title: str, summary: str, rules: dict[str, Any], status: str, raw_text: str, source_channel: str = "", notes: str = "", source_date: str | None = None) -> dict[str, Any]:
    family, trigger, execution_style = _classify(strategy_id, summary)
    testability = 0.85 if any(rules.get(k) for k in ("entry_rules", "exit_rules", "stop_loss_rules", "take_profit_rules")) else 0.35
    clarity = 0.8 if summary else 0.4
    confidence = float(rules.get("confidence") or rules.get("ai_confidence") or 0.65)
    risk_score = float(rules.get("risk_score") or 65)
    return {
        "strategy_id": strategy_id,
        "strategy_name": strategy_id.replace("_", " ").title(),
        "asset_class": "forex" if symbol in {"EURUSD", "USDJPY", "GBPUSD"} else "unknown",
        "symbols": [symbol],
        "timeframe": timeframe,
        "strategy_family": family,
        "trigger_type": trigger,
        "execution_style": execution_style,
        "source_type": source_type,
        "source_url": source_url,
        "source_title": source_title,
        "source_channel": source_channel,
        "source_date": source_date,
        "summary": summary,
        "entry_rules": rules.get("entry_rules"),
        "exit_rules": rules.get("exit_rules"),
        "stop_loss_rules": rules.get("stop_loss_rules"),
        "take_profit_rules": rules.get("take_profit_rules"),
        "risk_management_rules": rules.get("risk_rules") or rules.get("risk_management_rules"),
        "session_rules": rules.get("session_rules"),
        "news_event_rules": rules.get("news_event_rules"),
        "indicators_used": rules.get("indicators_used") or [],
        "invalidation_rules": rules.get("invalidation_rules"),
        "required_data": rules.get("required_data") or ["candles"],
        "testability_score": round(testability, 2),
        "clarity_score": round(clarity, 2),
        "risk_score": round(risk_score, 2),
        "confidence_score": round(confidence, 2),
        "status": status,
        "notes": notes,
        "raw_extracted_text": raw_text[:4000],
        "created_at": _now(),
    }


def _load_registry() -> list[dict[str, Any]]:
    return _load_json_list(SOURCE_REGISTRY)


def _discover_from_supabase_artifacts() -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    supabase_snapshot = _load_json(ROOT / "logs" / "hermes_supabase_strategy_candidates_latest.json")
    for row in supabase_snapshot.get("candidates") or []:
        strategy_id = str(row.get("strategy_id") or "unknown")
        summary = json.dumps(row.get("rules_summary") or {}, default=str)
        symbol = str(row.get("symbol") or "EURUSD").upper().replace("_", "")
        rules_summary = row.get("rules_summary") or {}
        rules = {
            "entry_rules": json.dumps(rules_summary.get("entry_rules") or rules_summary.get("entry_price") or rules_summary, default=str),
            "exit_rules": json.dumps(rules_summary.get("exit_rules") or rules_summary.get("replay_outcome") or {}, default=str),
            "stop_loss_rules": rules_summary.get("stop_loss_rules") or rules_summary.get("stop_loss"),
            "take_profit_rules": rules_summary.get("take_profit_rules") or rules_summary.get("take_profit"),
            "risk_rules": rules_summary.get("risk_rules") or rules_summary.get("risk_decision"),
            "confidence": row.get("confidence"),
            "risk_score": row.get("score"),
        }
        candidates.append(
            _to_candidate(
                strategy_id,
                symbol=symbol,
                timeframe=str(row.get("timeframe") or "H1"),
                source_type="supabase",
                source_url="logs/hermes_supabase_strategy_candidates_latest.json",
                source_title="Supabase strategy candidates snapshot",
                summary=summary,
                rules=rules,
                status="promoted_for_tournament" if row.get("test_status") == "tested" else "testable_candidate",
                raw_text=summary,
                notes=f"strategy_source={row.get('strategy_source')} promotion_decision={row.get('promotion_decision')}",
            )
        )
    promotion = _load_json(ROOT / "logs" / "trading_memory_supabase_promotion_latest.json")
    for row in promotion.get("candidates") or []:
        strategy_id = str(row.get("strategy_id") or "unknown")
        symbol = str(row.get("symbol") or "EURUSD").upper().replace("_", "")
        rules = {
            "entry_rules": row.get("entry_rules"),
            "exit_rules": row.get("exit_rules"),
            "stop_loss_rules": row.get("stop_loss_rules"),
            "take_profit_rules": row.get("take_profit_rules"),
            "risk_rules": row.get("risk_rules"),
            "confidence": row.get("confidence"),
            "risk_score": row.get("risk_score"),
        }
        candidates.append(
            _to_candidate(
                strategy_id,
                symbol=symbol,
                timeframe=str(row.get("timeframe") or "H1"),
                source_type="supabase",
                source_url="logs/trading_memory_supabase_promotion_latest.json",
                source_title="Promoted trading memory candidates",
                summary=str(row.get("hypothesis") or row.get("variant_name") or ""),
                rules=rules,
                status="testable_candidate",
                raw_text=json.dumps(row, default=str),
                notes=f"parent_strategy_id={row.get('parent_strategy_id')}",
            )
        )
    return candidates


def _discover_from_local_reports() -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    tournament = _load_json(ROOT / "logs" / "nexus_trading_tournament_latest.json")
    for row in tournament.get("strategies") or []:
        strategy_id = str(row.get("strategy_id") or "unknown")
        symbol = str(row.get("symbol") or _symbols_from_text(strategy_id)[0]).upper().replace("_", "")
        summary = "; ".join(row.get("analysis_reasons") or []) or str(row.get("reason") or "")
        rules = {
            "entry_rules": json.dumps(row.get("entry_rules") or row.get("signals") or [], default=str),
            "exit_rules": row.get("promotion_reason") or row.get("promotion_decision"),
            "risk_rules": f"trades_count={row.get('trades_count')} max_drawdown={row.get('max_drawdown')}",
            "risk_score": row.get("profit_factor") or 50,
            "confidence": row.get("win_rate") or 0.5,
        }
        status = "promoted_for_practice" if row.get("promotion_decision") in {"promoted", "promoted_for_next_cap_reset"} else "testable_candidate"
        candidates.append(
            _to_candidate(
                strategy_id,
                symbol=symbol,
                timeframe=str(row.get("timeframe") or "H1"),
                source_type="local_file",
                source_url="logs/nexus_trading_tournament_latest.json",
                source_title="Latest Nexus tournament",
                summary=summary,
                rules=rules,
                status=status,
                raw_text=json.dumps(row, default=str),
                notes=f"data_source={row.get('data_source')} data_quality={row.get('data_quality')}",
            )
        )
    vibe_paths = sorted(glob.glob(str(ROOT / "integrations" / "vibe_trading" / "reports" / "vibe_strategy_review_*.json")))
    if vibe_paths:
        vibe_path = Path(vibe_paths[-1])
        vibe = _load_json(vibe_path)
        for recommendation in vibe.get("recommendations") or []:
            name = str(recommendation).lower().replace(" ", "_")[:64] or "vibe_candidate"
            symbol = _symbols_from_text(recommendation)[0]
            candidates.append(
                _to_candidate(
                    name,
                    symbol=symbol,
                    timeframe="H1",
                    source_type="vibe_report",
                    source_url=str(vibe_path.relative_to(ROOT)),
                    source_title=vibe_path.name,
                    summary=str(recommendation),
                    rules={},
                    status="needs_research",
                    raw_text=str(recommendation),
                    notes="Vibe recommendation needs fuller rule extraction before tournament submission.",
                )
            )
    for row in latest_jsonl("market_scan", limit=50):
        strategy_id = f"{str(row.get('symbol') or 'eurusd').lower()}_{str(row.get('recommended_strategy_family') or 'scanner')}"
        symbol = str(row.get("symbol") or "EURUSD").upper().replace("_", "")
        candidates.append(
            _to_candidate(
                strategy_id,
                symbol=symbol,
                timeframe="H1",
                source_type="local_file",
                source_url="logs/nexus_market_scan_results_YYYYMMDD.jsonl",
                source_title="Market scan results",
                summary=str(row.get("reason") or ""),
                rules={
                    "required_data": ["candles", "volatility", "trend"],
                    "risk_rules": f"scanner_confidence={row.get('confidence')}",
                    "confidence": row.get("confidence"),
                    "risk_score": (row.get("trend_score") or 0.5) * 100,
                },
                status="needs_research",
                raw_text=json.dumps(row, default=str),
                notes=f"data_quality={row.get('data_quality')}",
            )
        )
    return candidates


def _discover_from_local_youtube() -> list[dict[str, Any]]:
    registry_path = ROOT / "docs" / "reports" / "youtube" / "source_registry.json"
    registry = _load_json(registry_path)
    candidates: list[dict[str, Any]] = []
    for row in registry.get("items") or []:
        title = str(row.get("title") or "")
        if "trade" not in title.lower() and "forex" not in title.lower():
            continue
        strategy_id = title.lower().replace(" ", "_")[:64]
        symbol = _symbols_from_text(title)[0]
        candidates.append(
            _to_candidate(
                strategy_id,
                symbol=symbol,
                timeframe="H1",
                source_type="youtube_channel",
                source_url=str(row.get("url") or ""),
                source_title=title or "youtube_strategy_source",
                summary=str(row.get("notes") or title),
                rules={},
                status="needs_research",
                raw_text=json.dumps(row, default=str),
                source_channel=str(row.get("channel_name") or ""),
                notes="YouTube registry item found locally; transcript/rules extraction not yet attached here.",
                source_date=row.get("submitted_at"),
            )
        )
    return candidates


def _dedupe(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    seen: set[tuple[str, str]] = set()
    deduped: list[dict[str, Any]] = []
    skipped = 0
    for row in rows:
        key = _candidate_key(row)
        if key in seen:
            skipped += 1
            continue
        seen.add(key)
        deduped.append(row)
    return deduped, skipped


def build_inventory_report() -> str:
    lines = [
        "# Trading Strategy Scout / Visual Inventory",
        "",
        "## Existing Scouts Found",
        "- `lib/hermes_scout_dispatcher.py`: already contains the `trading_strategy` route. Extend this route instead of creating a parallel scout dispatcher.",
        "- `lib/youtube_source_registry.py`: existing source registry for YouTube intake and status tracking.",
        "- `lib/youtube_quality_reviewer.py`: existing YouTube quality scoring/review path.",
        "- `lib/youtube_intelligence_extractor.py`: existing transcript extraction path for structured research artifacts.",
        "- `scripts/run_market_scan.py`: existing market scan artifact producer using `lib.trading_market_data`.",
        "",
        "## Existing Strategy / Research Paths",
        "- `scripts/hermes_supabase_strategy_search.py`: existing Supabase-first strategy candidate search snapshot.",
        "- `scripts/promote_trading_memory_to_supabase_strategies.py`: existing promotion path from local verified memory into Supabase strategy tables.",
        "- `scripts/strategy_paper_bridge.py`: existing bridge for `reviewed_signal_proposals`, `replay_results`, `risk_decisions`, and `strategy_variants`.",
        "- `scripts/run_vibe_trading_review.py`: existing Vibe Trading review runner.",
        "- `integrations/vibe_trading/`: existing local review/backtest integration.",
        "",
        "## Existing Dashboard / Replay Components",
        "- `dashboard.py`: existing generic trading dashboard that should be linked to, not replaced.",
        "- `workflows/replay_lab/`: existing replay lab assets for broader replay workflows.",
        "- No dedicated local `start_trading_watch_session.py` or `generate_trade_replay_chart.py` existed before this run.",
        "",
        "## Existing Supabase Tables / Migrations Found",
        "- `reviewed_signal_proposals`",
        "- `risk_decisions`",
        "- `paper_trade_runs`",
        "- `replay_results`",
        "- `strategy_variants`",
        "- `research_artifacts` and related research tables in docs/migrations",
        "",
        "## Trade / Tournament Artifacts Found",
        "- `logs/hermes_supabase_strategy_candidates_latest.json`",
        "- `logs/nexus_trading_tournament_latest.json`",
        "- `logs/trading_memory_supabase_promotion_latest.json`",
        "- `logs/nexus_market_scan_results_*.jsonl`",
        "- `logs/nexus_paper_trades_*.jsonl`",
        "- `logs/nexus_strategy_scores_*.jsonl`",
        "",
        "## Extend, Do Not Duplicate",
        "- Extend the existing strategy bridge and promotion artifacts for discovery seeding.",
        "- Reuse `lib.trading_market_data.generate_strategy_signals_from_candles` inside watcher adapters.",
        "- Keep `run_nexus_demo_trading_loop.py` as the normal execution path for practice orders.",
        "- Link Hermes to new watch/replay artifacts rather than building a second dashboard backend.",
        "",
        "## Proposed Integration Points",
        "- `scripts/discover_trading_strategies.py`: unified local/Supabase/Vibe discovery wrapper.",
        "- `lib/trading_strategy_watchers.py`: normalized watcher interface over existing candle logic.",
        "- `lib/trading_live_watch.py` + `scripts/start_trading_watch_session.py`: lightweight watch session artifacts.",
        "- `lib/trading_visuals.py` + `scripts/generate_trade_replay_chart.py`: lightweight local replay/dashboard artifacts.",
        "- `lib/hermes_internal_first.py`: surface the new artifact paths for replay/watch queries.",
        "",
        "Duplicate systems avoided: yes.",
    ]
    content = "\n".join(lines) + "\n"
    INVENTORY_MD.write_text(content)
    return content


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--asset-class", default="forex")
    parser.add_argument("--source", choices=("all", "local", "supabase"), default="all")
    parser.add_argument("--keywords", default="")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    build_inventory_report()
    registry = _load_registry()
    discovered: list[dict[str, Any]] = []
    if args.source in {"all", "supabase"}:
        discovered.extend(_discover_from_supabase_artifacts())
    if args.source in {"all", "local"}:
        discovered.extend(_discover_from_local_reports())
        discovered.extend(_discover_from_local_youtube())
    if args.keywords.strip():
        for keyword in [part.strip() for part in args.keywords.split(",") if part.strip()]:
            strategy_id = keyword.lower().replace(" ", "_")[:64]
            symbol = _symbols_from_text(keyword)[0]
            discovered.append(
                _to_candidate(
                    strategy_id,
                    symbol=symbol,
                    timeframe="H1",
                    source_type="youtube_search",
                    source_url=keyword,
                    source_title="Keyword adapter seed",
                    summary=keyword,
                    rules={},
                    status="needs_research",
                    raw_text=keyword,
                    notes="Search adapter seed only; external search not invoked in this run.",
                )
            )
    filtered = [row for row in discovered if row.get("asset_class") == args.asset_class]
    deduped, duplicates_skipped = _dedupe(filtered)
    testable = [row for row in deduped if row.get("status") in {"testable_candidate", "promoted_for_tournament", "promoted_for_practice"}]
    payload = {
        "generated_at": _now(),
        "asset_class": args.asset_class,
        "source_mode": args.source,
        "dry_run": args.dry_run,
        "registry_sources": len(registry),
        "youtube_search_adapter_available": False,
        "google_search_adapter_available": False,
        "supabase_mining_available": True,
        "local_mining_available": True,
        "duplicates_skipped": duplicates_skipped,
        "candidates_discovered": len(deduped),
        "candidates_testable": len(testable),
        "candidates": deduped,
        "inventory_artifact": str(INVENTORY_MD),
    }
    ARTIFACT_JSON.write_text(json.dumps(payload, indent=2))
    lines = [
        "# Trading Strategy Discovery",
        "",
        f"- Asset class: `{args.asset_class}`",
        f"- Source mode: `{args.source}`",
        f"- Dry run: `{'yes' if args.dry_run else 'no'}`",
        f"- Sources configured: `{len(registry)}`",
        f"- Candidates discovered: `{len(deduped)}`",
        f"- Testable candidates: `{len(testable)}`",
        f"- Duplicates skipped: `{duplicates_skipped}`",
        f"- Inventory artifact: `{INVENTORY_MD}`",
        "",
        "## Top Candidates",
    ]
    for row in deduped[:12]:
        lines.append(
            f"- `{row['strategy_id']}` source=`{row['source_type']}` "
            f"family=`{row['strategy_family']}` trigger=`{row['trigger_type']}` "
            f"status=`{row['status']}` symbol=`{','.join(row['symbols'])}`"
        )
    ARTIFACT_MD.write_text("\n".join(lines) + "\n")
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
