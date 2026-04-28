# Nexus Optimization Lab

**Phase 5 — Strategy Optimization Lab**

Research-only system that analyzes historical signal proposals, replay results, and risk decisions to produce data-driven parameter improvement suggestions. No live trading, no broker execution, no order placement.

---

## Architecture

### Data Flow

```
INPUT (reads from)                     OUTPUT (writes to)
─────────────────                      ────────────────────
reviewed_signal_proposals  ──┐
replay_results             ──┼──► strategy_optimizer.js ──► strategy_optimizations
risk_decisions             ──┤                          ──► strategy_variants
confidence_calibration     ──┘                          ──► Telegram report
options_strategy_performance ─┘
```

### Module Map

| File | Role |
|------|------|
| `sl_tp_optimizer.js` | Analyzes SL/TP placement and RR ratios for forex strategies |
| `options_structure_optimizer.js` | Benchmarks options structure parameters vs known best practices |
| `threshold_optimizer.js` | Finds optimal risk score and confidence approval thresholds |
| `confidence_optimizer.js` | Detects AI over/under-confidence by band; generates prompt recommendations |
| `strategy_optimizer.js` | Coordinator — calls all sub-optimizers, returns unified report |
| `optimizer_writer.js` | Writes suggestions to `strategy_optimizations` and `strategy_variants` |
| `telegram_optimizer_alert.js` | Formats and sends optimization report to Telegram |
| `optimization_runner.js` | CLI entry point — parse args, run, write, alert |

---

## Run Commands

```bash
# Install dependencies
npm install

# Full analysis — all optimization types, write to Supabase, send Telegram
npm run analyze
# or: node optimization_runner.js --analyze

# Forex only — SL/TP placement + threshold analysis
npm run forex
# or: node optimization_runner.js --forex

# Options only — structure benchmarking + confidence calibration
npm run options
# or: node optimization_runner.js --options

# Threshold + confidence analysis only
npm run thresholds
# or: node optimization_runner.js --thresholds
```

### Environment Controls

```bash
# Disable Supabase writes (dry run)
WRITE_TO_SUPABASE=false node optimization_runner.js --analyze

# Disable Telegram alerts
SEND_TELEGRAM=false node optimization_runner.js --analyze
```

---

## How Optimization Works

The system is **data-driven and advisory only**. It does not change any live parameters.

### Forex SL/TP Analysis

1. Fetches all reviewed forex proposals with `entry_price`, `stop_loss`, `take_profit`
2. Computes per-strategy averages: SL distance, TP distance, RR ratio
3. Cross-references with `replay_results` to find which RR buckets produced the highest win rates
4. Suggests adjusted `suggested_sl_pct` and `suggested_tp_pct` as % of entry price
5. Assigns `improvement_score` (0–100) based on gap between current and optimal RR

### Options Structure Benchmarking

Compares actual performance (from `options_strategy_performance` and `replay_results`) against known-good parameter ranges:

| Strategy | Optimal Strike OTM | Optimal DTE | Target Premium |
|----------|--------------------|-------------|----------------|
| Covered Call | 2% | 30 | 2% |
| Cash-Secured Put | 3% | 30 | 2.5% |
| Iron Condor | 5% wing width | 45 | 3% credit |
| Credit Spread | 3% wide | 21 | 1.5% credit |
| Zebra | 70-delta | 90 | — |
| Wheel | 5% OTM | 30 | 2% |

### Threshold Optimization

- Buckets `risk_decisions` by risk score (10-point bands)
- Cross-references with `replay_results` outcomes
- Finds lowest risk score band with win rate ≥ 55%
- Suggests `approval_threshold` and `review_threshold` adjustments

### Confidence Calibration

- Reads `confidence_calibration` table (populated by performance tracker)
- Identifies bands where `calibration_gap` > 5% (AI predicts wrong win rate)
- Rates overall quality: `excellent` / `good` / `fair` / `poor`
- Generates human-readable prompt improvement recommendations

---

## Validation SQL

After running, verify results in Supabase:

```sql
-- Top optimization suggestions
SELECT
  strategy_id,
  optimization_type,
  parameter_name,
  original_value,
  suggested_value,
  improvement_score
FROM strategy_optimizations
ORDER BY improvement_score DESC
LIMIT 20;

-- Strategy variants by replay performance
SELECT
  strategy_id,
  variant_name,
  backtest_score,
  replay_score
FROM strategy_variants
ORDER BY replay_score DESC;
```

---

## Safety Rules

1. **Suggestions only** — the optimization lab never modifies live strategy parameters, approval thresholds, or any running system configuration.
2. **No auto-changes** — all suggestions are written to `strategy_optimizations` as records for human review. A human must deliberately implement any change.
3. **Human reviews all recommendations** — before adjusting any threshold, RR target, or options parameter, a human must verify the suggestion makes sense given current market conditions.
4. **Minimum sample requirements** — suggestions with fewer than the configured minimum samples (10 for forex, 5 for options) are flagged as provisional.
5. **No broker access** — this module has no broker API credentials and cannot place, modify, or cancel orders.

---

## Required Supabase Tables

These tables must exist before running (see `docs/` for SQL):

**Read from:**
- `reviewed_signal_proposals`
- `replay_results`
- `risk_decisions`
- `confidence_calibration`
- `options_strategy_performance`

**Write to:**
- `strategy_optimizations`
- `strategy_variants`
