#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib.autonomous_demo_trading_lab import build_demo_status_snapshot
from lib.trading_fallback_logger import jsonl_path, latest_jsonl
from lib.trading_safety_gate import evaluate_trading_safety


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    safety = evaluate_trading_safety()
    demo = build_demo_status_snapshot()
    status_file = ROOT / "logs" / "trading_engine_status.json"
    saved = {}
    if status_file.exists():
        try:
            saved = json.loads(status_file.read_text())
        except Exception:
            saved = {}
    tournament_file = ROOT / "logs" / "nexus_trading_tournament_latest.json"
    tournament = {}
    if tournament_file.exists():
        try:
            tournament = json.loads(tournament_file.read_text())
        except Exception:
            tournament = {}
    loop_file = ROOT / "logs" / "nexus_demo_trading_loop_latest.json"
    loop = {}
    if loop_file.exists():
        try:
            loop = json.loads(loop_file.read_text())
        except Exception:
            loop = {}
    oanda_rows = [r for r in latest_jsonl("reports", limit=50) if r.get("report_type") == "oanda_practice_check"]
    oanda = (oanda_rows[-1].get("verified_facts") if oanda_rows else {}) or {}
    bridge_rows = [r for r in latest_jsonl("reports", limit=50) if r.get("report_type") == "strategy_paper_bridge_snapshot"]
    bridge = bridge_rows[-1] if bridge_rows else {}
    strategy_file = ROOT / "logs" / "hermes_supabase_strategy_candidates_latest.json"
    strategy_memory = {}
    if strategy_file.exists():
        try:
            strategy_memory = json.loads(strategy_file.read_text())
        except Exception:
            strategy_memory = {}
    vibe_dir = ROOT / "integrations" / "vibe_trading" / "reports"
    vibe_files = sorted(vibe_dir.glob("vibe_strategy_review_*.json"))
    vibe_latest = vibe_files[-1] if vibe_files else None
    scanner_path = jsonl_path("market_scan")
    local_signal_path = jsonl_path("signals")
    local_trade_path = jsonl_path("trades")
    local_score_path = jsonl_path("strategy_scores")
    latest_signal = (saved.get("last_signal") or {}).get("timestamp") or "none"
    latest_trade = ((saved.get("last_result") or {}).get("status")) or "none"
    tournament_status = "ready" if tournament else "not_run"
    tournament_submission = tournament.get("receiver_submission") or {}
    loop_steps = loop.get("steps") or {}
    loop_oanda = loop_steps.get("oanda") or {}
    loop_strategy_search = loop_steps.get("strategy_search") or {}
    loop_tournament = loop_steps.get("tournament") or {}
    selected_candidate = loop.get("selected_candidate") or {}
    rotated_candidate = loop.get("rotated_to_candidate") or {}
    duplicate_blocked_candidates = loop.get("duplicate_blocked_candidates") or []
    skipped_candidates = loop.get("skipped_candidates") or []
    next_candidate_queue = loop.get("next_candidate_queue") or []
    local_paper_fallback_reason = loop.get("local_paper_fallback_reason")
    no_trade_reason = loop.get("no_trade_reason")
    duplicate_summary = ", ".join(f"{row.get('strategy_id')}:{row.get('symbol')}" for row in duplicate_blocked_candidates[:5]) or "none"
    rotated_summary = rotated_candidate.get("strategy_id", "none")
    selected_summary = selected_candidate.get("strategy_id", "none")
    queue_summary = ", ".join(f"{row.get('strategy_id')}:{row.get('symbol')}" for row in next_candidate_queue[:5]) or "none"
    skipped_summary = ", ".join(f"{row.get('strategy_id')}:{row.get('symbol')}" for row in skipped_candidates[:5]) or "none"
    fallback_used = bool(
        (tournament_submission.get("body") or {}).get("fallback_used")
        or (saved.get("last_result") or {}).get("fallback_used")
        or local_paper_fallback_reason
    )
    oanda_trade_placed = bool(
        (tournament_submission.get("body") or {}).get("execution_mode") == "oanda_practice"
        or oanda.get("practice_order_placed")
        or saved.get("last_oanda_practice_order_at")
    )
    scanner_status = "ready" if scanner_path.exists() else "not_run"
    vibe_status = "ready" if vibe_latest else "not_run"
    oanda_status = "OANDA_PRACTICE_READY" if loop_oanda.get("ok") else (oanda.get("status") or "not_checked")
    execution_mode = (saved.get("last_result") or {}).get("execution_mode") or ("oanda_practice" if oanda_status == "OANDA_PRACTICE_READY" else "local_paper")
    strategy_search_status = (
        "online" if loop_strategy_search.get("ok") and not ((loop_strategy_search.get("payload") or {}).get("fallback_used"))
        else "online" if strategy_memory and not strategy_memory.get("fallback_used")
        else "fallback_active" if strategy_memory
        else "not_run"
    )
    promotion_file = ROOT / "logs" / "trading_memory_supabase_promotion_latest.json"
    promotion = {}
    if promotion_file.exists():
        try:
            promotion = json.loads(promotion_file.read_text())
        except Exception:
            promotion = {}
    supabase_logging = "online" if strategy_search_status == "online" else (bridge.get("verified_facts") or {}).get("supabase_logging") or "blocked_local_fallback_active"
    promotion_created = promotion.get("new_candidates_created", 0)
    top_candidate = (loop_tournament.get("payload") or {}).get("top_candidate_for_next_cap_reset") or tournament.get("top_candidate_for_next_cap_reset") or {}
    display_candidate = selected_candidate or rotated_candidate or top_candidate or (tournament.get("top_strategy") or {})
    display_candidate_name = display_candidate.get("strategy_name") or display_candidate.get("strategy_id") or "none"
    display_candidate_quality = display_candidate.get("data_quality") or ((tournament.get("top_strategy") or {}).get("data_quality")) or "unknown"
    display_candidate_source = display_candidate.get("data_source") or ((tournament.get("top_strategy") or {}).get("strategy_source")) or "unknown"
    display_candidate_decision = display_candidate.get("promotion_decision") or ((tournament.get("top_strategy") or {}).get("promotion_decision")) or "unknown"
    display_candidate_trades = display_candidate.get("trades_count")
    if display_candidate_trades is None:
        display_candidate_trades = ((tournament.get("top_strategy") or {}).get("trades_count"))
    cap_remaining = loop_oanda.get("daily_cap_remaining")
    cap_exhausted = cap_remaining == 0 if cap_remaining is not None else True
    discovery_file = ROOT / "logs" / "trading_strategy_discovery_latest.json"
    discovery = {}
    if discovery_file.exists():
        try:
            discovery = json.loads(discovery_file.read_text())
        except Exception:
            discovery = {}
    youtube_research_file = ROOT / "logs" / "youtube_strategy_research_latest.json"
    youtube_research = {}
    if youtube_research_file.exists():
        try:
            youtube_research = json.loads(youtube_research_file.read_text())
        except Exception:
            youtube_research = {}
    watch_file = ROOT / "logs" / "live_watch" / "trading_watch_session_latest.json"
    watch = {}
    if watch_file.exists():
        try:
            watch = json.loads(watch_file.read_text())
        except Exception:
            watch = {}
    safe_loop_file = ROOT / "logs" / "safe_learning_loop_latest.json"
    safe_loop = {}
    if safe_loop_file.exists():
        try:
            safe_loop = json.loads(safe_loop_file.read_text())
        except Exception:
            safe_loop = {}
    learning_memory_file = ROOT / "logs" / "learning_memory_latest.json"
    learning_memory = {}
    if learning_memory_file.exists():
        try:
            learning_memory = json.loads(learning_memory_file.read_text())
        except Exception:
            learning_memory = {}
    replay_path = ROOT / "logs" / "charts" / "trade_replay_latest.html"
    dashboard_path = ROOT / "logs" / "charts" / "trading_dashboard_latest.html"
    report_status = (
        "STRATEGY_PIPELINE_READY_FOR_NEXT_OANDA_CAP_RESET"
        if strategy_search_status == "online" and promotion_created and top_candidate
        else "STRATEGY_PIPELINE_PARTIAL"
    )
    blocker_items = list(safety.get("blockers") or [])
    if not blocker_items:
        if oanda_status != "OANDA_PRACTICE_READY":
            blocker_items.append(str(oanda.get("blocker") or "oanda_not_ready"))
        if strategy_search_status not in {"online", "fallback_active"}:
            blocker_items.append("strategy_search_unavailable")
        if supabase_logging not in {"online", "blocked_local_fallback_active"}:
            blocker_items.append("supabase_logging_unavailable")
    blocker_summary = ", ".join(dict.fromkeys(item for item in blocker_items if item)) or "none"

    next_cap_reset_command = "python3 scripts/run_nexus_demo_trading_loop.py --mode paper"
    safe_loop_summary = safe_loop.get("summary") or {}
    safe_loops = safe_loop.get("loops") or []
    safe_loop_names = ", ".join(loop.get("lane", "unknown") for loop in safe_loops) or "none"
    zero_result_lanes = ", ".join(safe_loop_summary.get("zero_result_lanes") or []) or "none"
    next_safe_commands = ", ".join(
        action.get("next_safe_command", "unknown")
        for action in (safe_loop.get("next_safe_actions") or [])[:4]
    ) or "none"
    learning_records = learning_memory.get("records") or []
    latest_lessons = " | ".join(
        f"{record.get('lane')}: {record.get('lesson_learned')}"
        for record in learning_records[:4]
        if record.get("lesson_learned")
    ) or "none"

    lines = [
        "NEXUS TRADING STATUS",
        "",
        f"Status: {report_status}",
        f"Receiver: {saved.get('stage', 'unknown')}",
        f"Port: {saved.get('signal_port', 5000)}",
        f"Broker mode: {saved.get('broker_type', safety.get('broker_mode', 'unknown'))}",
        f"Oanda practice: {oanda_status}",
        f"Execution mode: {execution_mode}",
        f"Oanda cap exhausted: {'yes' if cap_exhausted else 'no'}",
        f"Live trading: {'DISABLED' if not safety.get('live_trading') and not safety.get('live_execution_enabled') else 'BLOCKED'}",
        f"Paper/demo active: {'yes' if safety.get('safe') else 'no'}",
        f"Last signal: {latest_signal}",
        f"Last paper/demo trade: {latest_trade}",
        f"Oanda practice trade placed: {'yes' if oanda_trade_placed else 'no'}",
        f"Fallback used: {'yes' if fallback_used else 'no'}",
        f"Duplicate blocked in latest loop: {'yes' if duplicate_blocked_candidates else 'no'}",
        f"Duplicate blocked candidates: {duplicate_summary}",
        f"Rotated candidate: {rotated_summary}",
        f"Selected candidate: {selected_summary}",
        f"Local paper fallback reason: {local_paper_fallback_reason or 'none'}",
        f"No-trade reason: {no_trade_reason or 'none'}",
        f"Supabase logging: {supabase_logging}",
        f"Supabase strategy search: {strategy_search_status}",
        f"Local fallback logging: {'active' if local_signal_path.exists() or local_trade_path.exists() or local_score_path.exists() else 'inactive'}",
        f"Market scanner: {scanner_status}",
        f"Tournament: {tournament_status}",
        f"Top strategy: {display_candidate_name}",
        f"Strategy source: {display_candidate_source}",
        f"Data quality: {display_candidate_quality}",
        f"Top strategy trades: {display_candidate_trades if display_candidate_trades is not None else 'unknown'}",
        f"Top strategy decision: {display_candidate_decision}",
        f"Supabase candidates created this run: {promotion.get('new_candidates_created', 'unknown')}",
        f"Supabase candidate duplicates skipped: {promotion.get('duplicates_skipped', 'unknown')}",
        f"Discovery candidates discovered: {discovery.get('candidates_discovered', 'unknown')}",
        f"Discovery candidates testable: {discovery.get('candidates_testable', 'unknown')}",
        f"YouTube strategy videos/transcripts reviewed: {youtube_research.get('documents_reviewed', 'unknown')}",
        f"YouTube strategies extracted: {youtube_research.get('strategies_extracted', 'unknown')}",
        f"YouTube strategies testable: {youtube_research.get('testable_strategies', 'unknown')}",
        f"YouTube strategy seeds found: {youtube_research.get('seeds_found', 'unknown')}",
        f"YouTube Supabase rows written: {'yes' if youtube_research.get('rows_written') else 'no'}",
        f"YouTube ready for tournament: {'yes' if youtube_research.get('handoff', {}).get('tournament_dry_run', {}).get('ok') else 'no'}",
        f"YouTube result meaning: {youtube_research.get('result_interpretation', 'unknown')}",
        f"YouTube next safe action: {youtube_research.get('next_safe_action', 'unknown')}",
        f"Safe loops ran: {safe_loop_names}",
        f"Safe loop zero-result lanes: {zero_result_lanes}",
        f"Safe loop seeds found: {safe_loop_summary.get('seed_total', 'unknown')}",
        f"Safe loop variants created: {safe_loop_summary.get('variants_total', 'unknown')}",
        f"Safe loop tests run: {safe_loop_summary.get('tests_total', 'unknown')}",
        f"Learning lessons: {latest_lessons}",
        f"Next safe commands: {next_safe_commands}",
        "Ray approval required for: live trading, paid APIs, public publishing, email/outreach, production deploys, real-money broker activity",
        f"Top candidate for next cap reset: {top_candidate.get('strategy_name', 'none')}",
        f"Top candidate win rate: {top_candidate.get('win_rate', 'n/a')}",
        f"Top candidate profit factor: {top_candidate.get('profit_factor', 'n/a')}",
        f"Top candidate max drawdown: {top_candidate.get('max_drawdown', 'n/a')}",
        f"Next candidate queue: {queue_summary}",
        f"Skipped candidates: {skipped_summary}",
        f"Live watch session: {watch.get('session_name', 'not_run')}",
        f"Live watch setup detected: {'yes' if watch.get('setup_detected') else 'no'}",
        f"Replay chart: {replay_path if replay_path.exists() else 'not_generated'}",
        f"Trading dashboard: {dashboard_path if dashboard_path.exists() else 'not_generated'}",
        f"Vibe review: {vibe_status}",
        f"Oanda daily cap remaining: {loop_oanda.get('daily_cap_remaining', 'unknown')}",
        f"Blockers: {blocker_summary}",
        f"Next command after cap reset: {next_cap_reset_command}",
        "Safety confirmation: LIVE_TRADING=false · PAPER_ONLY=true · DRY_RUN=true",
        "Recommendation: Keep receiver in paper/demo mode, do not force trades while capped, and use the next-cap-reset command to test the strongest Supabase-native candidate.",
    ]
    report = "\n".join(lines)
    latest_md = ROOT / "logs" / "nexus_trading_telegram_ready_latest.md"
    latest_md.write_text(report + "\n")
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
