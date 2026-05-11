# nexus-strategy-lab

Mac Mini intelligence workers for the Nexus AI Strategy Lab.

## Machine Boundary

| Machine | Role |
|---|---|
| **Mac Mini** (this) | Strategy ingestion, scoring, Hermes review, demo trading workers |
| **Windows** | Admin portal (`/admin/hermes`, `/admin/trading-lab`), Netlify deploy |
| **Oracle VM** | Public API (`api.goclearonline.cc`), TradingView webhook receiver |
| **Supabase** | Shared durable state — all three machines read/write here |

**Never deploy Mac Mini workers to Oracle. Never SSH to Oracle from here.**  
See `~/nexus-ai/docs/MAC_SCOPE_BOUNDARY.md` for full rules.

## Structure

```
nexus-strategy-lab/
├── config/
│   └── settings.py          # Config loader — all workers import from here
├── db/
│   ├── supabase_client.py   # PostgREST wrapper (select/insert/upsert/update)
│   └── ai_client.py         # Hermes → OpenClaw fallback gateway client
├── ingestion/               # Prompt 2: strategy scraping + transcript storage
├── scoring/                 # Prompt 2: rule-based + AI scoring engine
├── review/                  # Prompt 3: Hermes review queue poller
├── trading/                 # Prompt 4: modular demo trading engine
├── backtest/                # Replay signals through risk manager
├── tests/
│   └── test_foundation.py   # Foundation smoke test (run this first)
└── logs/                    # Worker log output (gitignored)
```

## Setup

```bash
# Uses ~/nexus-ai/.env automatically — no separate setup needed
cd ~/nexus-ai/nexus-strategy-lab
python3 -m tests.test_foundation     # should show 5/5 passed
```

## Key Tables (Supabase)

| Group | Tables |
|---|---|
| Strategy pipeline | `strategy_sources`, `strategy_transcripts`, `strategy_candidates`, `strategy_scores`, `strategy_versions` |
| Backtesting | `strategy_backtest_runs`, `strategy_backtest_metrics`, `strategy_validation_reports` |
| Demo trading | `demo_accounts`, `paper_trading_journal_entries`, `paper_trading_outcomes` |
| Trade events | `demo_trade_runs`, `demo_trade_events`, `demo_trade_metrics` |
| Hermes reviews | `hermes_review_queue`, `hermes_reviews`, `trading_lessons`, `founder_trading_summaries` |

## AI Gateways

Workers call `db.ai_client.complete(prompt)` — it auto-selects the available gateway:
1. **Hermes** `localhost:8642` (fast, local)
2. **OpenClaw** `localhost:18789` (fallback, routes to ChatGPT/Codex)

Override with `AI_PROVIDER=hermes|openclaw|auto` in `.env`.

## Safety

`DRY_RUN=true` in `.env` — all trade execution is simulated until the 24h demo monitoring pass is complete.
