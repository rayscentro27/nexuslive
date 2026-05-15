# Demo Trading Guardrails

Date: 2026-05-15

Implemented in `lib/autonomous_demo_trading_lab.py` via `evaluate_guardrails()`.

Required hard guardrails enforced (fail => no trade):
- max concurrent demo trades
- max trades per day
- max daily demo drawdown
- max risk per demo trade
- stop loss required
- take profit required
- cooldown after losing streak
- session filters
- kill switch
- trade reason required
- strategy ID required

Result: If any guardrail fails, the trade is blocked.
