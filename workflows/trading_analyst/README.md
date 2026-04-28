# Nexus AI Trading Analyst

**Analysis only. No live trading. No broker execution.**

Reads enriched trade signals from Supabase, asks the configured OpenAI-compatible model gateway to review them against research context, generates structured proposals, stores them in Supabase, and sends Telegram alerts.

---

## Workflow

```
Supabase tv_normalized_signals (status = enriched)
        │
        ▼
analyst_poll.js          — fetch up to 5 unreviewed signals
        │
        ▼
analyst_context.js       — build context pack:
                             • latest market price snapshot (OANDA)
                             • top 3 matching research summaries
                             • strategy context string
        │
        ▼
analyst_runner.js        — call the configured AI gateway / chat completions endpoint
  (uses analyst_prompt.md as system prompt)
        │
        ▼
validate + enforce hard blocks (R:R < 1.5 → auto-blocked)
        │
        ▼
supabase_proposal_writer.js — write to reviewed_signal_proposals
                              mark signal as reviewed
        │
        ▼
telegram_proposal_alert.js  — send Telegram alert
```

---

## Required Environment Variables

These are already in `~/nexus-ai/.env`. The workflow loads them automatically.

| Variable | Description |
|----------|-------------|
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_ANON_KEY` | Anon key — read-only queries |
| `SUPABASE_SERVICE_ROLE_KEY` | Service role — write proposals, update signals |
| `NEXUS_LLM_BASE_URL` | Preferred. Example: `https://openrouter.ai/api/v1` |
| `NEXUS_LLM_API_KEY` | Preferred gateway API key |
| `NEXUS_LLM_MODEL` | Preferred model name |
| `OPENROUTER_BASE_URL` | Fallback supported |
| `OPENROUTER_API_KEY` | Fallback supported |
| `TELEGRAM_BOT_TOKEN` | Bot token for alerts |
| `TELEGRAM_CHAT_ID` | Chat ID to receive alerts |
| `POLL_INTERVAL_SECONDS` | Poll mode interval (default: 60) |

---

## Supabase Setup

Apply the SQL migration before first run:

```bash
# Paste contents of ~/nexus-ai/docs/reviewed_signal_proposals.sql
# into Supabase Dashboard → SQL Editor → Run
```

Verify:
```sql
SELECT id, symbol, side, status, created_at
FROM reviewed_signal_proposals
ORDER BY created_at DESC
LIMIT 10;
```

---

## Running

### One-shot (process up to 5 queued signals then exit)

```bash
cd ~/nexus-ai/workflows/trading_analyst
node analyst_runner.js --once
```

### Poll mode (continuous, runs every POLL_INTERVAL_SECONDS)

```bash
node analyst_runner.js --poll
```

### From workspace root (with env loaded)

```bash
cd ~/nexus-ai
node workflows/trading_analyst/analyst_runner.js --once
```

---

## Test Command

Run with a real enriched signal from Supabase:

```bash
cd ~/nexus-ai/workflows/trading_analyst

# First confirm there are enriched signals:
node -e "
import('./analyst_poll.js').then(m =>
  m.pollEnrichedSignals().then(s => console.log(JSON.stringify(s, null, 2)))
)
"

# Then run the analyst:
node analyst_runner.js --once
```

---

## Checking Results in Supabase

```sql
-- Latest proposals
SELECT symbol, side, status, ai_confidence, recommendation, created_at
FROM reviewed_signal_proposals
ORDER BY created_at DESC
LIMIT 10;

-- Full proposal detail
SELECT *
FROM reviewed_signal_proposals
WHERE symbol = 'EUR_USD'
ORDER BY created_at DESC
LIMIT 5;

-- Trace a signal end-to-end
SELECT
  'signal'    AS tbl, id, status, trace_id, created_at FROM tv_normalized_signals   WHERE trace_id = '<your-trace-id>'
UNION ALL
SELECT
  'proposal'  AS tbl, id::text, status, trace_id, created_at FROM reviewed_signal_proposals WHERE trace_id = '<your-trace-id>'
ORDER BY created_at;
```

---

## Proposal Statuses

| Status | Meaning |
|--------|---------|
| `proposed` | Passed all AI and hard-block checks. Ready for risk office review. |
| `blocked` | Failed R:R check, missing SL/TP, or AI assessed as invalid. |
| `needs_review` | Ambiguous signal or missing data. Needs human review. |

---

## Hard Block Rules (enforced in code, not just AI)

- R:R ratio below 1:1.5 → auto-blocked
- Stop loss = 0 or missing → auto-blocked
- Take profit = 0 or missing → auto-blocked
- Entry price = 0 or missing → auto-blocked

---

## Architecture Notes

- This workflow runs **on the Mac Mini only**
- An OpenAI-compatible model gateway must be reachable
- No broker access, no OANDA orders, no live execution
- All writes use `SUPABASE_SERVICE_ROLE_KEY` to bypass RLS
- Poll mode can be added to launchd — see `scripts/install_launchd_service.sh` for pattern
