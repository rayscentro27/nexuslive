# Trading System Foundation Audit
**Date:** 2026-05-12  
**Mode:** Audit only — no changes to trading config, no live execution enabled  
**Safety:** All trading remains on Oanda PRACTICE account (api-fxpractice.oanda.com). No live execution authorized.

---

## CRITICAL FLAGS — READ FIRST

| Flag | Value | Risk |
|---|---|---|
| `trading_config.json → live_trading` | `true` | ⚠️ HIGH — Config allows live execution branch |
| `trading_config.json → auto_trading` | `true` | ⚠️ HIGH — Enables autonomous order placement |
| `.env → NEXUS_DRY_RUN` | `false` | ⚠️ HIGH — Engine DRY_RUN bypass is NOT active |
| Oanda API URL | `api-fxpractice.oanda.com` | ✅ Practice account — paper trading only |
| `TRADING_LIVE_EXECUTION_ENABLED` | Not referenced by engine | ⚠️ MEDIUM — Intended safety flag has no effect |

**Bottom line:** The trading engine is connected to a PRACTICE account, so no real money is at risk today. However, the config flags `live_trading: true` + `auto_trading: true` + `NEXUS_DRY_RUN=false` mean the engine is operating in its most permissive mode. If the API URL were ever changed to `api-fxtrade.oanda.com`, actual live trading would begin without any additional config change. This must be remediated before any live account credentials are present.

---

## 1. Active Processes

Four trading processes are running continuously:

| PID | Process | Role |
|---|---|---|
| 578 | `signal-router/tradingview_router.py` | Ingests TradingView signals via webhook |
| 586 | `trading-engine/nexus_trading_engine.py` | Core order management and execution |
| 603 | `trading-engine/auto_executor.py` | Autonomous execution from signal queue |
| 617 | `trading-engine/tournament_service.py` | Competition/scoring management |

All four processes run as persistent daemons. No supervisor or watchdog monitors them — if they crash, they stay down until manually restarted.

---

## 2. Directory Structure

```
nexus-ai/
├── trading-engine/
│   ├── nexus_trading_engine.py     — Core engine: order mgmt, execution gate
│   ├── auto_executor.py            — Autonomous executor: min conf=0.65, min R:R=2.0
│   ├── tournament_service.py       — Competition scoring
│   └── trading_config.json         — CRITICAL: live_trading=true, auto_trading=true
├── signal-router/
│   └── tradingview_router.py       — TradingView webhook ingestion
├── nexus-strategy-lab/
│   ├── ingestion/                  — Strategy intake pipeline
│   ├── scoring/                    — Strategy quality scoring
│   ├── review/                     — Manual review queue
│   └── backtest/                   — Backtesting infrastructure
└── workflows/
    ├── trading_analyst/            — JS-based analyst with Supabase + Telegram alerts
    └── ai_workforce/
        └── trading_research_worker — AI workforce trading research component
```

---

## 3. Execution Gate Analysis

### nexus_trading_engine.py
- **Lines 127-129:** DRY_RUN check — when `NEXUS_DRY_RUN=true`, forces demo mode
- **Line 406:** `if self.config.get('live_trading', False):` — actual execution branch
- **Current state:** `NEXUS_DRY_RUN=false` in .env → DRY_RUN protection NOT active
- **Current state:** `live_trading=true` in config → execution branch IS reachable
- **Protection:** API URL points to `fxpractice` → orders land on paper account

### auto_executor.py
- Explicitly targets `api-fxpractice.oanda.com` in its connection config
- Has `MAX_PER_RUN` cap — limits orders per execution cycle
- Requires minimum confidence 0.65 and minimum R:R 2.0 before executing
- These are sensible guards but are not safety flags — they are tunable parameters

### TRADING_LIVE_EXECUTION_ENABLED
- Present in `.env` (or expected to be)
- **Not referenced in any trading engine Python file**
- This flag has no effect on the running system
- If an operator assumes setting this to `false` prevents live execution, they are wrong

---

## 4. Strategy Lab Assessment

### nexus-strategy-lab/ — Not yet operational
- Directory structure exists: ingestion/, scoring/, review/, backtest/
- No active processes observed
- Represents future pipeline for: strategy ingestion → scoring → backtesting → paper trading
- Currently: dormant skeleton

### workflows/trading_analyst/
- JS-based, Supabase-integrated
- Sends Telegram alerts on signal events
- Risk: Telegram alert spam if signal volume is high and no rate limiting

### workflows/ai_workforce/trading_research_worker
- AI-driven research component
- Feeds into strategy pipeline
- Currently: low activity (no observed output)

---

## 5. Signal Flow (Current)

```
TradingView alert → tradingview_router.py (webhook)
    → signal queue
    → nexus_trading_engine.py (strategy + risk evaluation)
    → auto_executor.py (execution gate: conf ≥ 0.65, R:R ≥ 2.0)
    → Oanda Practice API (api-fxpractice.oanda.com)
    → paper order placed
    → tournament_service.py (scoring update)
```

