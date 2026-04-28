# Nexus Performance Lab — Phase 3

**RESEARCH ONLY. No live trading. No broker connections. No order placement.**

This system reads outcome data from Supabase, computes performance metrics for strategies and AI agents, writes rankings and scorecards back to Supabase, and sends Telegram summaries.

---

## Architecture Overview

```
proposal_outcomes          (source of truth for trade results)
       │
       ├── strategy_metrics.js   → per-strategy forex metrics
       ├── options_metrics.js    → per-strategy options metrics
       ├── analyst_metrics.js    → AI analyst accuracy metrics
       └── risk_metrics.js       → risk office decision metrics
              │
              ├── ranking_engine.js     → writes strategy_performance + options_strategy_performance
              ├── scorecard_generator.js → writes agent_scorecards
              └── telegram_performance_alert.js → sends Telegram HTML report
```

Entry point: `performance_runner.js`

---

## Supabase Tables

| Table | Purpose |
|---|---|
| `proposal_outcomes` | Ground truth — recorded wins/losses/breakevens/expireds |
| `reviewed_signal_proposals` | AI analyst proposals with ai_confidence scores |
| `approval_queue` | Risk office decisions (approved / manual_review / blocked) |
| `risk_decisions` | Detailed risk decisions with risk_score and risk_flags |
| `strategy_performance` | Computed forex strategy metrics and rankings (written by this lab) |
| `options_strategy_performance` | Computed options strategy metrics and rankings (written by this lab) |
| `agent_scorecards` | Analyst and risk office performance metrics (written by this lab) |

---

## Run Commands

```bash
# Generate all agent scorecards (analyst + risk office)
npm run scorecards
# or
node performance_runner.js --scorecards

# Rank all strategies and send Telegram performance summary
npm run rank
# or
node performance_runner.js --rank

# Ingest an outcome file
npm run ingest -- outcome.json
# or
node performance_runner.js --ingest outcome.json
```

---

## How to Record an Outcome

Create a JSON file (e.g., `outcome.json`) with an array of outcome objects:

```json
[
  {
    "proposal_id": "abc-123",
    "symbol": "EURUSD",
    "strategy_id": "breakout_v2",
    "asset_type": "forex",
    "outcome_status": "win",
    "pnl_r": 2.1,
    "pnl_pct": null,
    "mfe": 2.4,
    "mae": -0.3,
    "notes": "Closed at TP1 after London session breakout",
    "trace_id": "trace-xyz"
  },
  {
    "proposal_id": "def-456",
    "symbol": "GBPUSD",
    "strategy_id": "mean_reversion_v1",
    "asset_type": "forex",
    "outcome_status": "loss",
    "pnl_r": -1.0,
    "pnl_pct": null,
    "mfe": 0.5,
    "mae": -1.2,
    "notes": "Stop hit on NFP spike",
    "trace_id": null
  }
]
```

**Required fields:** `proposal_id`, `symbol`, `strategy_id`, `outcome_status`

**Valid outcome_status values:** `win`, `loss`, `breakeven`, `expired`

**R-multiple fields:** `pnl_r` represents profit/loss in R units (e.g., 2.0 = 2R win, -1.0 = 1R loss). `pnl_pct` is percentage-based (primarily for options).

Then run:

```bash
node performance_runner.js --ingest outcome.json
```

---

## Validation SQL

Run these in the Supabase SQL editor to verify the system:

```sql
-- Forex strategy rankings
SELECT strategy_id, win_rate, expectancy, score, ranking_label
FROM strategy_performance
ORDER BY score DESC;

-- Agent scorecards
SELECT agent_name, metric_type, metric_value
FROM agent_scorecards
ORDER BY agent_name, metric_type;

-- Outcome distribution
SELECT outcome_status, COUNT(*)
FROM proposal_outcomes
GROUP BY outcome_status;

-- Options rankings
SELECT strategy_type, win_rate, avg_pnl_pct, score, ranking_label
FROM options_strategy_performance
ORDER BY score DESC;

-- Pending outcomes (approved but not yet recorded)
SELECT aq.proposal_id, rsp.symbol, rsp.strategy_id
FROM approval_queue aq
JOIN reviewed_signal_proposals rsp ON rsp.proposal_id = aq.proposal_id
LEFT JOIN proposal_outcomes po ON po.proposal_id = aq.proposal_id
WHERE aq.decision = 'approved'
  AND po.proposal_id IS NULL;
```

---

## Ranking Score Formula

### Forex Strategies
```
score = (win_rate * 100) × 0.40
      + normalize(expectancy, -2..2) × 0.40
      + normalize(trades_count, 0..max) × 0.20
```

**Ranking Labels:**
| Score | Label |
|---|---|
| >= 80 | elite |
| >= 65 | strong |
| >= 45 | average |
| >= 25 | weak |
| < 25 | poor |

### Options Strategies
```
score = (win_rate * 100) × 0.50
      + normalize(avg_pnl_pct, -50..50) × 0.30
      + normalize(trades_count, 0..max) × 0.20
```

---

## Safety Rules

1. **NO LIVE TRADING** — This lab never connects to Oanda, IBKR, or any broker API.
2. **NO ORDER PLACEMENT** — The system only reads Supabase and writes metrics tables.
3. **READ-ONLY SOURCE DATA** — Uses `SUPABASE_KEY` (anon) for all reads.
4. **WRITES USE SERVICE ROLE** — `SUPABASE_SERVICE_ROLE_KEY` only used for writing metrics/scorecards/rankings, never for trading actions.
5. **DRY RUN BOUNDARY** — The trading engine (`trading-engine/`) remains separate. This lab does not import from it.
6. **Mac Mini scope** — Runs locally on Mac Mini. Does not SSH to Oracle VM or deploy to cloud.
