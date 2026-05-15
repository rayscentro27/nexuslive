#!/usr/bin/env python3
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from lib.autonomous_demo_trading_lab import (
    build_demo_status_snapshot,
    evaluate_guardrails,
    pause_demo_trading,
    record_trade_learning,
    resume_demo_trading,
    verify_demo_mode,
)


def check(label: str, ok: bool) -> bool:
    print(f"{'[PASS]' if ok else '[FAIL]'} {label}")
    return ok


def main() -> int:
    os.environ.setdefault("AUTONOMOUS_PAPER_TRADING", "true")
    os.environ.setdefault("OANDA_DEMO_AUTONOMY", "true")
    os.environ.setdefault("TRADING_SIMULATION_MODE", "true")
    os.environ.setdefault("REAL_MONEY_TRADING", "false")
    os.environ.setdefault("LIVE_TRADING", "false")
    os.environ.setdefault("TRADING_LIVE_EXECUTION_ENABLED", "false")
    os.environ.setdefault("OANDA_API_URL", "https://api-fxpractice.oanda.com")

    ok = True
    posture = verify_demo_mode()
    ok &= check("demo account endpoint verification", posture.get("practice_endpoint") is True)
    ok &= check("real-money endpoint blocked", posture.get("live_endpoint_detected") is False)
    ok &= check("real-money trading disabled", posture.get("real_money_trading") is False)
    ok &= check("live trading disabled", posture.get("live_trading") is False)

    valid_signal = {
        "stop_loss": 1.09,
        "take_profit": 1.12,
        "risk_percent": 0.8,
        "trade_reason": "breakout retest",
        "strategy_id": "london_breakout",
        "session": "london",
    }
    guard_ok, _ = evaluate_guardrails(valid_signal, {"active_trades": 0, "trades_today": 1, "daily_pnl": 40, "losing_streak": 0})
    ok &= check("valid guardrail pass allowed", guard_ok)

    blocked, issues = evaluate_guardrails({"risk_percent": 2.0}, {"active_trades": 9, "trades_today": 20, "daily_pnl": -999, "losing_streak": 5})
    ok &= check("guardrail fail blocks trade", blocked is False and len(issues) > 0)
    ok &= check("stop loss required", any("stop loss" in i for i in issues))
    ok &= check("take profit required", any("take profit" in i for i in issues))
    ok &= check("max concurrent positions enforced", any("concurrent" in i for i in issues))
    ok &= check("daily drawdown enforced", any("drawdown" in i for i in issues))

    pause_demo_trading("test")
    blocked2, issues2 = evaluate_guardrails(valid_signal, {"active_trades": 0, "trades_today": 1, "daily_pnl": 0, "losing_streak": 0})
    ok &= check("kill switch blocks trading", blocked2 is False and any("kill switch" in i for i in issues2))
    resume_demo_trading("test")

    learn = record_trade_learning({
        "strategy_id": "london_breakout",
        "entry_reason": "range break",
        "exit_reason": "stop_loss_hit",
        "market_conditions": "choppy",
        "rr_ratio": 0.6,
        "stop_loss_hit": True,
        "take_profit_hit": False,
        "fakeout_detected": True,
        "volatility_state": "high",
        "confidence_before": 0.61,
        "confidence_after": 0.57,
        "lesson": "Avoid first fake breakout when volatility is unstable.",
        "pnl": -23.5,
    })
    ok &= check("trade journal writes", isinstance(learn, dict) and "confidence_after" in learn)

    snap = build_demo_status_snapshot()
    ok &= check("strategy confidence updates", isinstance(snap.get("strategy_confidence"), dict))

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
