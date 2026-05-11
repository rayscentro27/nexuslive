# Mac Mini — Phases 3/4/5 Runbook
## Performance Lab · Replay Lab · Optimization Lab

> **RESEARCH ONLY — No live trading. No broker execution. No order placement.**

---

## Required Environment Variables

All phases read from `~/nexus-ai/.env`. Each lab directory has a symlink `.env → ../../.env`.

| Variable | Required By | Purpose |
|---|---|---|
| `SUPABASE_URL` | All | Supabase project URL |
| `SUPABASE_KEY` | All | Anon key (read access) |
| `SUPABASE_SERVICE_ROLE_KEY` | All | Service role key (write access) |
| `TELEGRAM_BOT_TOKEN` | All | Telegram bot token |
| `TELEGRAM_CHAT_ID` | All | Target chat ID |
| `OPENCLAW_URL` | Lab runner | OpenClaw gateway URL (default: http://localhost:18789) |
| `OPENCLAW_AUTH_TOKEN` | Lab runner | OpenClaw auth token |
| `POLL_INTERVAL_SECONDS` | Lab runner | Poll interval (default: 60) |

---

## Phase 3 — Performance Lab

**Directory:** `~/nexus-ai/workflows/performance_lab/`

### Run Once — Rank Strategies
```bash
cd ~/nexus-ai/workflows/performance_lab
node performance_runner.js --rank
```
- Computes forex + options strategy rankings
- Computes analyst and risk office scorecards
- Sends Telegram performance summary

### Run Once — Generate Scorecards
```bash
node performance_runner.js --scorecards
```
- Upserts all agent scorecards to Supabase
- Sends system alert to Telegram

### Key Mode Variations
| Command | Description |
|---|---|
| `--rank` | Strategy rankings + analyst/risk scorecards |
| `--scorecards` | Agent scorecard upsert only |

### Validation SQL
```sql
-- Check strategy rankings
SELECT * FROM public.strategy_performance ORDER BY win_rate DESC LIMIT 10;

-- Check agent scorecards
SELECT agent_name, metric_type, metric_value, period
FROM public.agent_scorecards
ORDER BY agent_name, metric_type;

-- Check proposal outcomes
SELECT outcome_status, count(*) FROM public.proposal_outcomes GROUP BY 1;
```

### Verify Telegram
Run `--rank` and check your Telegram chat for a performance summary message.

---

## Phase 4 — Replay Lab

**Directory:** `~/nexus-ai/workflows/replay_lab/`

### Run Once — Replay All Pending
```bash
cd ~/nexus-ai/workflows/replay_lab
node replay_runner.js --once
```
- Polls reviewed_signal_proposals with status `proposed` or `needs_review`
- Runs static R:R simulation for forex, historical profile for options
- Writes results to paper_trade_runs + replay_results
- Sends Telegram replay summary

### Run Calibration
```bash
node replay_runner.js --calibrate
```
- Analyzes confidence calibration bands
- Upserts calibration data to confidence_calibration table
- Reports over/underconfidence by band

### Key Mode Variations
| Command | Description |
|---|---|
| `--once` | Replay all pending proposals |
| `--limit N` | Replay up to N proposals |
| `--calibrate` | Calibration analysis only |

### Validation SQL
```sql
-- Check paper trade runs
SELECT replay_mode, status, count(*)
FROM public.paper_trade_runs
GROUP BY 1, 2;

-- Check replay results
SELECT replay_outcome, count(*), avg(pnl_r)
FROM public.replay_results
GROUP BY 1;

-- Check calibration
SELECT confidence_band, actual_win_rate, expected_win_rate, calibration_gap
FROM public.confidence_calibration
ORDER BY confidence_band;
```

---

## Phase 5 — Optimization Lab

**Directory:** `~/nexus-ai/workflows/optimization_lab/`

### Run Full Analysis
```bash
cd ~/nexus-ai/workflows/optimization_lab
node optimization_runner.js --analyze
```
- Analyzes forex SL/TP ratios
- Analyzes options structure
- Reviews risk thresholds
- Reviews confidence calibration
- Writes top suggestion to strategy_optimizations
- Sends Telegram optimization report

### Key Mode Variations
| Command | Description |
|---|---|
| `--analyze` | Full optimization analysis |
| `--forex` | Forex SL/TP analysis only |
| `--options` | Options structure analysis only |
| `--thresholds` | Risk threshold review only |

### Validation SQL
```sql
-- Check optimization suggestions
SELECT strategy_id, optimization_type, parameter_name,
       original_value, suggested_value, improvement_score
FROM public.strategy_optimizations
ORDER BY improvement_score DESC;

-- Check strategy variants (if populated)
SELECT * FROM public.strategy_variants LIMIT 10;
```

---

## Running All Three Phases in Sequence
```bash
cd ~/nexus-ai/workflows/performance_lab && node performance_runner.js --rank
cd ~/nexus-ai/workflows/replay_lab && node replay_runner.js --once
cd ~/nexus-ai/workflows/replay_lab && node replay_runner.js --calibrate
cd ~/nexus-ai/workflows/optimization_lab && node optimization_runner.js --analyze
```

---

## Autonomous Trading Lab (Phase 1/2) — Poll Mode
```bash
# Check if running
tmux ls | grep nexus-lab

# View logs
tail -f ~/nexus-ai/logs/lab.log

# Restart poll if needed
tmux kill-session -t nexus-lab
tmux new-session -d -s nexus-lab
tmux send-keys -t nexus-lab "cd ~/nexus-ai/workflows/autonomous_trading_lab && node lab_runner.js --poll 2>&1 | tee ~/nexus-ai/logs/lab.log" Enter
```
