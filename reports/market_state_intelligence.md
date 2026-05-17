# Market State Intelligence

Implemented in `lib/adaptive_trading_intelligence.py` via `classify_market_state()`.

Supported states:
- trending
- ranging
- breakout
- reversal
- high volatility
- low volatility
- liquidity hunt
- news-driven instability
- mean reversion environment
- trend continuation environment
- choppy/no-trade environment

Tracked fields: confidence, volatility, liquidity conditions, session, momentum, trend structure, fakeout risk, trade suitability.
