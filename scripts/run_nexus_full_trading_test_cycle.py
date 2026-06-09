#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


OUTPUT_JSON = ROOT / "logs" / "full_trading_test_cycle_latest.json"
OUTPUT_MD = ROOT / "logs" / "full_trading_test_cycle_latest.md"
DEFAULT_MAX_OANDA_TRADES = 5
DEFAULT_MAX_UNITS = 1
DEFAULT_LOCAL_PAPER_REPS = 50


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


def _read_file(path: Path) -> str:
    try:
        return path.read_text()
    except Exception:
        return ""


def _run_step(name: str, cmd: list[str], *, timeout: int = 300) -> dict[str, Any]:
    started = _now()
    try:
        proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=timeout)
        raw = proc.stdout.strip() or proc.stderr.strip()
        payload: Any = None
        if raw:
            try:
                payload = json.loads(raw)
            except Exception:
                payload = raw
        return {
            "step": name,
            "started_at": started,
            "completed_at": _now(),
            "ok": proc.returncode == 0,
            "returncode": proc.returncode,
            "command": " ".join(cmd),
            "payload": payload,
            "raw": raw,
        }
    except Exception as exc:
        return {
            "step": name,
            "started_at": started,
            "completed_at": _now(),
            "ok": False,
            "returncode": 1,
            "command": " ".join(cmd),
            "payload": None,
            "raw": str(exc),
        }


def _mode_from_args(args: argparse.Namespace) -> str:
    if args.execute:
        return "execute"
    if args.dry_run:
        return "dry-run"
    return "check-only"


def _warning_text() -> str:
    return "\n".join(
        [
            "WARNING: EXECUTE MODE CAN PLACE CAPPED OANDA PRACTICE ORDERS.",
            "LIVE_TRADING remains false.",
            "OANDA practice/demo only.",
            "Max units: 1.",
            "local_paper fallback active.",
            "No live-money trading allowed.",
        ]
    )