No human-in-the-loop step in this current flow. All decisions are autonomous.

---

## 6. Risk Matrix

| Risk | Severity | Current State | Recommended Fix |
|---|---|---|---|
| API URL swap → instant live trading | CRITICAL | Practice URL active | Add URL validation in engine startup |
| `live_trading=true` in config | HIGH | Active | Change to `false` until live is authorized |
| `NEXUS_DRY_RUN=false` | HIGH | Active | Set to `true` for safe default posture |
| `TRADING_LIVE_EXECUTION_ENABLED` not wired | HIGH | Dead flag | Remove or wire to actual gate |
| No human approval step | HIGH | None present | Add pre-execution approval queue |
| No watchdog for engine processes | MEDIUM | No supervisor | Add launchd or pm2 process manager |
| Telegram spam from trading alerts | MEDIUM | Potential | Rate-limit alerts in hermes_gate |
| Credentials in trading_config.json | MEDIUM | Oanda practice key present | Move to .env, never commit |
| auto_executor MAX_PER_RUN not visible | LOW | Configured but not monitored | Log MAX_PER_RUN on startup |

---

## 7. Recommended Immediate Actions

### Priority 1 — Config hardening (do before anything else)
```
trading_config.json:
  "live_trading": false       ← change from true
  "auto_trading": false       ← change from true (re-enable manually when ready)

.env:
  NEXUS_DRY_RUN=true          ← change from false
```
These three changes make the engine safe even if the API URL changes.

### Priority 2 — Wire the intended safety flag
In `nexus_trading_engine.py` at the execution gate (line ~406), add:
```python
if os.getenv("TRADING_LIVE_EXECUTION_ENABLED", "false").lower() != "true":
    # redirect to paper path regardless of config
    ...
```
This makes `TRADING_LIVE_EXECUTION_ENABLED=false` actually protective.

### Priority 3 — Human approval layer (Strategy Lab)
Before the strategy lab goes live, add a pre-execution review queue:
- Proposed trades land in a review queue
- Operator reviews via CLI or Telegram `/review trades`
- Approval required before execution
- Timeout = no-execute (never auto-approve)

### Priority 4 — Process supervision
Add launchd plist or pm2 config to:
- Auto-restart crashed trading processes
- Log startup/shutdown events
- Alert via Telegram on unexpected restart

### Priority 5 — Credentials hygiene
- Move Oanda API key from `trading_config.json` to `.env`
- Add `trading_config.json` to `.gitignore` or redact credentials section
- Rotate practice key if it has appeared in any git history

---

## 8. Strategy Lab Readiness Assessment

| Component | Status | Gap |
|---|---|---|
| Signal ingestion (TradingView webhook) | ✅ Running | None — operational |
| Strategy scoring | ⚠️ Skeleton | Scoring logic not implemented |
| Strategy review queue | ⚠️ Skeleton | No UI or CLI for review |
| Backtesting | ⚠️ Skeleton | Framework exists, no strategies loaded |
| Paper trading loop | ✅ Running | Via auto_executor → practice API |
| Human approval layer | ❌ Missing | No approval step before execution |
| Performance analytics | ⚠️ Partial | tournament_service.py tracks scores, no equity curve |
| Money management rules | ⚠️ Partial | Min confidence + R:R in auto_executor; no drawdown circuit breaker |

**Strategy Lab overall readiness: 3/10** — Core signal flow works but strategy intelligence, human review, and safety layer are not built.

---

## 9. What's Safe Right Now

The system is safe for continued use because:
1. Oanda API URL points to practice (fxpractice.oanda.com) — confirmed in auto_executor.py
2. Practice account = paper money only, no real funds at risk
3. auto_executor has minimum confidence and R:R gates
4. tournament_service.py is scoring-only, no execution

**What changes everything:** Swapping the API URL to `api-fxtrade.oanda.com`. If that happens with current config (`live_trading: true`, `auto_trading: true`, `NEXUS_DRY_RUN: false`), the engine would immediately begin placing real trades. There is no other barrier.

---

## 10. Tests Needed (Not Yet Run)

- [ ] Confirm practice URL is hardcoded (not pulled from config that could change)
- [ ] Confirm NEXUS_DRY_RUN=true actually prevents execution (unit test the gate)
- [ ] Confirm auto_executor MAX_PER_RUN is enforced even at high signal volume
- [ ] Confirm tournament_service has no execution path
- [ ] Confirm tradingview_router validates webhook payload before queuing signal

---

**Audit conclusion:** System is paper-safe today due to practice URL. Config posture is live-trading-ready — one URL change away from real execution. Hardening the config (`live_trading=false`, `NEXUS_DRY_RUN=true`) and wiring `TRADING_LIVE_EXECUTION_ENABLED` are the two actions that would make this system genuinely safe rather than coincidentally safe.
