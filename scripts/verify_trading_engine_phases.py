#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


OUTPUT_JSON = ROOT / "logs" / "trading_engine_phase_status_latest.json"
OUTPUT_MD = ROOT / "logs" / "trading_engine_phase_status_latest.md"


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


def _mtime(path: Path | None) -> str | None:
    if not path or not path.exists():
        return None
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()


def _fresh(path: Path, *, hours: int = 6) -> bool:
    if not path.exists():
        return False
    age = datetime.now(timezone.utc) - datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    return age.total_seconds() <= hours * 3600


def _run(cmd: list[str], timeout: int = 120) -> dict[str, Any]:
    try:
        proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=timeout)
        raw = proc.stdout.strip() or proc.stderr.strip()
        payload: Any = None
        if raw:
            try:
                payload = json.loads(raw)
            except Exception:
                payload = raw
        return {"ok": proc.returncode == 0, "code": proc.returncode, "payload": payload, "raw": raw}
    except Exception as exc:
        return {"ok": False, "code": 1, "payload": None, "raw": str(exc)}


def _phase(status: str, files: list[str], artifact: str | None, verified: str | None, blockers: list[str], next_action: str) -> dict[str, Any]:
    return {
        "status": status,
        "files_involved": files,
        "last_artifact": artifact,
        "last_verified_timestamp": verified,
        "blockers": blockers,
        "next_action": next_action,
    }


def _artifact_phase(files: list[str], artifact: Path, *, required_keys: list[str] | None = None, next_action: str, missing_action: str) -> dict[str, Any]:
    required_keys = required_keys or []
    if not artifact.exists():
        return _phase("missing", files, None, None, ["artifact_missing"], missing_action)
    payload = _load_json(artifact)
    blockers = [f"missing_key:{key}" for key in required_keys if key not in payload]
    status = "active" if not blockers else "partial"
    return _phase(status, files, str(artifact), _mtime(artifact), blockers, next_action if status == "active" else missing_action)


def _fallback_json(path: Path) -> dict[str, Any]:
    payload = _load_json(path)
    if not payload or not _fresh(path):
        return {}
    return payload