def _asset_lane_summary() -> list[dict[str, Any]]:
    memory = _load_json(ROOT / "logs" / "practice_trade_memory_latest.json")
    lanes = memory.get("asset_lanes")
    if isinstance(lanes, list) and lanes:
        return lanes
    return [
        {
            "asset_class": "forex",
            "symbols": ["EURUSD", "USDJPY", "GBPUSD"],
            "execution_mode": "oanda_practice_or_local_paper",
            "trades_reps": 0,
            "rejects": 0,
            "next_improvement": "collect fresh practice reps",
        },
        {
            "asset_class": "crypto",
            "symbols": ["BTC", "ETH"],
            "execution_mode": "local_paper_only",
            "trades_reps": 0,
            "rejects": 0,
            "next_improvement": "collect local_paper reps",
        },
        {
            "asset_class": "stocks",
            "symbols": ["SPY", "QQQ"],
            "execution_mode": "local_paper_only",
            "trades_reps": 0,
            "rejects": 0,
            "next_improvement": "collect local_paper reps",
        },
        {
            "asset_class": "options",
            "symbols": ["SPY", "QQQ"],
            "execution_mode": "local_paper_theoretical",
            "trades_reps": 0,
            "rejects": 0,
            "next_improvement": "keep theoretical until a paper adapter exists",
        },
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--max-oanda-trades", type=int, default=DEFAULT_MAX_OANDA_TRADES)
    parser.add_argument("--max-units", type=int, default=DEFAULT_MAX_UNITS)
    parser.add_argument("--local-paper-max-reps", type=int, default=DEFAULT_LOCAL_PAPER_REPS)
    parser.add_argument("--stage", default="practice_learning")
    args = parser.parse_args()

    mode = _mode_from_args(args)
    if sum(bool(v) for v in (args.check_only, args.dry_run, args.execute)) > 1:
        parser.error("choose only one mode")

    result: dict[str, Any] = {
        "generated_at": _now(),
        "mode": mode,
        "stage": args.stage,
        "warning": _warning_text() if mode == "execute" else None,
        "caps": {
            "oanda_practice_max_units": min(args.max_units, 1),
            "oanda_practice_max_trades_per_run": args.max_oanda_trades,
            "oanda_practice_max_trades_per_day": 50,
            "local_paper_max_reps_per_run": args.local_paper_max_reps,
        },
        "steps": [],
        "artifacts": {},
        "status": "TEST_CYCLE_BLOCKED",
        "execute_trade_attempted": False,
    }

    if mode == "execute":
        print(_warning_text())

    steps: list[dict[str, Any]] = []
    def add(name: str, cmd: list[str], *, timeout: int = 300, required: bool = True) -> dict[str, Any]:
        step = _run_step(name, cmd, timeout=timeout)
        step["required"] = required
        steps.append(step)
        return step

    safety = add("safety_gate", [sys.executable, str(ROOT / "scripts" / "check_trading_safety.py")], timeout=60)
    receiver = add("receiver_health", [sys.executable, str(ROOT / "scripts" / "trading_receiver_healthcheck.py")], timeout=60)
    oanda = add("oanda_practice_status", [sys.executable, str(ROOT / "scripts" / "check_oanda_practice.py"), "--status-only"], timeout=120)
    supabase = add("supabase_connectivity", [sys.executable, str(ROOT / "scripts" / "check_supabase_connectivity.py")], timeout=120)
    phases = add("verify_trading_phases", [sys.executable, str(ROOT / "scripts" / "verify_trading_engine_phases.py")], timeout=180)

    if mode in {"dry-run", "execute"}:
        add("strategy_discovery", [sys.executable, str(ROOT / "scripts" / "discover_trading_strategies.py"), "--asset-class", "forex", "--source", "all", "--dry-run"], timeout=300)
        add("supabase_strategy_search", [sys.executable, str(ROOT / "scripts" / "hermes_supabase_strategy_search.py"), "--asset-class", "all", "--limit", "20"], timeout=300)
        add("build_trading_intelligence_packet", [sys.executable, str(ROOT / "scripts" / "build_trading_intelligence_packet.py"), "--dry-run"], timeout=180)
        add("market_data_pull_forex", [sys.executable, str(ROOT / "scripts" / "run_nexus_trading_tournament.py"), "--mode", "paper", "--source", "supabase_first", "--data-source", "oanda_practice", "--symbols", "EURUSD,USDJPY,GBPUSD", "--dry-run"], timeout=300)
        add("technical_session_watch_london", [sys.executable, str(ROOT / "scripts" / "start_trading_watch_session.py"), "--session", "london_open", "--symbols", "EURUSD,USDJPY,GBPUSD", "--mode", "paper", "--dry-run", "--data-source", "oanda_practice"], timeout=300)
        add("technical_session_watch_new_york_refresh", [sys.executable, str(ROOT / "scripts" / "start_trading_watch_session.py"), "--session", "new_york_open", "--symbols", "EURUSD,USDJPY,GBPUSD", "--mode", "paper", "--dry-run", "--data-source", "oanda_practice", "--refresh-seconds", "10", "--duration-minutes", "5"], timeout=420)
        add("generate_trade_replay", [sys.executable, str(ROOT / "scripts" / "generate_trade_replay_chart.py"), "--latest", "--data-source", "oanda_practice"], timeout=180)
        add("demo_trading_loop", [sys.executable, str(ROOT / "scripts" / "run_nexus_demo_trading_loop.py"), "--mode", "paper", "--stage", args.stage, "--dry-run", "--max-oanda-trades", str(args.max_oanda_trades)], timeout=300)
        add("vibe_review", [sys.executable, str(ROOT / "scripts" / "run_vibe_trading_review.py"), "--latest-tournament"], timeout=180)
        add("practice_memory_analysis", [sys.executable, str(ROOT / "scripts" / "analyze_practice_trade_memory.py")], timeout=300)
        add("hermes_report", [sys.executable, str(ROOT / "scripts" / "send_trading_status_report.py"), "--dry-run"], timeout=180)

    execute_ready = all(step["ok"] for step in steps if step.get("required", True))
    if mode == "execute":
        result["execute_trade_attempted"] = True
        if execute_ready:
            add("execute_cycle", [sys.executable, str(ROOT / "scripts" / "run_nexus_demo_trading_loop.py"), "--mode", "paper", "--stage", args.stage, "--max-oanda-trades", str(args.max_oanda_trades)], timeout=300)
            add("post_execute_replay", [sys.executable, str(ROOT / "scripts" / "generate_trade_replay_chart.py"), "--latest", "--data-source", "oanda_practice"], timeout=180, required=False)
            add("post_execute_memory", [sys.executable, str(ROOT / "scripts" / "analyze_practice_trade_memory.py")], timeout=300, required=False)
            add("post_execute_report", [sys.executable, str(ROOT / "scripts" / "send_trading_status_report.py"), "--dry-run"], timeout=180, required=False)
        else:
            steps.append(
                {
                    "step": "execute_cycle",
                    "started_at": _now(),
                    "completed_at": _now(),
                    "ok": False,
                    "returncode": 1,
                    "command": "skipped",
                    "payload": None,
                    "raw": "execute skipped because required dry-run safety/health steps failed",
                    "required": True,
                }
            )

    result["steps"] = steps
    phase_payload = _load_json(ROOT / "logs" / "trading_engine_phase_status_latest.json")
    memory_payload = _load_json(ROOT / "logs" / "practice_trade_memory_latest.json")
    packet_payload = _load_json(ROOT / "logs" / "trading_intelligence_packet_latest.json")
    loop_payload = _load_json(ROOT / "logs" / "nexus_demo_trading_loop_latest.json")
    report_path = ROOT / "logs" / "nexus_trading_telegram_ready_latest.md"
    result["artifacts"] = {
        "phase_status_json": str(ROOT / "logs" / "trading_engine_phase_status_latest.json"),
        "phase_status_md": str(ROOT / "logs" / "trading_engine_phase_status_latest.md"),
        "intelligence_packet_json": str(ROOT / "logs" / "trading_intelligence_packet_latest.json"),
        "practice_memory_json": str(ROOT / "logs" / "practice_trade_memory_latest.json"),
        "live_watch_dashboard": str(ROOT / "logs" / "charts" / "live_watch_dashboard_latest.html"),
        "trade_replay": str(ROOT / "logs" / "charts" / "trade_replay_latest.html"),
        "trading_dashboard": str(ROOT / "logs" / "charts" / "trading_dashboard_latest.html"),
        "hermes_report_md": str(report_path),
    }
    result["asset_lanes"] = _asset_lane_summary()
    result["phase_counts"] = phase_payload.get("counts")
    result["phase_overall_status"] = phase_payload.get("overall_status")
    result["practice_memory_summary"] = {
        "wins": memory_payload.get("wins"),
        "losses": memory_payload.get("losses"),
        "rejects": memory_payload.get("rejects"),
        "fallback_to_local_paper": memory_payload.get("fallback_to_local_paper"),
        "duplicate_blocked": memory_payload.get("duplicate_blocked"),
    }
    result["practice_rotation_summary"] = {
        "selected_candidate": loop_payload.get("selected_candidate"),
        "skipped_candidates": loop_payload.get("skipped_candidates"),
        "duplicate_blocked_candidates": loop_payload.get("duplicate_blocked_candidates"),
        "rotated_to_candidate": loop_payload.get("rotated_to_candidate"),
        "local_paper_fallback_reason": loop_payload.get("local_paper_fallback_reason"),
        "no_trade_reason": loop_payload.get("no_trade_reason"),
        "next_candidate_queue": loop_payload.get("next_candidate_queue"),
    }
    result["top_expected_value"] = (packet_payload.get("expected_value_scores") or [None])[0]
    result["hermes_report_preview"] = _read_file(report_path).splitlines()[:12] if report_path.exists() else []

    blocked = [step for step in steps if step.get("required", True) and not step["ok"]]
    if blocked:
        result["status"] = "TEST_CYCLE_BLOCKED"
    elif mode == "check-only":
        result["status"] = "TEST_CYCLE_CHECKS_OK"
    elif mode == "dry-run":
        result["status"] = "TEST_CYCLE_DRY_RUN_OK"
    else:
        result["status"] = "TEST_CYCLE_EXECUTE_OK"

    OUTPUT_JSON.write_text(json.dumps(result, indent=2, default=str))
    lines = [
        "# Full Trading Test Cycle",
        "",
        f"- Generated at: `{result.get('generated_at')}`",
        f"- Mode: `{mode}`",
        f"- Stage: `{args.stage}`",
        f"- Status: `{result.get('status')}`",
        f"- Phase overall status: `{result.get('phase_overall_status')}`",
        f"- Top expected value candidate: `{((result.get('top_expected_value') or {}).get('strategy_id')) or 'none'}`",
        "",
        "## Steps",
    ]
    for step in steps:
        lines.append(
            f"- `{step.get('step')}` ok=`{'yes' if step.get('ok') else 'no'}` rc=`{step.get('returncode')}` "
            f"cmd=`{step.get('command')}`"
        )
    lines.append("")
    lines.append("## Asset Lanes")
    for lane in result.get("asset_lanes") or []:
        lines.append(
            f"- `{lane.get('asset_class')}` symbols=`{', '.join(lane.get('symbols') or [])}` "
            f"execution=`{lane.get('execution_mode')}` reps=`{lane.get('trades_reps', 'unknown')}` rejects=`{lane.get('rejects', 'unknown')}`"
        )
    OUTPUT_MD.write_text("\n".join(lines) + "\n")
    print(json.dumps({"json": str(OUTPUT_JSON), "markdown": str(OUTPUT_MD), "status": result["status"]}, indent=2))
    return 0 if not blocked else 1


if __name__ == "__main__":
    raise SystemExit(main())
