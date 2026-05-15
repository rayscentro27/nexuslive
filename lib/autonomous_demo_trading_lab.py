from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
STATE_DIR = ROOT / "state"
STATUS_FILE = ROOT / "logs" / "trading_engine_status.json"
PAUSE_FILE = STATE_DIR / "demo_trading_paused.json"
JOURNAL_FILE = STATE_DIR / "demo_trade_journal.json"
LEARNING_FILE = STATE_DIR / "demo_strategy_learning.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _flag(name: str, default: str) -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


def _read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def verify_demo_mode() -> dict[str, Any]:
    api_url = os.getenv("OANDA_API_URL", "https://api-fxpractice.oanda.com")
    using_practice = "fxpractice" in api_url
    live_endpoint = "fxtrade" in api_url or "live" in api_url
    posture = {
        "autonomous_paper_trading": _flag("AUTONOMOUS_PAPER_TRADING", "true"),
        "oanda_demo_autonomy": _flag("OANDA_DEMO_AUTONOMY", "true"),
        "trading_simulation_mode": _flag("TRADING_SIMULATION_MODE", "true"),
        "real_money_trading": _flag("REAL_MONEY_TRADING", "false"),
        "live_trading": _flag("LIVE_TRADING", "false"),
        "trading_live_execution_enabled": _flag("TRADING_LIVE_EXECUTION_ENABLED", "false"),
        "oanda_api_url": api_url,
        "practice_endpoint": using_practice,
        "live_endpoint_detected": live_endpoint,
        "safe": using_practice and not live_endpoint and not _flag("REAL_MONEY_TRADING", "false") and not _flag("LIVE_TRADING", "false") and not _flag("TRADING_LIVE_EXECUTION_ENABLED", "false"),
    }
    return posture


def get_guardrail_config() -> dict[str, Any]:
    return {
        "max_concurrent_demo_trades": int(os.getenv("DEMO_MAX_CONCURRENT_TRADES", "3")),
        "max_trades_per_day": int(os.getenv("DEMO_MAX_TRADES_PER_DAY", "8")),
        "max_daily_demo_drawdown": float(os.getenv("DEMO_MAX_DAILY_DRAWDOWN", "250")),
        "max_risk_per_demo_trade_percent": float(os.getenv("DEMO_MAX_RISK_PER_TRADE_PERCENT", "1.0")),
        "required_stop_loss": True,
        "required_take_profit": True,
        "cooldown_after_losing_streak": int(os.getenv("DEMO_COOLDOWN_MINUTES", "30")),
        "losing_streak_limit": int(os.getenv("DEMO_LOSING_STREAK_LIMIT", "3")),
        "allowed_sessions": ["london", "new york", "ny", "us overlap", "london/ny overlap"],
        "kill_switch_enabled": bool(_read_json(PAUSE_FILE, {}).get("paused", False)),
        "trade_reason_required": True,
        "strategy_id_required": True,
    }


def evaluate_guardrails(signal: dict[str, Any], context: dict[str, Any] | None = None) -> tuple[bool, list[str]]:
    context = context or {}
    cfg = get_guardrail_config()
    issues: list[str] = []
    active = int(context.get("active_trades", 0))
    trades_today = int(context.get("trades_today", 0))
    daily_pnl = float(context.get("daily_pnl", 0.0))
    losing_streak = int(context.get("losing_streak", 0))
    session = str(signal.get("session") or "").lower()
    risk_percent = float(signal.get("risk_percent") or 0.0)

    if cfg["kill_switch_enabled"]:
        issues.append("demo kill switch enabled")
    if active >= cfg["max_concurrent_demo_trades"]:
        issues.append("max concurrent demo trades reached")
    if trades_today >= cfg["max_trades_per_day"]:
        issues.append("max trades per day reached")
    if daily_pnl <= -abs(cfg["max_daily_demo_drawdown"]):
        issues.append("daily demo drawdown limit reached")
    if risk_percent <= 0 or risk_percent > cfg["max_risk_per_demo_trade_percent"]:
        issues.append("risk per demo trade exceeds limit")
    if cfg["required_stop_loss"] and signal.get("stop_loss") in (None, "", 0):
        issues.append("stop loss required")
    if cfg["required_take_profit"] and signal.get("take_profit") in (None, "", 0):
        issues.append("take profit required")
    if losing_streak >= cfg["losing_streak_limit"]:
        issues.append("cooldown after losing streak active")
    if session and session not in cfg["allowed_sessions"]:
        issues.append("session filter blocked")
    if not str(signal.get("trade_reason") or "").strip():
        issues.append("trade reason required")
    if not str(signal.get("strategy_id") or "").strip():
        issues.append("strategy ID required")
    return len(issues) == 0, issues


