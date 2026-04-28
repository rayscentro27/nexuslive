# Skill: Nexus — Business Context & Vision

## What Nexus Is
Nexus is Ray Davis's autonomous AI business operating system. It runs 24/7 on a
Mac Mini and Oracle ARM VPS, managing a fleet of AI workers that handle trading,
client operations, research, grants, and business development without manual input.

## Operator
- Name: Ray Davis
- Email: goclearonline@gmail.com
- Telegram: chat ID 1288928049
- All critical alerts go to Telegram via @NexusHermbot

## The Single Brain Architecture
Nexus implements the "Single Brain" / "World Intelligence" concept:
- **Central data layer**: Supabase (all events, clients, tasks, strategies)
- **Event bus**: `system_events` table — every action creates an event
- **Agent dispatch**: `autonomy_worker` polls every 30s, routes events to agents
- **Query interface**: Hermes gateway on :8642 — any agent or operator can query
- **Knowledge base**: `~/nexus-ai/research-engine/strategies/` + Supabase
- **Self-healing**: `ops-control-worker` restarts any failed automatic worker

## Agent Fleet
| Agent | Purpose |
|---|---|
| Hermes | AI gateway, Telegram bot, trade reviewer, operator interface |
| autonomy_worker | Event dispatcher — routes system_events to specialized agents |
| credit agent | Evaluates client creditworthiness |
| funding agent | Identifies funding/grant opportunities for clients |
| capital agent | Capital allocation recommendations |
| communication agent | Drafts client communications |
| business agent | Business strategy and opportunity scoring |
| trading engine | Signal review, Oanda execution, position management |
| research orchestrator | YouTube → transcript → strategy extraction |
| email pipeline | Inbound email processing, YouTube URL ingestion |

## Products
- **goclearonline.cc** — Client portal (React/Vite, Netlify)
  - Stripe payments (live key)
  - Supabase auth
  - Signup → AI agent onboarding pipeline

## Infrastructure
| Component | Location |
|---|---|
| Main workstation | Mac Mini (local) |
| Database | Supabase cloud (ygqglfbhxiumqdisauar) |
| Remote LLM | Oracle ARM at 161.153.40.41 (qwen2.5:14b) |
| Website hosting | Netlify |
| Broker | Oanda practice (api-fxpractice.oanda.com) |
| Public webhook | Cloudflare Tunnel → localhost:5000 |
| Domain | goclearonline.cc (Cloudflare DNS) |

## Growth Flywheel
Month 1: Workers running, basic automation.
Month 2: Patterns emerging, agents reusing research.
Month 3: Compounding — strategies inform trading, trading profits fund operations,
research improves agent decisions, better agents attract more clients.

## Key Files
- `~/nexus-ai/.env` — all credentials
- `~/nexus-ai/trading-engine/trading_config.json` — trading parameters
- `~/nexus-ai/supabase/migrations/` — database schema history
- `~/.hermes/SOUL.md` — Hermes identity and command mappings
- `~/nexus-ai/skills/` — this skills directory
