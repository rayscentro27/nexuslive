# Strategy Learning Loop

Date: 2026-05-15

Implemented in `lib/autonomous_demo_trading_lab.py` via `record_trade_learning()`.

Per-trade tracking includes:
- win/loss (via pnl)
- entry reason
- exit reason
- strategy used
- session timing
- market conditions
- drawdown proxy (from pnl)
- RR ratio
- stop loss hit
- take profit hit
- fakeout detection
- volatility state
- confidence before/after
- lesson learned text

Persistence:
- trade journal: `state/demo_trade_journal.json`
- strategy confidence + lessons: `state/demo_strategy_learning.json`

Goal met: Hermes can safely learn from demo failures without real-money execution.
