#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from integrations.oanda_demo import OandaDemoAdapter
from integrations.oanda_demo.oanda_demo_adapter import OandaSafetyError
from lib.trading_fallback_logger import append_jsonl, latest_jsonl
from lib.trading_market_data import resolve_market_data_bundle
from lib.trading_safety_gate import evaluate_trading_safety, seed_safe_trading_env_from_launch_agent


REPORT_FILE = ROOT / "logs" / "nexus_demo_trading_loop_latest.json"
RECEIVER_SIGNAL_URL = "http://127.0.0.1:5000/signal"
DEFAULT_LOCAL_PAPER_REPS = 50
DEFAULT_MAX_OANDA_TRADES_PER_DAY = 50


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _run(cmd: list[str]) -> tuple[int, str]:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return proc.returncode, proc.stdout or proc.stderr


def _run_json(cmd: list[str]) -> tuple[int, Any, str]:
    code, raw = _run(cmd)
    payload: Any = None
    text = raw.strip()
    if text:
        try:
            payload = json.loads(text)
        except Exception:
            payload = None
    return code, payload, raw


def _fetch(url: str) -> dict[str, Any]:
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            return json.loads(resp.read())
    except Exception as exc:
        code, out = _run(["curl", "-sS", url])
        if code == 0 and out.strip():
            return json.loads(out)
        raise RuntimeError(f"receiver_fetch_failed: {exc}") from exc


