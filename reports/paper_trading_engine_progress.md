# Paper Trading Engine Progress Report
**Date:** 2026-05-12  
**Phase:** D2 — Paper Trading Engine  
**Safety:** NEXUS_DRY_RUN=true | LIVE_TRADING=false | No real execution

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
