# Adaptive Strategy Confidence

Implemented in `lib/adaptive_trading_intelligence.py` via `adaptive_strategy_confidence()`.

Confidence adapts to:
- market state fit
- volatility fit
- recent drawdown
- fakeout frequency
- strategy stability

Result: confidence is dynamic and context-aware instead of static pass/fail.
