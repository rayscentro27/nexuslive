# Nexus Replay Lab — Phase 4

**Research only. No live trading. No broker execution. No order placement.**

---

## Architecture

The Replay Lab simulates trade outcomes from AI-reviewed proposals stored in Supabase. It operates entirely offline from any broker, using deterministic simulation to score proposals and calibrate the AI's confidence model.

```
reviewed_signal_proposals
        │
        ▼
  replay_poll.js ──── filters out already-replayed proposals
        │
        ▼
replay_context.js ── attaches scenario metadata
        │
        ├─ forex proposals → forex_replay_engine.js (static R:R simulation)
        └─ options proposals → options_replay_engine.js (historical profile simulation)
        │
        ▼
paper_result_writer.js ── writes to paper_trade_runs + replay_results
        │
        ├─ calibration_engine.js ── confidence_calibration table
        ├─ replay_scorecards.js  ── per-strategy scorecard log
        └─ telegram_replay_alert.js ── Telegram summary report
```

---

## Supabase Tables

### `paper_trade_runs`
Tracks each simulation run.

| Column       | Type      | Notes                                   |
|--------------|-----------|-----------------------------------------|
| id           | uuid      | Primary key (auto)                      |
| proposal_id  | uuid      | FK to reviewed_signal_proposals         |
| signal_id    | uuid      | FK to tv_normalized_signals             |
| asset_type   | text      | "forex" or "options"                    |
| symbol       | text      | e.g. "EUR_USD", "SPY"                   |
| strategy_id  | text      | e.g. "trend_follow", "covered_call"     |
| replay_mode  | text      | "forex_static_rr" or "options_historical_profile" |
| status       | text      | "running" → "finished"                  |
| trace_id     | text      | Traceability ID                         |
| finished_at  | timestamptz | Set when run completes                |

### `replay_results`
Stores simulation outcomes.

| Column            | Type    | Notes                                        |
|-------------------|---------|----------------------------------------------|
| id                | uuid    | Primary key (auto)                           |
| run_id            | uuid    | FK to paper_trade_runs                       |
| proposal_id       | uuid    | FK to reviewed_signal_proposals              |
| signal_id         | uuid    |                                              |
| asset_type        | text    |                                              |
| symbol            | text    |                                              |
| strategy_id       | text    |                                              |
| strategy_type     | text    | Redundant copy for fast queries              |
| replay_outcome    | text    | "tp_hit", "sl_hit", "breakeven", "win", "loss", "expired" |
| pnl_r             | numeric | R-multiple PnL (forex only)                  |
| pnl_pct           | numeric | % gain/loss                                  |
| hit_take_profit   | boolean |                                              |
| hit_stop_loss     | boolean |                                              |
| expired           | boolean |                                              |
| bars_to_resolution| integer | Simulated bars (null for options)            |
| trace_id          | text    |                                              |
| created_at        | timestamptz | Auto                                    |

### `confidence_calibration`
Calibration results per confidence band.

| Column            | Type    | Notes                                        |
|-------------------|---------|----------------------------------------------|
| confidence_band   | text    | PK: "0.0-0.3", "0.3-0.5", etc.             |
| samples           | integer |                                              |
| wins              | integer |                                              |
| losses            | integer |                                              |
| actual_win_rate   | numeric |                                              |
| expected_win_rate | numeric | Midpoint of the band                         |
| calibration_gap   | numeric | actual - expected (positive = underconfident)|
| computed_at       | timestamptz |                                          |

---

## Run Commands

```bash
# Replay all pending proposals
node replay_runner.js --once

# Replay up to 5 proposals
node replay_runner.js --limit 5

# Replay only EUR/USD proposals
node replay_runner.js --symbol EURUSD

# Replay only a specific strategy
node replay_runner.js --strategy trend_follow

# Calibration analysis only (no new replays)
node replay_runner.js --calibrate
```

Or use npm scripts:
```bash
npm run once
npm run calibrate
```

---

## Simulation Methodology

### Forex — Static R:R (`forex_replay_engine.js`)

No live price data is used. The outcome is determined entirely by the proposal's
own `entry_price`, `stop_loss`, and `take_profit` values.

```
risk   = |entry_price - stop_loss|
reward = |take_profit - entry_price|
R:R    = reward / risk
```

| R:R         | Outcome    | pnl_r       |
|-------------|------------|-------------|
| >= 2.0      | tp_hit     | +rr_ratio   |
| 1.5 – 1.99  | breakeven  | 0           |
| < 1.5       | sl_hit     | -1.0        |

This approach is deliberately conservative: only proposals with a strong R:R
qualify as wins in simulation, ensuring quality signal discipline.

### Options — Historical Profile (`options_replay_engine.js`)

Options strategies are evaluated against empirical win-rate profiles derived
from historical strategy performance data. No live data feed is required.

```
effective_win_prob = (strategy_base_win_rate + ai_confidence) / 2
```

| effective_win_prob | Outcome    |
|--------------------|------------|
| >= 0.55            | win        |
| 0.45 – 0.54        | breakeven  |
| < 0.45             | loss       |

Supported strategies: `covered_call`, `cash_secured_put`, `iron_condor`,
`credit_spread`, `debit_spread`, `straddle`, `strangle`, `butterfly`,
`calendar_spread`, `zebra_strategy`, `wheel_strategy`.

---

## Calibration Explanation

Calibration measures how well the AI's stated confidence scores match actual
simulated outcomes. A perfectly calibrated AI would win 80% of the time on
proposals it rated 0.7–0.9 confidence.

**Confidence bands and expected win rates:**

| Band      | Expected Win Rate |
|-----------|-------------------|
| 0.0 – 0.3 | 15%               |
| 0.3 – 0.5 | 40%               |
| 0.5 – 0.7 | 60%               |
| 0.7 – 0.9 | 80%               |
| 0.9 – 1.0 | 95%               |

`calibration_gap = actual_win_rate - expected_win_rate`

- Negative gap = AI is **overconfident** (claims high confidence but loses more than expected)
- Positive gap = AI is **underconfident** (wins more than its stated confidence predicts)

---

## Validation SQL

```sql
-- Replay outcomes by strategy
SELECT strategy_id, replay_outcome, COUNT(*)
FROM replay_results
GROUP BY strategy_id, replay_outcome
ORDER BY strategy_id, replay_outcome;

-- Calibration summary
SELECT confidence_band, actual_win_rate, expected_win_rate, calibration_gap
FROM confidence_calibration
ORDER BY confidence_band;

-- Paper trade run status breakdown
SELECT status, COUNT(*)
FROM paper_trade_runs
GROUP BY status;

-- Average PnL by asset type
SELECT asset_type, AVG(pnl_r) AS avg_pnl_r, COUNT(*) AS total
FROM replay_results
GROUP BY asset_type;
```

---

## Safety Rules

1. **No live trading.** This module never calls any broker API.
2. **No order placement.** `DRY_RUN=True` is the assumed posture for all upstream engines.
3. **Read-only Supabase for polls.** Writes use `SUPABASE_SERVICE_ROLE_KEY` only for `paper_trade_runs`, `replay_results`, and `confidence_calibration`.
4. **No external price feeds.** All simulation is static and deterministic.
5. **Telegram alerts are informational only.** They contain no actionable trading instructions.
6. **Review calibration gaps before increasing AI confidence thresholds** in any upstream system.