def pause_demo_trading(actor: str = "hermes") -> dict[str, Any]:
    payload = {"paused": True, "actor": actor, "updated_at": _now()}
    _write_json(PAUSE_FILE, payload)
    return payload


def resume_demo_trading(actor: str = "hermes") -> dict[str, Any]:
    payload = {"paused": False, "actor": actor, "updated_at": _now()}
    _write_json(PAUSE_FILE, payload)
    return payload


def record_trade_learning(entry: dict[str, Any]) -> dict[str, Any]:
    journal = _read_json(JOURNAL_FILE, [])
    if not isinstance(journal, list):
        journal = []
    entry = dict(entry)
    entry.setdefault("created_at", _now())
    journal.append(entry)
    _write_json(JOURNAL_FILE, journal[-500:])

    learning = _read_json(LEARNING_FILE, {"strategy_confidence": {}, "lessons": []})
    if not isinstance(learning, dict):
        learning = {"strategy_confidence": {}, "lessons": []}
    sid = str(entry.get("strategy_id") or "unknown")
    before = float((learning.get("strategy_confidence", {}) or {}).get(sid, 0.5))
    pnl = float(entry.get("pnl", 0.0))
    after = max(0.0, min(1.0, before + (0.03 if pnl > 0 else -0.04 if pnl < 0 else 0.0)))
    learning.setdefault("strategy_confidence", {})[sid] = round(after, 4)
    learning.setdefault("lessons", []).append(
        {
            "strategy_id": sid,
            "result": "win" if pnl > 0 else "loss" if pnl < 0 else "flat",
            "lesson": entry.get("lesson") or "Review entry quality, session context, and risk discipline.",
            "created_at": _now(),
        }
    )
    _write_json(LEARNING_FILE, learning)
    return {"strategy_id": sid, "confidence_before": before, "confidence_after": after}


def build_demo_status_snapshot() -> dict[str, Any]:
    engine_status = _read_json(STATUS_FILE, {})
    journal = _read_json(JOURNAL_FILE, [])
    learning = _read_json(LEARNING_FILE, {"strategy_confidence": {}, "lessons": []})
    pause = _read_json(PAUSE_FILE, {"paused": False})
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    today_entries = [j for j in journal if str(j.get("created_at", "")).startswith(today)] if isinstance(journal, list) else []
    wins = sum(1 for j in today_entries if float(j.get("pnl", 0.0)) > 0)
    losses = sum(1 for j in today_entries if float(j.get("pnl", 0.0)) < 0)
    pnl = round(sum(float(j.get("pnl", 0.0)) for j in today_entries), 2)
    return {
        "demo_label": "DEMO / PAPER TRADING ONLY",
        "autonomous_demo_enabled": _flag("AUTONOMOUS_PAPER_TRADING", "true") and _flag("OANDA_DEMO_AUTONOMY", "true"),
        "real_money_trading_disabled": not _flag("REAL_MONEY_TRADING", "false") and not _flag("LIVE_TRADING", "false") and not _flag("TRADING_LIVE_EXECUTION_ENABLED", "false"),
        "kill_switch": bool(pause.get("paused", False)),
        "active_demo_trades": int(engine_status.get("active_positions", 0) or 0),
        "daily_demo_pnl": pnl,
        "daily_win_loss": {"wins": wins, "losses": losses},
        "strategy_confidence": (learning.get("strategy_confidence") or {}),
        "recent_lessons": (learning.get("lessons") or [])[-5:],
        "trade_journal_recent": today_entries[-8:],
        "risk_status": get_guardrail_config(),
    }


def last_losing_trade_lesson() -> str:
    journal = _read_json(JOURNAL_FILE, [])
    if not isinstance(journal, list):
        return "No demo trade journal entries yet."
    for row in reversed(journal):
        if float(row.get("pnl", 0.0)) < 0:
            return str(row.get("lesson") or "Loss logged. Improve context alignment and tighten invalidation rules.")
    return "No losing demo trades recorded yet."
