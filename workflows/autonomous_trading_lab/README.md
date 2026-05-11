# Nexus Autonomous Trading Lab

> **NO LIVE TRADING. NO AUTO EXECUTION. NO BROKER ORDERS.**
> This lab produces AI analysis and human-approval alerts only.
> All trades are executed manually by a human in Webull or OANDA.

---

## Architecture

```
Supabase (tv_normalized_signals, status='enriched')
    │
    ▼
lab_poll.js          ← polls enriched signals, detects asset_type (forex | options)
    │
    ▼
lab_context.js       ← market snapshot + research + strategy + options Greeks context
    │
    ▼
analyst_runner.js    ← OpenAI-compatible AI analyst (OpenRouter/OpenAI/custom gateway)
    │
    ▼
proposal_writer.js   ← writes reviewed_signal_proposals, marks signal reviewed
    │
    ▼
telegram_proposal_alert.js  ← sends AI proposal to Telegram (all statuses)
    │
    ▼ (if not AI-blocked)
risk_engine.js       ← 100-penalty scoring system → approved / manual_review / blocked
    │
    ▼
risk_writer.js       ← writes risk_decisions table (with risk_flags JSONB)
    │
    ▼
telegram_risk_alert.js   ← sends risk decision to Telegram
    │
    ▼ (if approved or manual_review)
approval_queue.js    ← enqueues to approval_queue table (approval_status='pending')
    │
    ▼
telegram_approval_alert.js  ← sends APPROVAL REQUIRED alert to Telegram
    │
    ▼
HUMAN REVIEW → Manual execution in Webull / OANDA
```

---

## Supabase Tables

| Table | Purpose |
|---|---|
| `tv_normalized_signals` | Source signals from TradingView via Oracle API |
| `reviewed_signal_proposals` | AI analyst proposals (forex + options) |
| `risk_decisions` | Risk engine decisions (100-penalty score, flags) |
| `approval_queue` | Human review queue (approval_status: pending/approved/rejected) |

Apply SQL via **Supabase Dashboard → SQL Editor**:
```
~/nexus-ai/docs/reviewed_signal_proposals.sql
~/nexus-ai/docs/risk_decisions.sql
~/nexus-ai/docs/approval_queue.sql
```

---

## Signal Types

### FOREX Signals
- Entry price, stop loss, take profit
- R:R ratio computed from price levels
- Strategies: breakout, trend_follow, mean_reversion, momentum, etc.
- Executed manually in OANDA if approved

### OPTIONS Signals
- Detected by `strategy_id` (e.g., `covered_call`, `iron_condor`, `ZEBRA`)
- No entry/SL/TP price levels
- AI provides: underlying, expiration guidance, strike guidance, premium estimate, Greeks notes
- Executed manually in Webull if approved

---

## Risk Engine (100-Penalty System)

Starts at **100** and subtracts penalties per flag:

| Flag | Penalty | Trigger |
|---|---|---|
| `poor_rr` | -30 | R:R < 2.0 (forex) |
| `missing_sl` | -30 | No stop loss |
| `low_confidence` | -25 | AI confidence < 0.6 |
| `conflict` | -20 | AI confidence < 0.4 |
| `unknown_strategy` | -20 | Strategy not in library |
| `high_spread` | -15 | Spread > 0.0003 |
| `duplicate_signal` | -15 | Same symbol+side already in approval_queue |
| `low_rr_options` | -15 | Options signal without premium estimate |

**Decision thresholds:**
- Score ≥ 70 → `approved`
- Score 40–69 → `manual_review`
- Score < 40 → `blocked`

---

## Environment Variables

All sourced from `~/nexus-ai/.env` (symlinked as `.env`):

```env
SUPABASE_URL=...
SUPABASE_KEY=...                # anon key (read access)
SUPABASE_SERVICE_KEY=...        # service_role key (write access)
NEXUS_LLM_BASE_URL=https://openrouter.ai/api/v1
NEXUS_LLM_API_KEY=...
NEXUS_LLM_MODEL=meta-llama/llama-3.3-70b-instruct
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
POLL_INTERVAL_SECONDS=60        # optional, default 60
```

---

## Run Commands

```bash
cd ~/nexus-ai/workflows/autonomous_trading_lab

# Single batch (all pending enriched signals)
npm run once
# or: node lab_runner.js --once

# Limited batch (up to N signals)
node lab_runner.js --limit 3

# Continuous polling
npm run poll
# or: node lab_runner.js --poll

# Status report
npm run status
# or: node lab_runner.js --status
```

---

## Test Commands

```bash
# 1. Check for enriched signals
node -e "import('./lab_poll.js').then(m=>m.pollEnrichedSignals()).then(s=>console.log(s.length,'signals'))"

# 2. Check approval queue
node -e "import('./approval_queue.js').then(m=>m.fetchPendingApprovals()).then(q=>console.log(q.length,'pending'))"

# 3. Run analyst status
node lab_runner.js --status
```

---

## Validation SQL

Run in Supabase Dashboard → SQL Editor to validate data flow:

```sql
-- Recent AI proposals
SELECT symbol, side, asset_type, status, ai_confidence, created_at
FROM reviewed_signal_proposals
ORDER BY created_at DESC LIMIT 10;

-- Recent risk decisions
SELECT symbol, side, asset_type, decision, risk_score, risk_flags, created_at
FROM risk_decisions
ORDER BY created_at DESC LIMIT 10;

-- Pending approvals
SELECT symbol, side, asset_type, decision, risk_score, approval_status, created_at
FROM approval_queue
WHERE approval_status = 'pending'
ORDER BY created_at DESC;

-- Full pipeline trace (replace with actual trace_id)
SELECT
    s.symbol, s.side, s.status AS signal_status,
    p.status AS proposal_status, p.ai_confidence,
    r.decision, r.risk_score, r.risk_flags,
    q.approval_status
FROM tv_normalized_signals s
LEFT JOIN reviewed_signal_proposals p ON p.signal_id = s.id
LEFT JOIN risk_decisions r ON r.signal_id = s.id
LEFT JOIN approval_queue q ON q.signal_id = s.id
WHERE s.trace_id = '<your-trace-id>'
LIMIT 1;
```

---

## Files

| File | Purpose |
|---|---|
| `lab_runner.js` | Main orchestrator — wires all modules |
| `lab_poll.js` | Poll enriched signals, detect asset_type |
| `lab_context.js` | Build context pack (snapshot + research + options Greeks) |
| `analyst_prompt.md` | System prompt for the AI analyst |
| `analyst_runner.js` | Call the configured AI gateway, parse + validate proposal |
| `risk_prompt.md` | Notes for risk engine logic |
| `risk_engine.js` | 100-penalty scoring, returns decision |
| `risk_runner.js` | Thin wrapper around risk_engine |
| `proposal_writer.js` | Write to reviewed_signal_proposals |
| `risk_writer.js` | Write to risk_decisions |
| `approval_queue.js` | Enqueue / fetch / update approval_queue |
| `approval_runner.js` | Drain pending approvals, send alerts |
| `telegram_proposal_alert.js` | AI proposal Telegram alert |
| `telegram_risk_alert.js` | Risk decision Telegram alert |
| `telegram_approval_alert.js` | Approval required Telegram alert |
| `package.json` | ESM config, dotenv dependency |
| `.env` | Symlink → `../../.env` |

---

*Nexus Autonomous Trading Lab — Mac Mini AI Ops scope only. Oracle VM handles signal intake. Windows handles Oracle VM deployment.*