def _post_signal(payload: dict[str, Any]) -> dict[str, Any]:
    req = urllib.request.Request(
        RECEIVER_SIGNAL_URL,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        body = json.loads(resp.read())
    return {"status_code": resp.status, "accepted": resp.status < 300, "body": body}


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


def _normalize_symbol(value: Any) -> str:
    return str(value or "").upper().replace("_", "")


def _parse_time(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except Exception:
        return None


def _cooldown_seconds() -> int:
    try:
        return int(os.getenv("NEXUS_SIGNAL_COOLDOWN_SECONDS", "300"))
    except Exception:
        return 300


def _candidate_key(candidate: dict[str, Any]) -> str:
    signal = candidate.get("signal_payload") or {}
    base = {
        "strategy_id": candidate.get("strategy_id"),
        "symbol": candidate.get("symbol"),
        "direction": candidate.get("direction"),
        "timeframe": candidate.get("timeframe"),
        "entry_price": signal.get("entry_price"),
        "stop_loss": signal.get("stop_loss"),
        "take_profit": signal.get("take_profit"),
    }
    return json.dumps(base, sort_keys=True, default=str)


def _strategy_symbol_key(candidate: dict[str, Any]) -> str:
    return f"{candidate.get('strategy_id')}::{candidate.get('symbol')}"


def _submission_result(submission: dict[str, Any] | None) -> tuple[str, str | None]:
    if not submission:
        return "missing_submission", "missing_submission"
    body = submission.get("body") or {}
    engine_result = body.get("engine_result") or {}
    status = str(engine_result.get("status") or "").lower()
    rejection = str(engine_result.get("rejection_reason") or "")
    if rejection:
        return status or "rejected", rejection
    return status or "unknown", None


def _build_recent_activity(receiver_status: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for trade in latest_jsonl("trades", limit=200):
        rows.append(
            {
                "strategy_id": trade.get("strategy_id"),
                "symbol": _normalize_symbol(trade.get("symbol")),
                "direction": trade.get("direction"),
                "entry_price": trade.get("entry_price"),
                "stop_loss": trade.get("stop_loss"),
                "take_profit": trade.get("take_profit"),
                "timestamp": trade.get("created_at"),
                "source": "trade_log",
                "status": trade.get("status"),
                "failure_reason": trade.get("failure_reason"),
            }
        )
    for row in latest_jsonl("signals", limit=200):
        payload = row.get("signal_payload") or {}
        rows.append(
            {
                "strategy_id": row.get("strategy_id"),
                "symbol": _normalize_symbol(row.get("symbol")),
                "direction": row.get("direction"),
                "entry_price": payload.get("entry_price"),
                "stop_loss": payload.get("stop_loss"),
                "take_profit": payload.get("take_profit"),
                "timestamp": row.get("created_at"),
                "source": "signal_log",
                "status": row.get("status"),
                "failure_reason": row.get("rejection_reason"),
            }
        )
    last_signal = (receiver_status.get("status") or {}).get("last_signal") or {}
    if last_signal:
        rows.append(
            {
                "strategy_id": last_signal.get("strategy_id") or last_signal.get("strategy"),
                "symbol": _normalize_symbol(last_signal.get("symbol")),
                "direction": last_signal.get("action"),
                "entry_price": last_signal.get("entry_price"),
                "stop_loss": last_signal.get("stop_loss"),
                "take_profit": last_signal.get("take_profit"),
                "timestamp": last_signal.get("timestamp"),
                "source": "receiver_last_signal",
                "status": ((last_signal.get("engine_result") or {}).get("status") or "").lower(),
                "failure_reason": (last_signal.get("engine_result") or {}).get("rejection_reason"),
            }
        )
    return rows


def _duplicate_reason(candidate: dict[str, Any], recent_activity: list[dict[str, Any]], cooldown_seconds: int) -> str | None:
    signal = candidate.get("signal_payload") or {}
    now_ts = _parse_time(_now()) or datetime.now(timezone.utc)
    for row in recent_activity:
        if _normalize_symbol(row.get("symbol")) != _normalize_symbol(candidate.get("symbol")):
            continue
        if str(row.get("strategy_id") or "") != str(candidate.get("strategy_id") or ""):
            continue
        row_ts = _parse_time(row.get("timestamp"))
        exact = (
            str(row.get("direction") or "").upper() == str(candidate.get("direction") or "").upper()
            and _safe_float(row.get("entry_price")) == _safe_float(signal.get("entry_price"))
            and _safe_float(row.get("stop_loss")) == _safe_float(signal.get("stop_loss"))
            and _safe_float(row.get("take_profit")) == _safe_float(signal.get("take_profit"))
        )
        if exact:
            return "duplicate_signal"
        if row_ts and (now_ts - row_ts) < timedelta(seconds=cooldown_seconds):
            return f"cooldown_active_{int(cooldown_seconds - (now_ts - row_ts).total_seconds())}s"
    return None


def _ev_map(packet: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    out: dict[tuple[str, str], dict[str, Any]] = {}
    for row in packet.get("expected_value_scores") or []:
        key = (str(row.get("strategy_id") or ""), _normalize_symbol(row.get("symbol")))
        current = out.get(key)
        if current is None or _safe_float(row.get("expected_value_score")) > _safe_float(current.get("expected_value_score")):
            out[key] = row
    return out


def _tournament_candidates(tournament: dict[str, Any], packet: dict[str, Any]) -> list[dict[str, Any]]:
    ev_lookup = _ev_map(packet)
    rows = sorted(tournament.get("strategies") or [], key=lambda row: int(row.get("rank") or 9999))
    queue: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        signal = dict(row.get("recommended_signal") or {})
        if not signal:
            continue
        symbol = _normalize_symbol(row.get("symbol") or signal.get("symbol"))
        key = (str(row.get("strategy_id") or ""), symbol)
        ev = ev_lookup.get(key, {})
        promotion_decision = str(row.get("promotion_decision") or "")
        execution_eligibility = "not_eligible"
        if str(row.get("asset_class")).lower() == "forex" and promotion_decision in {"paper_candidate", "promoted_for_next_cap_reset"}:
            execution_eligibility = "oanda_practice"
        candidate = {
            "strategy_id": row.get("strategy_id"),
            "strategy_name": row.get("strategy_name"),
            "symbol": symbol,
            "asset_class": row.get("asset_class", "forex"),
            "direction": str(signal.get("action") or "BUY").upper(),
            "timeframe": row.get("timeframe") or signal.get("timeframe") or "H1",
            "rank": int(row.get("rank") or 9999),
            "data_quality": row.get("data_quality"),
            "data_source": row.get("data_source"),
            "promotion_decision": promotion_decision,
            "tournament_rank": int(row.get("rank") or 9999),
            "ev_score": _safe_float(ev.get("expected_value_score"), -999.0),
            "last_setup_timestamp": ((row.get("date_range") or {}).get("end") or row.get("created_at")),
            "execution_eligibility": execution_eligibility,
            "source_artifact": "logs/nexus_trading_tournament_latest.json",
            "signal_payload": signal,
        }
        sig_key = _candidate_key(candidate)
        if sig_key in seen:
            continue
        seen.add(sig_key)
        queue.append(candidate)
    queue.sort(key=lambda row: (row["tournament_rank"], -row["ev_score"]))
    return queue


def _infer_direction_from_template(template: dict[str, Any]) -> str:
    name = str(template.get("strategy_name") or "").lower()
    if "reversal" in name or "condor" in name:
        return "SELL"
    return "BUY"


def _price_candidate(template: dict[str, Any]) -> dict[str, Any]:
    symbol = str(template.get("symbol_or_pair") or "SPY").upper().replace("_", "")
    market = resolve_market_data_bundle(
        symbol,
        timeframe=str(template.get("timeframe") or "H1"),
        lookback=24,
        preferred_source="fallback_sample",
        allow_fallback=True,
    )
    candles = market.get("candles") or []
    last = candles[-1] if candles else {}
    entry = _safe_float(last.get("close"), 100.0 if symbol in {"SPY", "QQQ"} else 50000.0 if "BTC" in symbol else 2000.0 if "ETH" in symbol else 1.25)
    direction = _infer_direction_from_template(template)
    stop = round(entry * (0.99 if direction == "BUY" else 1.01), 6)
    target = round(entry * (1.02 if direction == "BUY" else 0.98), 6)
    asset_class = str(template.get("market_type") or "crypto").lower()
    if asset_class == "options":
        asset_class = "options"
    elif asset_class in {"stock", "equity"}:
        asset_class = "stocks"
    signal = {
        "symbol": symbol,
        "action": direction,
        "entry_price": entry,
        "stop_loss": stop,
        "take_profit": target,
        "timeframe": str(template.get("timeframe") or "H1"),
        "strategy": str(template.get("strategy_name") or "local_paper_template").lower().replace(" ", "_"),
        "strategy_id": str(template.get("strategy_name") or "local_paper_template").lower().replace(" ", "_"),
        "confidence": int(_safe_float(template.get("confidence_score"), 0.55) * 100),
        "entry_reason": "local_paper_practice_rotation",
        "asset_class": asset_class,
        "position_size": 0.01,
        "units": 1,
    }
    return {
        "strategy_id": signal["strategy_id"],
        "strategy_name": template.get("strategy_name"),
        "symbol": symbol,
        "asset_class": asset_class,
        "direction": direction,
        "timeframe": signal["timeframe"],
        "rank": 1000,
        "data_quality": market.get("data_quality") or "fallback_sample",
        "data_source": market.get("source") or "fallback_sample",
        "promotion_decision": "local_paper_only",
        "tournament_rank": 1000,
        "ev_score": 0.0,
        "last_setup_timestamp": (candles[-1].get("time") if candles else _now()),
        "execution_eligibility": "local_paper",
        "source_artifact": "logs/trading_intelligence_packet_latest.json",
        "signal_payload": signal,
    }


def _local_paper_candidates(packet: dict[str, Any]) -> list[dict[str, Any]]:
    templates = ((packet.get("lab_report") or {}).get("strategy_templates") or [])
    queue: list[dict[str, Any]] = []
    seen: set[str] = set()
    for template in templates:
        candidate = _price_candidate(template)
        key = _candidate_key(candidate)
        if key in seen:
            continue
        seen.add(key)
        queue.append(candidate)
    return queue


def _json_candidate(candidate: dict[str, Any] | None) -> dict[str, Any] | None:
    if not candidate:
        return None
    return {
        "strategy_id": candidate.get("strategy_id"),
        "strategy_name": candidate.get("strategy_name"),
        "symbol": candidate.get("symbol"),
        "asset_class": candidate.get("asset_class"),
        "direction": candidate.get("direction"),
        "timeframe": candidate.get("timeframe"),
        "data_quality": candidate.get("data_quality"),
        "data_source": candidate.get("data_source"),
        "promotion_decision": candidate.get("promotion_decision"),
        "tournament_rank": candidate.get("tournament_rank"),
        "ev_score": candidate.get("ev_score"),
        "execution_eligibility": candidate.get("execution_eligibility"),
        "last_setup_timestamp": candidate.get("last_setup_timestamp"),
        "signal_payload": candidate.get("signal_payload"),
    }


def _queue_preview(queue: list[dict[str, Any]], limit: int = 8) -> list[dict[str, Any]]:
    return [_json_candidate(row) for row in queue[:limit]]


def _research_tasks(skipped: list[dict[str, Any]]) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in skipped[:5]:
        strategy_id = str(row.get("strategy_id") or "unknown")
        if strategy_id in seen:
            continue
        seen.add(strategy_id)
        tasks.append(
            {
                "task_type": "strategy_variant_research",
                "strategy_id": strategy_id,
                "symbol": row.get("symbol"),
                "reason": row.get("skip_reason") or row.get("duplicate_reason") or "no_safe_candidate",
            }
        )
    return tasks


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("paper",), default="paper")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--max-oanda-trades", type=int, default=1)
    parser.add_argument(
        "--max-oanda-trades-per-day",
        type=int,
        default=int(os.getenv("NEXUS_OANDA_MAX_TRADES_PER_DAY", str(DEFAULT_MAX_OANDA_TRADES_PER_DAY))),
    )
    parser.add_argument("--local-paper-max-reps", type=int, default=DEFAULT_LOCAL_PAPER_REPS)
    parser.add_argument("--stage", default="standard")
    args = parser.parse_args()

    seed_safe_trading_env_from_launch_agent()
    safety = evaluate_trading_safety(broker_mode="oanda_practice", api_url="")
    result: dict[str, Any] = {
        "ran_at": _now(),
        "mode": args.mode,
        "dry_run": args.dry_run,
        "max_oanda_trades": args.max_oanda_trades,
        "max_oanda_trades_per_day": args.max_oanda_trades_per_day,
        "local_paper_max_reps": args.local_paper_max_reps,
        "stage": args.stage,
        "steps": {},
        "status": "blocked",
        "selected_candidate": None,
        "skipped_candidates": [],
        "duplicate_blocked_candidates": [],
        "rotated_to_candidate": None,
        "local_paper_fallback_reason": None,
        "no_trade_reason": None,
        "next_candidate_queue": [],
        "oanda_practice_trades_placed": 0,
        "local_paper_reps": 0,
        "asset_lanes_used": [],
        "recommended_strategy_research_tasks": [],
    }
    if not safety["safe"]:
        result["steps"]["safety"] = {"ok": False, "blockers": safety.get("blockers", [])}
        REPORT_FILE.write_text(json.dumps(result, indent=2))
        print(json.dumps(result, indent=2))
        return 1
    result["steps"]["safety"] = {"ok": True, "details": safety}

    try:
        receiver_status = {
            "health": _fetch("http://127.0.0.1:5000/health"),
            "status": _fetch("http://127.0.0.1:5000/status"),
        }
        result["steps"]["receiver"] = {"ok": True, **receiver_status}
    except Exception as exc:
        result["steps"]["receiver"] = {"ok": False, "error": str(exc)}
        REPORT_FILE.write_text(json.dumps(result, indent=2))
        print(json.dumps(result, indent=2))
        return 1

    try:
        adapter = OandaDemoAdapter()
        oanda_status = adapter.connection_status()
        daily_count = adapter.daily_order_count()
        result["steps"]["oanda"] = {
            "ok": bool(oanda_status.get("ok")),
            "daily_order_count": daily_count,
            "run_cap_remaining": max(0, args.max_oanda_trades),
            "daily_cap_remaining": max(0, args.max_oanda_trades_per_day - daily_count),
            "connection_status": oanda_status,
        }
    except OandaSafetyError as exc:
        result["steps"]["oanda"] = {"ok": False, "error": str(exc), "run_cap_remaining": 0, "daily_cap_remaining": 0}
    except Exception as exc:
        result["steps"]["oanda"] = {"ok": False, "error": str(exc), "run_cap_remaining": 0, "daily_cap_remaining": 0}

    code, payload, raw = _run_json([sys.executable, str(ROOT / "scripts" / "hermes_supabase_strategy_search.py"), "--asset-class", "all", "--limit", "20"])
    result["steps"]["strategy_search"] = {"ok": code == 0, "payload": payload, "output": raw}

    code, payload, raw = _run_json([sys.executable, str(ROOT / "scripts" / "build_trading_intelligence_packet.py"), "--dry-run"])
    result["steps"]["intelligence_packet"] = {"ok": code == 0, "payload": payload, "output": raw}

    tournament_cmd = [
        sys.executable,
        str(ROOT / "scripts" / "run_nexus_trading_tournament.py"),
        "--mode",
        "paper",
        "--source",
        "supabase_first",
        "--data-source",
        "oanda_practice",
        "--symbols",
        "EURUSD,USDJPY,GBPUSD",
        "--no-submit",
    ]
    if args.dry_run:
        tournament_cmd.append("--dry-run")
    code, payload, raw = _run_json(tournament_cmd)
    result["steps"]["tournament"] = {"ok": code == 0, "payload": payload, "output": raw}

    tournament = _load_json(ROOT / "logs" / "nexus_trading_tournament_latest.json")
    packet = _load_json(ROOT / "logs" / "trading_intelligence_packet_latest.json")
    recent_activity = _build_recent_activity(result["steps"]["receiver"])
    oanda_run_cap_remaining = int((result["steps"]["oanda"] or {}).get("run_cap_remaining") or 0)
    oanda_cap_remaining = int((result["steps"]["oanda"] or {}).get("daily_cap_remaining") or 0)

    oanda_queue = _tournament_candidates(tournament, packet)
    local_paper_queue = _local_paper_candidates(packet)
    full_queue = oanda_queue + local_paper_queue
    result["next_candidate_queue"] = _queue_preview(full_queue)

    selected: dict[str, Any] | None = None
    rotated_to: dict[str, Any] | None = None
    duplicate_blocked: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    cooldown_seconds = _cooldown_seconds()
    for candidate in full_queue:
        signal = dict(candidate.get("signal_payload") or {})
        duplicate_reason = _duplicate_reason(candidate, recent_activity, cooldown_seconds)
        if duplicate_reason:
            blocked = {**_json_candidate(candidate), "duplicate_reason": duplicate_reason, "skip_reason": duplicate_reason}
            duplicate_blocked.append(blocked)
            skipped.append(blocked)
            continue
        if candidate.get("execution_eligibility") == "oanda_practice":
            if not result["steps"]["oanda"].get("ok"):
                skip = {**_json_candidate(candidate), "skip_reason": "oanda_practice_unavailable"}
                skipped.append(skip)
                continue
            if oanda_run_cap_remaining <= 0:
                skip = {**_json_candidate(candidate), "skip_reason": "oanda_run_cap_exhausted"}
                skipped.append(skip)
                continue
            if oanda_cap_remaining <= 0:
                skip = {**_json_candidate(candidate), "skip_reason": "oanda_cap_exhausted"}
                skipped.append(skip)
                continue
        selected = candidate
        if skipped:
            rotated_to = candidate
        break

    result["selected_candidate"] = _json_candidate(selected)
    result["skipped_candidates"] = skipped
    result["duplicate_blocked_candidates"] = duplicate_blocked
    result["rotated_to_candidate"] = _json_candidate(rotated_to)

    submission: dict[str, Any] | None = None
    if selected and not args.dry_run:
        try:
            submission = _post_signal(selected["signal_payload"])
        except Exception as exc:
            result["no_trade_reason"] = str(exc)
            submission = {"accepted": False, "error": str(exc)}
        if submission:
            status, rejection = _submission_result(submission)
            if rejection and ("duplicate_signal" in rejection or rejection.startswith("cooldown_active_")):
                blocked = {**_json_candidate(selected), "duplicate_reason": rejection, "skip_reason": rejection}
                duplicate_blocked.append(blocked)
                skipped.append(blocked)
                result["duplicate_blocked_candidates"] = duplicate_blocked
                result["skipped_candidates"] = skipped
                selected = None
                result["selected_candidate"] = None
                for candidate in full_queue:
                    if any(item.get("strategy_id") == candidate.get("strategy_id") and item.get("symbol") == candidate.get("symbol") and item.get("direction") == candidate.get("direction") for item in skipped):
                        continue
                    if candidate.get("execution_eligibility") == "oanda_practice" and oanda_run_cap_remaining <= 0:
                        continue
                    if candidate.get("execution_eligibility") == "oanda_practice" and oanda_cap_remaining <= 0:
                        continue
                    if _duplicate_reason(candidate, recent_activity, cooldown_seconds):
                        continue
                    selected = candidate
                    rotated_to = candidate
                    result["selected_candidate"] = _json_candidate(selected)
                    result["rotated_to_candidate"] = _json_candidate(rotated_to)
                    break
                if selected:
                    submission = _post_signal(selected["signal_payload"])
                    status, rejection = _submission_result(submission)
                else:
                    status, rejection = "rejected", rejection
            result["submission"] = submission
            if selected:
                if status == "executed_oanda_practice":
                    result["oanda_practice_trades_placed"] = 1
                    result["asset_lanes_used"].append("forex")
                elif status == "approved_demo":
                    result["local_paper_reps"] = 1
                    result["local_paper_fallback_reason"] = rejection or "non_forex_or_oanda_fallback"
                    result["asset_lanes_used"].append(str(selected.get("asset_class") or "local_paper"))
                else:
                    result["no_trade_reason"] = rejection or status
    elif selected and args.dry_run:
        if selected.get("execution_eligibility") == "local_paper":
            result["local_paper_fallback_reason"] = "dry_run_local_paper_candidate_selected"
            result["asset_lanes_used"].append(str(selected.get("asset_class") or "local_paper"))
        else:
            result["asset_lanes_used"].append("forex")

    if not selected:
        local_candidate = None
        for candidate in local_paper_queue:
            if _duplicate_reason(candidate, recent_activity, cooldown_seconds):
                continue
            local_candidate = candidate
            break
        if local_candidate:
            result["selected_candidate"] = _json_candidate(local_candidate)
            result["rotated_to_candidate"] = _json_candidate(local_candidate) if skipped else None
            result["local_paper_fallback_reason"] = "no_safe_oanda_candidate"
            result["asset_lanes_used"].append(str(local_candidate.get("asset_class") or "local_paper"))
            if not args.dry_run:
                submission = _post_signal(local_candidate["signal_payload"])
                result["submission"] = submission
                status, rejection = _submission_result(submission)
                if status == "approved_demo":
                    result["local_paper_reps"] = 1
                else:
                    result["no_trade_reason"] = rejection or status
        else:
            result["no_trade_reason"] = "no_safe_candidate_available"

    code, payload, raw = _run_json([sys.executable, str(ROOT / "scripts" / "run_vibe_trading_review.py"), "--latest-tournament"])
    result["steps"]["vibe_review"] = {"ok": code == 0, "payload": payload, "output": raw}

    result["recommended_strategy_research_tasks"] = _research_tasks(skipped)

    result["status"] = "completed" if result["steps"]["receiver"].get("ok") else "blocked"
    REPORT_FILE.write_text(json.dumps(result, indent=2, default=str))

    code, payload, raw = _run_json([sys.executable, str(ROOT / "scripts" / "send_trading_status_report.py"), "--dry-run"])
    result["steps"]["hermes_report"] = {"ok": code == 0, "payload": payload, "output": raw}
    REPORT_FILE.write_text(json.dumps(result, indent=2, default=str))
    append_jsonl(
        "reports",
        {
            "created_at": _now(),
            "report_type": "nexus_demo_trading_loop",
            "mode": args.mode,
            "stage": args.stage,
            "receiver_status": "healthy" if result["steps"]["receiver"].get("ok") else "blocked",
            "broker_status": "oanda_practice" if result["steps"]["oanda"].get("ok") else "local_paper_only",
            "live_trading_enabled": False,
            "paper_trading_enabled": True,
            "summary": "Nexus demo trading loop run with candidate rotation",
            "verified_facts": result,
        },
    )
    print(json.dumps(result, indent=2, default=str))
    return 0 if result["steps"]["receiver"].get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
