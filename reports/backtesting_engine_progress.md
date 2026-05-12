# Backtesting Engine Progress Report
**Date:** 2026-05-12  
**Phase:** D1 — Backtesting Engine Implementation  
**Safety:** NEXUS_DRY_RUN=true enforced — no live execution possible

---

## What Was Built

### nexus-strategy-lab/backtest/engine.py (NEW)

Full backtesting engine with synthetic price replay.

**BacktestConfig dataclass:**
- `strategy_id`, `market`, `asset_class`, `session`
- `risk_pct_per_trade` (default 1.0%)
- `starting_balance` (default $10,000)
- `num_trades` (default 50)
- `min_rr` (minimum risk:reward, default 2.0)
- `win_rate_assumption` (for synthetic replay)
- `slippage_pips`

**BacktestResult dataclass (computed properties):**
- `win_rate`, `wins`, `losses`
- `profit_factor` (gross_profit / gross_loss)
- `net_pnl`, `max_drawdown_pct`
- `expectancy_r` (average R-multiple)
- `avg_win_usd`, `avg_loss_usd`
- `equity_curve` (list of balance values)
- `meets_min_criteria` — True if: 30+ trades, WR ≥ 50%, PF ≥ 1.5, drawdown ≤ 10%

**run_backtest(config) function:**
- Generates synthetic price series with noise
- Simulates long/short entries with SL/TP
- Applies slippage cost per trade
- Builds equity curve for drawdown calculation
- Raises RuntimeError if `NEXUS_DRY_RUN=false` (safety guard)

**quick_test() convenience function:**
- 50-trade test on EURUSD London session
- Default 60% win rate assumption, 2:1 R:R

**Verified test run:**
```
win_rate: 56.0%  (50 trades)  meets_min_criteria: True
```
(Win rate varies by random seed — typical range 50-65% with 60% assumption)

---

## What Exists (Pre-existing)

### nexus-strategy-lab/trading/simulator.py
- `simulate_trade(strategy)` — single paper trade simulation
- Fetches real strategy scores from Supabase when available
- Covers forex, crypto, equities, futures

### nexus-strategy-lab/trading/journal.py
- `write_journal_entry(trade, strategy)` → Supabase `paper_trading_journal_entries`
- `write_outcome(journal_id, trade)` → Supabase `paper_trading_outcomes`
- Full paper trade lifecycle logging

### nexus-strategy-lab/trading/session_intelligence.py (NEW — this pass)
- `classify_session(dt)` → "london" | "ny_open" | "overlap" | "asia"
- `analyze_session_performance(trades)` → per-session win rate, PF, avg PnL
- `best_session(performance)`, `worst_session(performance)`
- `detect_edge_decay(trades, baseline_win_rate)` → {decaying: bool, delta_pct, message}
- `session_heatmap(trades)` → 24-hour win rate array

---

## What's Next (Phase D2 — Paper Trading Engine)

1. Wire `run_backtest()` output to strategy approval checklist
2. Implement `paper_trade_executor.py` — real-time paper simulation using live OANDA practice prices
3. Deploy Supabase schema: `paper_trades`, `risk_checks`, `circuit_breaker_events`
4. Wire `session_intelligence.analyze_session_performance()` to Hermes weekly digest
5. Strategy registry: replace mock data in `StrategyRegistry.tsx` with Supabase queries

---

## Performance Metrics Targets

| Metric | Formula | Minimum for Live Discussion |
|---|---|---|
| Win Rate | wins / total_trades | > 50% |
| Profit Factor | gross_profit / gross_loss | > 1.5 |
| Max Drawdown | equity curve drawdown | < 10% |
| Expectancy | avg R-multiple | > 0 |
| Trades | count | ≥ 30 |

No strategy advances to Phase 3 (human approval) without meeting all 5 targets.
