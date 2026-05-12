# Paper Trading Engine Progress — Updated Report
**Date:** 2026-05-12 | **Pass:** Trading Demo Platform (updated) | **Phase:** 2 — Paper Execution Live
**Safety:** NEXUS_DRY_RUN=true | LIVE_TRADING=false | No real execution

## Pass 3 Additions

### paper_trade_executor.py (new in Pass 3)
Full lifecycle paper trade executor:

| Function | Purpose |
|---|---|
| `get_practice_price(symbol)` | OANDA practice API (read-only) with synthetic fallback |
| `_check_circuit_breaker(strategy_id)` | Integrates lib.circuit_breaker.is_halted() |
| `_check_risk_limits(...)` | 5-layer pre-check: position count, SL, TP, R:R, account risk % |
| `open_paper_position(...)` | Full entry: CB check → risk check → live price → slippage → position |
| `check_exit_conditions(...)` | SL/TP hit detection per position direction |
| `close_paper_position(...)` | PnL calc (pips + USD), timestamps, status update |

**Slippage model:** 0.5–1.5 pip random per trade (realistic for paper simulation).

### SessionHeatmap.tsx (new in Pass 3)
- 24-bar win rate visualization (clickable, shows tooltip with WR/trades/avg pips)
- Session band overlays (Asia, London, NY Open, Overlap)
- Per-session breakdown table with edge decay warning

## Remaining for Phase 3
- [ ] Wire paper_trade_executor to real Supabase journal writes
- [ ] Session intelligence fed from actual closed positions
- [ ] Backtesting results page (BacktestResult visualization)
- [ ] Paper trade replay with historical OANDA tick data
- [ ] Graduated approval for live execution (30+ paper trades + operator sign-off)

---
**Original report continues below:**


---

## Existing Infrastructure

The paper trading engine infrastructure already existed prior to this pass:

### nexus-strategy-lab/trading/simulator.py
- `simulate_trade(strategy: dict) → dict`
- Covers 4 asset classes: forex, crypto, equities, futures
- Synthetic price generation with realistic spread/slippage
- Outcome weighted by strategy's Supabase `strategy_scores.total_score`
- Produces: symbol, side, entry/exit prices, SL, TP, PnL, duration, events list

### nexus-strategy-lab/trading/journal.py
- Writes closed paper trades to Supabase `paper_trading_journal_entries`
- Writes detailed outcome to `paper_trading_outcomes`
- Links journal_id → outcome for full audit trail

### Supabase tables (existing)
- `paper_trading_journal_entries` — trade records
- `paper_trading_outcomes` — result details

---

## New Components (This Pass)

### nexus-strategy-lab/trading/session_intelligence.py
Session-level analytics layer:
- Win rate by session: Asia, London, NY Open, Overlap
- Hour-of-day heatmap
- Edge decay detection: warns when win rate drops > 15% below baseline
- `best_session()` / `worst_session()` for Hermes recommendations

### nexuslive/src/components/PaperTradingArena.tsx (Prior pass)
UI layer for paper trading:
- Live open trades with TP progress bars
- Recent closes journal tab
- Weekly stats (win rate, profit factor)
- PAPER MODE safety indicator always visible

---

## Phase 2 Paper Trading Roadmap

### Step 1: Risk Engine Python Implementation
Create `lib/risk_engine.py`:
- 10 layers as callable Python functions
- Each layer: `check(signal) → {passed: bool, reason: str}`
- All layers must pass for trade to execute

### Step 2: Live Price Feed
Connect to OANDA practice API for real-time prices:
- `OANDA_API_URL=https://api-fxpractice.oanda.com` (already in .env)
- Practice account — no real funds
- Price streaming for SL/TP hit simulation

### Step 3: Paper Trade Executor
Create `nexus-strategy-lab/trading/paper_trade_executor.py`:
- Entry: risk_engine passes → place simulated order at market
- Exit: monitor price stream for SL/TP hit → close trade
- Journal: write result to Supabase on close

### Step 4: Supabase Schema Extension
Deploy new tables:
- `risk_checks` — 10-layer results per signal
- `circuit_breaker_events` — CB fire/reset history
- Update `paper_trades` for full field coverage

### Step 5: Strategy Registry Wiring
Replace mock data in `StrategyRegistry.tsx`:
- Query Supabase `paper_trading_journal_entries` grouped by strategy
- Compute live win rate, profit factor, trade count
- Show real progress to 30-trade minimum

---

## Live Criteria (Paper → Human Approval)

Before any live discussion begins, each strategy must meet:
- ≥ 30 paper trades
- Win rate within 10% of backtest win rate
- Profit factor > 1.5 over 30+ trades
- Max paper drawdown < 50% of approved live limit
- Human review of complete trade journal
- Operator sign-off on risk parameters
- Circuit breakers tested and verified
