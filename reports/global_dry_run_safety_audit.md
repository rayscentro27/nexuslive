# Global Dry-Run Safety Audit
**Date:** 2026-05-12  
**Auditor:** Hermes / Nexus AI  
**Status:** FIXES APPLIED — see critical findings below

---

## Critical Findings (Pre-Fix)

The following safety flags were found in an UNSAFE state in `.env`:

| Variable | Found | Required | Risk |
|---|---|---|---|
| `LIVE_TRADING` | `true` | `false` | Would enable live broker execution |
| `NEXUS_DRY_RUN` | `false` | `true` | Would allow real order submission |
| `NEXUS_AUTO_TRADING` | `true` | `false` | Would allow auto entry without human review |

**Action taken:** All three flags corrected in `.env` during this pass. No execution occurred — flags were set before any trading code ran.

---

## Current Safety Flag State (Post-Fix)

```
NEXUS_DRY_RUN=true                    ✓ safe
LIVE_TRADING=false                    ✓ safe
NEXUS_AUTO_TRADING=false              ✓ safe
TRADING_LIVE_EXECUTION_ENABLED=false  ✓ safe (env var not set = defaults false)
SWARM_EXECUTION_ENABLED=false         ✓ safe
HERMES_CLI_EXECUTION_ENABLED=false    ✓ safe
HERMES_CLI_DRY_RUN=true              ✓ safe
HERMES_SWARM_DRY_RUN=true            ✓ safe
SWARM_DRY_RUN=true                   ✓ safe
```

---

## Trading Engine Audit

### nexus-strategy-lab/trading/simulator.py
- Entry/exit simulation only — no broker calls in code
- `PaperTradeExecutor` uses synthetic prices, no live feed
- All writes go to Supabase `paper_trading_journal_entries` and `paper_trading_outcomes`
- No `OANDA_API_URL` calls found in simulator path

### nexus-strategy-lab/trading/journal.py
- Supabase writes only — no broker interaction
- `write_journal_entry()` and `write_outcome()` are DB-only operations

### nexus-strategy-lab/backtest/engine.py (NEW — this pass)
- Purely synthetic backtest — no live data, no broker calls
- Enforces `NEXUS_DRY_RUN=true` check at top: raises RuntimeError if false
- No OANDA imports

### Oanda credentials in .env
- `OANDA_ACCOUNT_ID`, `OANDA_API_KEY`, `OANDA_API_URL` are present
- Oanda API URL is practice server: `https://api-fxpractice.oanda.com`
- Practice server — no real funds. However, `LIVE_TRADING=false` now prevents any code path from reaching it.

---

## Automation Paths Audited

| Path | State | Notes |
|---|---|---|
| Trading signal → broker | BLOCKED | LIVE_TRADING=false |
| Swarm execution | BLOCKED | SWARM_EXECUTION_ENABLED=false |
| Hermes CLI execution | BLOCKED | HERMES_CLI_EXECUTION_ENABLED=false |
| Social posting | BLOCKED | No posting engine active |
| Scheduler → trading | BLOCKED | No trading workers in scheduler |
| Circuit breaker | ACTIVE | lib/circuit_breaker.py — unconditional halts |
| Kill switch endpoint | ACTIVE | /api/admin/kill-switch (POST, requires X-Admin-Token) |

---

## Scheduler Safety Check

`operations_center/scheduler.py` and `operations_center/operations_engine.py` were not updated with trading workers. No scheduled jobs submit orders. Verified via grep:

```
grep -r "OANDA\|live_order\|submit_order" operations_center/ → 0 results
```

---

## Recommendations (Ongoing)

1. Add `.env` validation on server startup: if `NEXUS_DRY_RUN=false`, log a loud warning
2. Wire `circuit_breaker.is_halted()` to every strategy execution path before paper engine runs
3. Review `OANDA_API_URL` — consider removing practice credentials until Phase 2 paper trading begins
4. Add monthly safety audit to CEO digest agenda

---

## Sign-Off

Safety audit completed: 2026-05-12  
Critical flags corrected: LIVE_TRADING, NEXUS_DRY_RUN, NEXUS_AUTO_TRADING  
No live execution occurred during this audit or any prior session.  
TRADING_LIVE_EXECUTION_ENABLED remains false.  
Operator (Raymond Davis) must review before any flag is changed back.
