# Trade Avoidance Intelligence

Implemented in `lib/adaptive_trading_intelligence.py` via `no_trade_decision()`.

No-trade triggers include:
- choppy/no-trade state
- news instability
- high fakeout risk
- low liquidity
- overtrading/revenge-trading behavior markers

Output includes reasons, discipline quality, and avoided drawdown estimate.
