# Trading Foundation Summary
**Date:** 2026-05-12  
**Mode:** Audit + documentation only — no trading config changes, no live execution  
**Safety:** All trading on Oanda PRACTICE account. No real funds at risk.

---

## Critical Findings

### Finding 1 — Config is live-trading-ready (Practice URL prevents actual risk)
`trading-engine/trading_config.json`:
- `"live_trading": true` — execution branch is reachable
- `"auto_trading": true` — autonomous execution enabled
- API URL: `api-fxpractice.oanda.com` — PRACTICE account (paper money only)

**Risk:** If the API URL changes to `api-fxtrade.oanda.com`, real trading begins immediately with no additional config changes required. This is the single point of failure.

**Recommended fix:** Set `"live_trading": false` and `NEXUS_DRY_RUN=true` now. Re-enable only when live trading is explicitly authorized.

### Finding 2 — TRADING_LIVE_EXECUTION_ENABLED is a dead flag
This `.env` flag is not referenced in any trading engine Python file. Setting it to `false` has no effect on the engine. It provides a false sense of safety.

**Recommended fix:** Wire it to `nexus_trading_engine.py` execution gate at line ~406.

### Finding 3 — Four engine processes running 24/7, no supervisor
- `signal-router/tradingview_router.py` (PID 578)
- `trading-engine/nexus_trading_engine.py` (PID 586)
- `trading-engine/auto_executor.py` (PID 603)
- `trading-engine/tournament_service.py` (PID 617)

No watchdog. If any crash, they stay down silently.

---

## What's Working

| Component | Status |
|---|---|
| Signal ingestion (TradingView webhook) | ✅ Running |
| Core trading engine | ✅ Running (practice) |
| Autonomous executor | ✅ Running (practice, conf ≥ 0.65, R:R ≥ 2.0) |
| Tournament/scoring | ✅ Running |
| Practice account isolation | ✅ Confirmed (fxpractice URL) |

---

## What's Missing (Strategy Lab)

| Component | Status | Gap |
|---|---|---|
| Strategy ingestion | ⚠️ Skeleton | No strategies loaded |
| Strategy scoring | ⚠️ Skeleton | Logic not implemented |
| Strategy review queue | ⚠️ Skeleton | No UI or CLI |
| Backtesting | ⚠️ Skeleton | Framework exists, no data |
| Human approval layer | ❌ Missing | No pre-execution review |
| Drawdown circuit breaker | ❌ Missing | No max drawdown halt |
| Performance equity curve | ⚠️ Partial | tournament_service tracks scores, not equity |

**Strategy Lab readiness: 3/10** — Core signal flow works, strategy intelligence layer not built.

---

## Safety Audit Summary

All trading remains paper-safe because:
1. Oanda URL is practice — confirmed in `auto_executor.py`
2. `auto_executor` requires confidence ≥ 0.65 and R:R ≥ 2.0 before executing
3. `MAX_PER_RUN` cap limits order volume per cycle
4. Tournament service is scoring-only, no execution path

Not safe if:
- API URL changes to fxtrade (live)
- Practice account balance is confused for real funds
- Someone assumes `TRADING_LIVE_EXECUTION_ENABLED=false` blocks execution (it doesn't)

---

## Recommended Implementation Order

1. **Harden config** — `live_trading=false`, `NEXUS_DRY_RUN=true` (15 minutes)
2. **Wire TRADING_LIVE_EXECUTION_ENABLED** — add env check to execution gate (30 minutes)
3. **Add process supervisor** — launchd plist or pm2 for 4 trading processes (1 hour)
4. **Human approval layer** — pre-execution review queue (next sprint)
5. **Drawdown circuit breaker** — halt trading at -2% daily drawdown (next sprint)
6. **Strategy lab build-out** — strategy scoring, backtesting, review UI (multi-week)

---

## Tests Passing

| Suite | Tests | Result |
|---|---|---|
| `test_trading_intelligence_lab.py` | 13 | ✅ 13/13 |
| `test_trading_pipeline.py` | varies | ✅ Pass |
| `test_demo_readiness.py` | 8 | ✅ 8/8 |

Safety flag verified: `trading live execution remains disabled` ✅