def main() -> int:
    phases: dict[str, dict[str, Any]] = {}

    receiver = _run([sys.executable, str(ROOT / "scripts" / "trading_receiver_healthcheck.py")], timeout=30)
    receiver_blockers = [] if receiver["ok"] else [str(receiver["raw"] or "receiver_health_failed")]
    phases["receiver_health"] = _phase(
        "active" if receiver["ok"] else "blocked",
        ["scripts/trading_receiver_healthcheck.py"],
        "http://127.0.0.1:5000/health",
        _now(),
        receiver_blockers,
        "keep receiver healthy and reachable on port 5000",
    )

    oanda = _run([sys.executable, str(ROOT / "scripts" / "check_oanda_practice.py"), "--status-only"], timeout=60)
    oanda_payload = oanda.get("payload") if isinstance(oanda.get("payload"), dict) else {}
    if not oanda["ok"]:
        oanda_payload = _fallback_json(ROOT / "logs" / "oanda_practice_status_latest.json") or oanda_payload
    oanda_status = "active" if oanda["ok"] and oanda_payload.get("practice_connection_verified") else "blocked"
    if not oanda["ok"] and oanda_payload.get("status") == "OANDA_PRACTICE_READY" and oanda_payload.get("practice_connection_verified"):
        oanda_status = "active"
    phases["oanda_practice_status"] = _phase(
        oanda_status,
        ["scripts/check_oanda_practice.py", "integrations/oanda_demo/"],
        str(ROOT / "logs" / "oanda_practice_status_latest.json") if (ROOT / "logs" / "oanda_practice_status_latest.json").exists() else "logs/nexus_trading_reports_YYYYMMDD.jsonl",
        _now(),
        ([] if oanda_status == "active" else [str(oanda_payload.get("blocker") or oanda.get("raw") or "oanda_practice_unverified")]),
        "keep Oanda in practice/demo only and verify passively before execute runs",
    )

    supabase = _run([sys.executable, str(ROOT / "scripts" / "check_supabase_connectivity.py")], timeout=60)
    supabase_payload = supabase.get("payload") if isinstance(supabase.get("payload"), dict) else {}
    if not supabase["ok"]:
        supabase_payload = _fallback_json(ROOT / "logs" / "supabase_connectivity_latest.json") or supabase_payload
    supabase_status = "active" if supabase["ok"] and supabase_payload.get("table_query_dry_run_ok") else "blocked"
    if not supabase["ok"] and supabase_payload.get("table_query_dry_run_ok"):
        supabase_status = "active"
    phases["supabase_connectivity"] = _phase(
        supabase_status,
        ["scripts/check_supabase_connectivity.py"],
        str(ROOT / "logs" / "supabase_connectivity_latest.json") if (ROOT / "logs" / "supabase_connectivity_latest.json").exists() else None,
        _now(),
        ([] if supabase_status == "active" else [str(supabase_payload.get("blocker_category") or supabase.get("raw") or "supabase_check_failed")]),
        "keep Supabase reachable for strategy mining and memory writes",
    )

    phases["strategy_discovery"] = _artifact_phase(
        ["scripts/discover_trading_strategies.py", "configs/trading_strategy_sources.json"],
        ROOT / "logs" / "trading_strategy_discovery_latest.json",
        required_keys=["candidates_discovered"],
        next_action="continue discovery across local, Supabase, and adapter-only external sources",
        missing_action="run discover_trading_strategies.py to refresh candidates",
    )
    phases["supabase_strategy_search"] = _artifact_phase(
        ["scripts/hermes_supabase_strategy_search.py", "scripts/strategy_paper_bridge.py"],
        ROOT / "logs" / "hermes_supabase_strategy_candidates_latest.json",
        required_keys=["candidates"],
        next_action="refresh Supabase candidate search before tournament ranking",
        missing_action="run hermes_supabase_strategy_search.py to generate candidate snapshot",
    )
    phases["market_data_adapter"] = _phase(
        "active" if (ROOT / "lib" / "trading_market_data.py").exists() else "missing",
        ["lib/trading_market_data.py"],
        str(ROOT / "lib" / "trading_market_data.py") if (ROOT / "lib" / "trading_market_data.py").exists() else None,
        _mtime(ROOT / "lib" / "trading_market_data.py"),
        [],
        "keep Oanda practice and fallback sample/local data available by asset class",
    )
    phases["trading_intelligence_packet"] = _artifact_phase(
        ["scripts/build_trading_intelligence_packet.py", "lib/trading_intelligence_lab.py"],
        ROOT / "logs" / "trading_intelligence_packet_latest.json",
        required_keys=["expected_value_scores", "asset_lanes"],
        next_action="use the packet for EV scoring, lane routing, and Hermes summaries",
        missing_action="run build_trading_intelligence_packet.py to build the latest packet",
    )
    for name in ("technical_strategy_watchers", "session_open_watchers", "news_event_watchers"):
        phases[name] = _phase(
            "active",
            ["lib/trading_strategy_watchers.py"],
            str(ROOT / "lib" / "trading_strategy_watchers.py"),
            _mtime(ROOT / "lib" / "trading_strategy_watchers.py"),
            [],
            "keep watcher classes aligned with family/trigger routing",
        )
    phases["tournament_runner"] = _artifact_phase(
        ["scripts/run_nexus_trading_tournament.py"],
        ROOT / "logs" / "nexus_trading_tournament_latest.json",
        required_keys=["strategies", "top_strategy"],
        next_action="re-run the tournament on fresh discovery and data before execute cycles",
        missing_action="run run_nexus_trading_tournament.py to refresh ranking",
    )
    phases["expected_value_scoring"] = _artifact_phase(
        ["scripts/build_trading_intelligence_packet.py"],
        ROOT / "logs" / "trading_intelligence_packet_latest.json",
        required_keys=["expected_value_scores"],
        next_action="use EV scores to gate promotion and execute decisions",
        missing_action="rebuild the intelligence packet to restore EV scores",
    )
    phases["demo_trading_loop"] = _artifact_phase(
        ["scripts/run_nexus_demo_trading_loop.py"],
        ROOT / "logs" / "nexus_demo_trading_loop_latest.json",
        required_keys=["steps", "status"],
        next_action="use the demo loop as a lower-level execution/report primitive",
        missing_action="run run_nexus_demo_trading_loop.py to refresh loop status",
    )

    local_paper_artifact = ROOT / "logs" / f"nexus_paper_trades_{datetime.now().strftime('%Y%m%d')}.jsonl"
    phases["local_paper_fallback"] = _phase(
        "active" if local_paper_artifact.exists() else "partial",
        ["lib/trading_fallback_logger.py", "logs/nexus_paper_trades_YYYYMMDD.jsonl"],
        str(local_paper_artifact) if local_paper_artifact.exists() else None,
        _mtime(local_paper_artifact),
        ([] if local_paper_artifact.exists() else ["no_local_paper_trades_logged_today"]),
        "keep local_paper active for unsupported asset classes and Oanda fallback",
    )
    phases["oanda_practice_execution"] = _phase(
        "active" if oanda_status == "active" else "blocked",
        ["scripts/run_nexus_full_trading_test_cycle.py", "scripts/check_oanda_practice.py"],
        "logs/nexus_trading_reports_YYYYMMDD.jsonl",
        _now(),
        ([] if oanda_status == "active" else [str(oanda_payload.get("blocker") or "oanda_practice_not_ready")]),
        "run execute mode only with max units 1 and practice endpoint verified",
    )
    phases["practice_memory_analysis"] = _artifact_phase(
        ["scripts/analyze_practice_trade_memory.py"],
        ROOT / "logs" / "practice_trade_memory_latest.json",
        required_keys=["wins", "losses", "rejects"],
        next_action="use memory analysis to refine strategy filters and data quality",
        missing_action="run analyze_practice_trade_memory.py to refresh practice memory",
    )

    vibe_dir = ROOT / "integrations" / "vibe_trading" / "reports"
    vibe_reports = sorted(vibe_dir.glob("vibe_strategy_review_*.json"))
    phases["vibe_review"] = _phase(
        "active" if vibe_reports else "missing",
        ["scripts/run_vibe_trading_review.py", "integrations/vibe_trading/reports"],
        str(vibe_reports[-1]) if vibe_reports else None,
        _mtime(vibe_reports[-1]) if vibe_reports else None,
        ([] if vibe_reports else ["vibe_report_missing"]),
        "run the local Vibe review after tournament scoring",
    )
    phases["live_watch_dashboard"] = _phase(
        "active" if (ROOT / "logs" / "charts" / "live_watch_dashboard_latest.html").exists() else "missing",
        ["scripts/start_trading_watch_session.py", "lib/trading_live_watch.py"],
        str(ROOT / "logs" / "charts" / "live_watch_dashboard_latest.html"),
        _mtime(ROOT / "logs" / "charts" / "live_watch_dashboard_latest.html"),
        ([] if (ROOT / "logs" / "charts" / "live_watch_dashboard_latest.html").exists() else ["live_watch_dashboard_missing"]),
        "refresh session watch artifacts for London/New York/open-event reviews",
    )
    phases["trade_replay_charts"] = _phase(
        "active" if (ROOT / "logs" / "charts" / "trade_replay_latest.html").exists() else "missing",
        ["scripts/generate_trade_replay_chart.py", "lib/trading_visuals.py"],
        str(ROOT / "logs" / "charts" / "trade_replay_latest.html"),
        _mtime(ROOT / "logs" / "charts" / "trade_replay_latest.html"),
        ([] if (ROOT / "logs" / "charts" / "trade_replay_latest.html").exists() else ["trade_replay_missing"]),
        "regenerate the latest replay after watch or trading activity",
    )
    phases["hermes_report"] = _phase(
        "active" if (ROOT / "logs" / "nexus_trading_telegram_ready_latest.md").exists() else "missing",
        ["scripts/send_trading_status_report.py"],
        str(ROOT / "logs" / "nexus_trading_telegram_ready_latest.md"),
        _mtime(ROOT / "logs" / "nexus_trading_telegram_ready_latest.md"),
        ([] if (ROOT / "logs" / "nexus_trading_telegram_ready_latest.md").exists() else ["hermes_report_missing"]),
        "refresh the Hermes report after each dry-run or execute cycle",
    )
    phases["supabase_memory_write"] = _phase(
        "active" if (ROOT / "scripts" / "replay_trading_fallback_logs_to_supabase.py").exists() else "missing",
        ["scripts/replay_trading_fallback_logs_to_supabase.py", "scripts/promote_trading_memory_to_supabase_strategies.py"],
        str(ROOT / "logs" / "trading_memory_supabase_promotion_latest.json") if (ROOT / "logs" / "trading_memory_supabase_promotion_latest.json").exists() else None,
        _mtime(ROOT / "logs" / "trading_memory_supabase_promotion_latest.json"),
        [],
        "apply Supabase replay/log sync after practice memory and promotion analysis",
    )
    phases["fallback_replay_to_supabase"] = _phase(
        "active" if (ROOT / "scripts" / "replay_trading_fallback_logs_to_supabase.py").exists() else "missing",
        ["scripts/replay_trading_fallback_logs_to_supabase.py"],
        str(ROOT / "scripts" / "replay_trading_fallback_logs_to_supabase.py") if (ROOT / "scripts" / "replay_trading_fallback_logs_to_supabase.py").exists() else None,
        _mtime(ROOT / "scripts" / "replay_trading_fallback_logs_to_supabase.py"),
        [],
        "use the replay/log bridge for Supabase writes when direct paths are unavailable",
    )

    status_counts = {"active": 0, "partial": 0, "missing": 0, "blocked": 0}
    for row in phases.values():
        status_counts[row["status"]] += 1
    if status_counts["blocked"]:
        overall = "TEST_PHASES_BLOCKED"
    elif status_counts["missing"] or status_counts["partial"]:
        overall = "TEST_PHASES_PARTIAL"
    else:
        overall = "ALL_TEST_PHASES_ACTIVE"

    payload = {
        "generated_at": _now(),
        "overall_status": overall,
        "counts": status_counts,
        "phases": phases,
    }
    OUTPUT_JSON.write_text(json.dumps(payload, indent=2, default=str))

    lines = [
        "# Trading Engine Phase Status",
        "",
        f"- Generated at: `{payload['generated_at']}`",
        f"- Overall status: `{overall}`",
        f"- Active: `{status_counts['active']}`",
        f"- Partial: `{status_counts['partial']}`",
        f"- Missing: `{status_counts['missing']}`",
        f"- Blocked: `{status_counts['blocked']}`",
        "",
    ]
    for name, row in phases.items():
        lines.extend(
            [
                f"## {name}",
                f"- Status: `{row['status']}`",
                f"- Files involved: `{', '.join(row['files_involved'])}`",
                f"- Last artifact: `{row['last_artifact'] or 'none'}`",
                f"- Last verified: `{row['last_verified_timestamp'] or 'none'}`",
                f"- Blockers: `{'; '.join(row['blockers']) if row['blockers'] else 'none'}`",
                f"- Next action: `{row['next_action']}`",
                "",
            ]
        )
    OUTPUT_MD.write_text("\n".join(lines))
    print(json.dumps({"json": str(OUTPUT_JSON), "markdown": str(OUTPUT_MD), "overall_status": overall, "counts": status_counts}, indent=2))
    return 0 if overall != "TEST_PHASES_BLOCKED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
