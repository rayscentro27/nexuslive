# Paper Trading Platform Design
**Date:** 2026-05-12  
**Mode:** Design + architecture — paper trading only, NO live execution

---

## Purpose

Paper trading is not a "safe practice mode." It is the primary validation system. Every strategy must pass paper trading before any other discussion happens. Paper trading results are the evidence base for the human approval decision.

---

## Architecture

```
Strategy Registry
    ↓
Signal Generator (TradingView webhook or Hermes analysis)
    ↓
Risk Engine (all 10 layers — same as live)
    ↓
Paper Execution Engine
    ↓
Trade Journal
    ↓
Performance Analyzer (Hermes)
    ↓
CEO Report / Human Review
```

---

## Paper Execution Engine

### Entry Simulation
```python
class PaperTradeExecutor:
    def execute(self, signal: dict, risk_check: dict) -> PaperTrade:
        entry_price = self._simulate_entry(
            market_price=signal['market_price'],
            order_type=signal['order_type'],
            slippage_model=self.slippage_config,
        )
        position_size = risk_engine.position_size(
            account=self.paper_account,
            signal=signal,
        )
        return PaperTrade(
            strategy_id=signal['strategy_id'],
            direction=signal['direction'],
            entry_price=entry_price,
            stop_loss=signal['stop_loss'],
            take_profit=signal['take_profit'],
            size=position_size,
            opened_at=now(),
            status='open',
            mode='paper',
        )
```

### Slippage Model
- Market orders: add 0.5-2 pips simulated slippage (random within range)
- Limit orders: filled at limit price or better
- Stop orders: assume 1 pip beyond stop for adverse fills
- News events: slippage multiplied 3x during blackout window

### Exit Simulation
- TP hit: closed at TP price (or TP - 0.5 pip)
- SL hit: closed at SL price (or SL + 1 pip — adverse)
- Trailing stop: updated on each price check (5-second interval simulation)
- Manual close: closed at simulated market price

---

## Paper Account

```python
PAPER_ACCOUNT = {
    "balance":          10_000.00,  # starting paper capital
    "currency":         "USD",
    "leverage":         30,         # 30:1 (forex standard)
    "max_positions":    4,
    "mode":             "paper",
}
```

Account balance updates in real-time as trades open/close. Separate from any real broker account. Never connected to live funds.

---

## Trade Journal Schema

```sql
CREATE TABLE paper_trades (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    strategy_id     TEXT NOT NULL,
    market          TEXT NOT NULL,       -- EUR/USD, GBP/USD, etc
    direction       TEXT NOT NULL,       -- long | short
    entry_price     DECIMAL(12,5),
    stop_loss       DECIMAL(12,5),
    take_profit     DECIMAL(12,5),
    exit_price      DECIMAL(12,5),
    size_units      DECIMAL(10,2),
    size_lots       DECIMAL(6,2),
    pnl_pips        DECIMAL(8,1),
    pnl_usd         DECIMAL(10,2),
    commission      DECIMAL(8,2) DEFAULT 0,
    slippage_pips   DECIMAL(6,2),
    opened_at       TIMESTAMPTZ,
    closed_at       TIMESTAMPTZ,
    status          TEXT,               -- open | closed | stopped | tp_hit
    exit_reason     TEXT,               -- tp | sl | trailing | manual
    session         TEXT,               -- london | ny_open | asia | etc
    risk_score      INTEGER,
    ai_confidence   DECIMAL(4,2),
    hermes_note     TEXT,               -- Hermes analysis on close
    tags            TEXT[],
    mode            TEXT DEFAULT 'paper'
);
```

---

## Strategy Competition (Gamified)

Multiple strategies run simultaneously in paper mode. They compete:

```
Weekly Leaderboard:
┌────────────────────────────────────────┐
│  🥇 London Breakout v2.1  +4.2%  71% WR │
│  🥈 SPY Continuation       +2.8%  65% WR │
│  🥉 BTC Structure Break    +1.1%  58% WR │
│      NY Momentum            -0.4%  45% WR │
└────────────────────────────────────────┘
```

Metrics tracked per strategy per week:
- Total return %
- Win rate
- Profit factor
- Max drawdown
- Sharpe-style ratio
- Average R:R achieved
- Best session

---

## Performance Analytics

### Equity Curve
- Daily paper account balance plotted over time
- Benchmark: flat line at starting balance
- Drawdown shading: red zone when below high-water mark

### Session Heatmap
- Win rate by hour-of-day × day-of-week
- Reveals which sessions each strategy excels in
- Used to set `approved_sessions` in risk engine

### Strategy Evolution
- Win rate trend over rolling 20-trade window
- Flags edge deterioration: if win rate drops >15% from baseline
- Edge deterioration → Hermes review + strategy pause

### Profit Distribution
- Histogram of trade outcomes in R-multiples
- Ideal: right-skewed (many small losses, fewer large wins)
- Warning: left-skewed (large losses vs small wins)

---

## Performance Metrics Definitions

| Metric | Formula | Target |
|---|---|---|
| Win Rate | wins / total_trades | > 50% (depends on R:R) |
| Profit Factor | gross_profit / gross_loss | > 1.5 |
| Expectancy | avg_win*wr - avg_loss*(1-wr) | > 0 |
| Max Drawdown | max(equity_curve) - min | < 10% |
| Sharpe-style | avg_daily_pnl / stdev_daily_pnl | > 0.8 |
| R-Multiple | actual_profit / initial_risk | > 1.0 avg |
| Recovery Factor | net_profit / max_drawdown | > 2.0 |

---

## Paper Trading → Live Criteria (Future)

Before any live execution discussion can begin:
- [ ] 30+ paper trades on the strategy
- [ ] Win rate within 10% of backtest win rate
- [ ] Max paper drawdown < 50% of approved live limit
- [ ] Profit factor > 1.5 over 30 trades
- [ ] Human review of complete trade journal
- [ ] Human approval of risk parameters
- [ ] Human approval of automation permissions
- [ ] Circuit breakers tested and verified
- [ ] All above: documented and signed off

This criteria list does not authorize live trading. It defines the minimum evidence required before that conversation starts.

---

## UI: Paper Trading Arena

```
┌─────────────────────────────────────────────────────┐
│  📊 PAPER TRADING ARENA     Balance: $10,847 (+8.5%) │
│─────────────────────────────────────────────────────│
│  LIVE TRADES                                         │
│  EUR/USD LONG  Entry:1.0842  SL:1.0820  TP:1.0886  │
│  +18 pips  [████████░░░░  TP 42% filled]  ⚡ active │
│                                                      │
│  RECENT CLOSES                                       │
│  GBP/USD SHORT  +32 pips  ✅ TP hit  London session │
│  USD/JPY LONG   -15 pips  ❌ SL hit  Asia session   │
│                                                      │
│  THIS WEEK  Trades: 12  Win: 8  P&L: +$847  4.2%   │
│  ████████░░ Win Rate 67%   Profit Factor 2.1x       │
│                                                      │
│  [Trade Journal] [Performance] [Hermes Analysis]    │
└─────────────────────────────────────────────────────┘
```
