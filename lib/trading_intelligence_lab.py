from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
import os


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _flag(name: str, default: str) -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


def strategy_templates() -> list[dict[str, Any]]:
    base = {
        "stop_loss_rules": "fixed invalidation plus volatility guard",
        "take_profit_rules": "partial at 1R, runner into trend continuation",
        "risk_per_trade_percent": 0.5,
        "max_daily_loss_percent": 2.0,
        "risk_reward_target": "2.0R",
        "confidence_score": 0.55,
        "stability_score": 0.6,
        "difficulty_level": "intermediate",
        "market_condition_fit": "trending or structured breakout",
        "hermes_coach_notes": "Educational paper-trading setup. Validate session context and risk limits before sim entry.",
        "visual_config": {"card_theme": "signal", "accent": "teal", "badge": "paper"},
        "educational_disclaimer": "Educational demo scenario only. Not financial advice. No guaranteed outcomes.",
    }
    rows = [
        {"strategy_name": "London Breakout", "market_type": "forex", "symbol_or_pair": "GBPUSD", "timeframe": "M15", "best_session": "London", "indicators": ["session range", "ATR"], "entry_rules": ["break of London range", "volume confirmation"], "exit_rules": ["close below breakout base"]},
        {"strategy_name": "SPY Trend Continuation", "market_type": "options", "symbol_or_pair": "SPY", "timeframe": "M30", "best_session": "New York", "indicators": ["VWAP", "EMA 20/50"], "entry_rules": ["pullback to trend support", "trend resumes"], "exit_rules": ["trend structure break"]},
        {"strategy_name": "BTC/ETH Trend Structure", "market_type": "crypto", "symbol_or_pair": "BTCUSD", "timeframe": "H1", "best_session": "US overlap", "indicators": ["market structure", "RSI"], "entry_rules": ["higher low confirmation", "momentum recovery"], "exit_rules": ["lower-low breakdown"]},
        {"strategy_name": "Trend Pullback", "market_type": "forex", "symbol_or_pair": "EURUSD", "timeframe": "M30", "best_session": "London/NY overlap", "indicators": ["EMA", "ADX"], "entry_rules": ["pullback to moving average", "trend resumption candle"], "exit_rules": ["trend invalidation"]},
        {"strategy_name": "Liquidity Sweep Reversal", "market_type": "forex", "symbol_or_pair": "USDJPY", "timeframe": "M15", "best_session": "London", "indicators": ["liquidity highs/lows", "orderflow proxy"], "entry_rules": ["sweep then reclaim", "confirmation close"], "exit_rules": ["retest failure"]},
        {"strategy_name": "Iron Condor Income", "market_type": "options", "symbol_or_pair": "SPY", "timeframe": "D1", "best_session": "New York", "indicators": ["IV rank", "range width"], "entry_rules": ["high IV environment", "balanced range"], "exit_rules": ["range expansion warning"]},
        {"strategy_name": "Earnings Volatility Watchlist", "market_type": "options", "symbol_or_pair": "QQQ", "timeframe": "D1", "best_session": "New York", "indicators": ["implied vol", "event calendar"], "entry_rules": ["pre-event volatility setup"], "exit_rules": ["post-event crush"]},
        {"strategy_name": "Momentum Breakout", "market_type": "crypto", "symbol_or_pair": "ETHUSD", "timeframe": "M30", "best_session": "US overlap", "indicators": ["range expansion", "volume"], "entry_rules": ["breakout with volume"], "exit_rules": ["failed follow-through"]},
        {"strategy_name": "Funding Rate Reversal", "market_type": "crypto", "symbol_or_pair": "BTCUSD", "timeframe": "H4", "best_session": "24h", "indicators": ["funding rate", "open interest"], "entry_rules": ["extreme funding divergence"], "exit_rules": ["normalization complete"]},
    ]
    out = []
    for row in rows:
        merged = dict(base)
        merged.update(row)
        out.append(merged)
    return out


def performance_metrics_shape() -> dict[str, Any]:
    return {
        "paper_trade_count": 0,
        "win_rate": 0.0,
        "average_rr": 0.0,
        "profit_factor": 0.0,
        "max_drawdown": 0.0,
        "demo_account_growth": 0.0,
        "weekly_result": 0.0,
        "monthly_result": 0.0,
        "consistency_score": 0.0,
        "last_tested_at": _now(),
    }


def build_trading_intelligence_report() -> dict[str, Any]:
    templates = strategy_templates()
    launch = [t for t in templates if t.get("strategy_name") in {"London Breakout", "SPY Trend Continuation", "BTC/ETH Trend Structure"}]
    return {
        "timestamp": _now(),
        "enabled": _flag("TRADING_INTELLIGENCE_LAB_ENABLED", "true"),
        "trading_live_execution_enabled": _flag("TRADING_LIVE_EXECUTION_ENABLED", "false"),
        "trading_paper_only": _flag("TRADING_PAPER_ONLY", "true"),
        "trading_coach_educational_only": _flag("TRADING_COACH_EDUCATIONAL_ONLY", "true"),
        "strategy_templates": templates,
        "launch_focus_strategies": launch,
        "active_strategy_tests": [],
        "top_strategy_candidates": [s.get("strategy_name") for s in launch],
        "strategy_health": {"status": "monitoring", "risk_score": "moderate"},
        "demo_results": performance_metrics_shape(),
        "coach_prompt_template": "Provide an educational paper-trading setup, risk-managed scenario, and demo validation checklist.",
    }
