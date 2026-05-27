# Nexus Vibe-Trading — Cost Control Policy

## Hard Rules

| Rule | Status |
|---|---|
| Free data only (yfinance, akshare, simulated) | REQUIRED |
| No paid market data APIs | BLOCKED by default |
| No paid LLM APIs unless manually approved | BLOCKED by default |
| No broker APIs | PERMANENTLY BLOCKED |
| No cloud GPU | NOT USED |
| No constant agent swarms | PROHIBITED |
| No autonomous scheduled runs without approval | PROHIBITED |

## Preferred Data Sources (Free)

- **yfinance** — Yahoo Finance historical OHLCV, included in vibe-trading-ai
- **akshare** — Chinese and international free market data, included in vibe-trading-ai
- **Simulated/synthetic** — For unit testing strategies without any API calls
- **DuckDB** — Local query engine, no external cost

## LLM Cost Tiers

| Provider | Use | Cost |
|---|---|---|
| Hermes → Ollama (Oracle ARM) | Summaries, light analysis | $0/run |
| OpenRouter deepseek-chat | Research prompts | ~$0.001/run |
| OpenRouter deepseek-r1 | Deep strategy analysis | ~$0.01/run |
| openai/gpt-4o | Premium only, manual approval | ~$0.05/run |

**Default for Vibe-Trading tasks: deepseek-chat or local Ollama.**

## When Paid LLM Is Required

Vibe-Trading AI internally calls an LLM to interpret results and generate summaries.
If `OPENAI_API_KEY` is not set, it will error or fall back to a limited mode.

Options (in preference order):
1. Set `OPENAI_BASE_URL=http://localhost:8642/v1` to route through Hermes → Ollama (free)
2. Set `OPENAI_BASE_URL=https://openrouter.ai/api/v1` with `OPENAI_API_KEY=$OPENROUTER_API_KEY`
3. Use `NEXUS_ALLOW_PAID_LLM=true` explicitly for a single run (with human approval)

## Run Frequency Policy

- **On-demand only** — no scheduled/cron backtests without explicit approval
- **Max 10 runs/day** from Hermes automation
- **Improvement loop** — max 5 iterations per strategy before human review required
- **Batch runs** — require Discord CEO Command approval before starting

## No-Cost Checklist Before Every Run

- [ ] `NEXUS_ALLOW_PAID_MARKET_DATA=false` confirmed
- [ ] `NEXUS_ALLOW_PAID_LLM=false` OR local/OpenRouter approved
- [ ] `VIBE_TRADING_ENABLE_SHELL_TOOLS=0` confirmed
- [ ] Task type in allowlist
- [ ] No broker API keys in environment
