from __future__ import annotations

from dataclasses import dataclass
from typing import Any


PROMOTION_STATES = {"new", "researching", "testing", "watchlist", "hall_of_fame", "rejected", "archived"}


@dataclass
class StrategyDNA:
    setup_name: str
    market_type: str
    entry_trigger: str
    confirmation: str
    stop_loss: str
    take_profit: str
    invalidation: str
    risk_reward: str
    session: str
    best_market_condition: str
    worst_market_condition: str
    failure_pattern: str
    journal_lesson: str


def extract_strategy_dna(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "setup_name": payload.get("setup_name") or payload.get("setup") or "Unknown setup",
        "market_type": payload.get("market_type") or payload.get("category") or "forex",
        "entry_trigger": payload.get("entry_trigger") or "Trigger not defined",
        "confirmation": payload.get("confirmation") or "Confirmation not defined",
        "stop_loss": payload.get("stop_loss") or "Required",
        "take_profit": payload.get("take_profit") or "Required",
        "invalidation": payload.get("invalidation") or "Invalidation not defined",
        "risk_reward": payload.get("risk_reward") or "1.5R",
        "session": payload.get("session") or "unknown",
        "best_market_condition": payload.get("best_market_condition") or "trending",
        "worst_market_condition": payload.get("worst_market_condition") or "choppy",
        "failure_pattern": payload.get("failure_pattern") or "low-liquidity fakeout",
        "journal_lesson": payload.get("journal_lesson") or "Document failure conditions before next run.",
    }


def strategy_record(payload: dict[str, Any]) -> dict[str, Any]:
    dna = extract_strategy_dna(payload)
    return {
        "category": payload.get("category") or dna.get("market_type"),
        "source": payload.get("source") or "internal",
        "setup": dna.get("setup_name"),
        "strategy_dna": dna,
        "confidence": float(payload.get("confidence") or 0.0),
        "risk_level": payload.get("risk_level") or "medium",
        "market_condition_fit": payload.get("market_condition_fit") or dna.get("best_market_condition"),
        "win_loss_history": payload.get("win_loss_history") or {"wins": 0, "losses": 0},
        "drawdown_behavior": payload.get("drawdown_behavior") or "unknown",
        "paper_trading_results": payload.get("paper_trading_results") or {},
        "lessons_learned": payload.get("lessons_learned") or [dna.get("journal_lesson")],
        "promotion_status": payload.get("promotion_status") or "new",
    }


def promotion_decision(record: dict[str, Any]) -> dict[str, Any]:
    results = record.get("paper_trading_results") or {}
    win_rate = float(results.get("win_rate") or 0.0)
    drawdown = float(results.get("max_drawdown") or 999.0)
    rr = float(results.get("avg_rr") or 0.0)
    repeatable = bool(results.get("repeatable_setup", False))
    has_failure_map = bool(record.get("strategy_dna", {}).get("failure_pattern"))

    promote = win_rate >= 55 and drawdown <= 3.0 and rr >= 1.5 and repeatable and has_failure_map
    status = "hall_of_fame" if promote else "watchlist"
    reason = (
        "Consistent demo performance, controlled drawdown, and repeatable setup."
        if promote
        else "Needs more consistent demo data or stronger risk metrics."
    )
    return {"promotion_status": status, "reason": reason}
