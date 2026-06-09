from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from lib.trading_market_data import generate_strategy_signals_from_candles


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _family(candidate: dict[str, Any]) -> str:
    return str(candidate.get("strategy_family") or "").lower()


def _strategy_id(candidate: dict[str, Any]) -> str:
    return str(candidate.get("strategy_id") or "unknown")


def _signal_base(candidate: dict[str, Any], data_quality: str, execution_allowed: bool) -> dict[str, Any]:
    return {
        "symbol": candidate.get("symbol"),
        "asset_class": candidate.get("asset_class", "forex"),
        "strategy_id": _strategy_id(candidate),
        "trigger_type": candidate.get("trigger_type", "manual_review_only"),
        "direction": "NONE",
        "confidence": float(candidate.get("confidence_score") or candidate.get("confidence") or 0.0),
        "setup_detected": False,
        "entry_price": None,
        "stop_loss": None,
        "take_profit": None,
        "risk_reward": None,
        "reason": "no_setup_detected",
        "data_quality": data_quality,
        "execution_allowed": execution_allowed,
        "rejection_reason": "no_setup_detected",
        "evaluated_at": _now(),
    }


def _risk_reward(entry: float | None, stop: float | None, target: float | None) -> float | None:
    if entry is None or stop is None or target is None:
        return None
    risk = abs(entry - stop)
    reward = abs(target - entry)
    if risk <= 0:
        return None
    return round(reward / risk, 2)


@dataclass
class BaseWatcher:
    candidate: dict[str, Any]

    def evaluate(self, market_bundle: dict[str, Any], *, execute: bool = False, session_name: str | None = None) -> dict[str, Any]:
        raise NotImplementedError

    def _market_signal(self, market_bundle: dict[str, Any], *, execute: bool = False) -> dict[str, Any]:
        candles = market_bundle.get("candles") or []
        base = _signal_base(self.candidate, str(market_bundle.get("data_quality") or "unknown"), execute)
        if len(candles) < 5:
            base["reason"] = "insufficient_candles"
            base["rejection_reason"] = "insufficient_candles"
            return base
        rows = generate_strategy_signals_from_candles(
            _strategy_id(self.candidate),
            str(self.candidate.get("symbol") or market_bundle.get("symbol") or "EURUSD"),
            str(self.candidate.get("timeframe") or market_bundle.get("timeframe") or "H1"),
            candles,
            limit=1,
        )
        if not rows:
            base["reason"] = "rules_not_triggered_on_current_window"
            base["rejection_reason"] = "rules_not_triggered_on_current_window"
            return base
        row = rows[0]
        base.update(
            {
                "direction": row.get("action"),
                "setup_detected": True,
                "entry_price": row.get("entry_price"),
                "stop_loss": row.get("stop_loss"),
                "take_profit": row.get("take_profit"),
                "risk_reward": _risk_reward(row.get("entry_price"), row.get("stop_loss"), row.get("take_profit")),
                "reason": "setup_detected",
                "rejection_reason": None,
            }
        )
        return base


class TechnicalIndicatorWatcher(BaseWatcher):
    def evaluate(self, market_bundle: dict[str, Any], *, execute: bool = False, session_name: str | None = None) -> dict[str, Any]:
        signal = self._market_signal(market_bundle, execute=execute)
        if not signal["setup_detected"]:
            signal["reason"] = "indicator_conditions_not_met"
            signal["rejection_reason"] = "indicator_conditions_not_met"
        return signal


class SessionOpenWatcher(BaseWatcher):
    def evaluate(self, market_bundle: dict[str, Any], *, execute: bool = False, session_name: str | None = None) -> dict[str, Any]:
        signal = self._market_signal(market_bundle, execute=execute)
        signal["session_name"] = session_name or self.candidate.get("session_rules") or "session_open"
        if not signal["setup_detected"]:
            signal["reason"] = "session_window_active_but_breakout_not_confirmed"
            signal["rejection_reason"] = "session_window_active_but_breakout_not_confirmed"
        return signal


class NewsEventWatcher(BaseWatcher):
    def evaluate(self, market_bundle: dict[str, Any], *, execute: bool = False, session_name: str | None = None) -> dict[str, Any]:
        signal = _signal_base(self.candidate, str(market_bundle.get("data_quality") or "unknown"), False)
        signal["reason"] = "news_calendar_not_integrated_local_only"
        signal["rejection_reason"] = "news_calendar_not_integrated_local_only"
        return signal


class HybridSetupWatcher(BaseWatcher):
    def evaluate(self, market_bundle: dict[str, Any], *, execute: bool = False, session_name: str | None = None) -> dict[str, Any]:
        signal = self._market_signal(market_bundle, execute=execute)
        if not signal["setup_detected"]:
            signal["reason"] = "hybrid_context_missing_confirmation"
            signal["rejection_reason"] = "hybrid_context_missing_confirmation"
        return signal


def watcher_for_candidate(candidate: dict[str, Any]) -> BaseWatcher:
    family = _family(candidate)
    trigger = str(candidate.get("trigger_type") or "").lower()
    execution_style = str(candidate.get("execution_style") or "").lower()
    if trigger == "news_calendar_event" or family == "news_event":
        return NewsEventWatcher(candidate)
    if trigger == "scheduled_session" or execution_style == "event_window" or family in {"session_open", "breakout"}:
        return SessionOpenWatcher(candidate)
    if family == "hybrid":
        return HybridSetupWatcher(candidate)
    return TechnicalIndicatorWatcher(candidate)


def evaluate_candidate(candidate: dict[str, Any], market_bundle: dict[str, Any], *, execute: bool = False, session_name: str | None = None) -> dict[str, Any]:
    return watcher_for_candidate(candidate).evaluate(market_bundle, execute=execute, session_name=session_name)
