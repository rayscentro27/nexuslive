# Nexus Vibe-Trading Integration

**Status:** Phase 1 — Local install, education-only, paper-trading only.  
**Branch:** `feature/vibe-trading-hermes-adapter`  
**Not client-facing. Not production.**

---

## What This Is

An isolated wrapper around [HKUDS Vibe-Trading](https://github.com/HKUDS/Vibe-Trading)
that allows Hermes to run paper-trading backtests and market research tasks safely,
with no live trading, no broker connections, and no paid API requirements.

---

## Directory Layout

```
integrations/vibe_trading/
  .venv/                     Python venv (gitignored)
  workspace/                 Vibe-Trading working directory (gitignored)
  reports/                   JSON backtest results (gitignored)
  sample_outputs/            Example outputs for review
  .env.example               Safe env template (commit this)
  .env                       Local secrets (NEVER commit)
  vibe_trading_adapter.py    Nexus wrapper — the ONLY safe entry point
  test_forex_backtest.py     Phase 6 EUR/USD RSI(14) backtest
  install_vibe_trading.sh    Install vibe-trading-ai in .venv
  test_vibe_cli.sh           Smoke-test CLI
  test_vibe_mcp.sh           Check MCP server + print config block
  HERMES_INTEGRATION_PLAN.md Future Hermes ↔ Supabase workflow
  COST_CONTROL.md            Cost policy: free-first, no broker APIs
  README.md                  This file
```

---

## Quick Start

```bash
# 1. Install
bash integrations/vibe_trading/install_vibe_trading.sh

# 2. Verify CLI
bash integrations/vibe_trading/test_vibe_cli.sh

# 3. Check MCP
bash integrations/vibe_trading/test_vibe_mcp.sh

# 4. Run first forex backtest
source integrations/vibe_trading/.venv/bin/activate
python integrations/vibe_trading/test_forex_backtest.py

# 5. Call from Hermes/Python
from integrations.vibe_trading.vibe_trading_adapter import run_vibe_trading_task
result = run_vibe_trading_task(
    "Backtest RSI(14) mean-reversion on EURUSD — education only.",
    task_type="backtest"
)
print(result["report_path"])
```

---

## Safety Contract

| Control | Setting |
|---|---|
| Live trading | DISABLED |
| Broker connection | BLOCKED |
| Shell tools | `VIBE_TRADING_ENABLE_SHELL_TOOLS=0` |
| Paid market data | BLOCKED by default |
| Paid LLM | BLOCKED by default |
| Client portal access | NOT WIRED |
| Task allowlist | backtest, market_research, strategy_compare, forex_research |
| Blocked keywords | live_trade, place_order, execute_trade, broker_connect, real_money, etc. |

Every result includes an educational disclaimer and is saved to `reports/` as JSON.

---

## Allowed Task Types

```python
ALLOWED_TASK_TYPES = {
    "backtest",
    "market_research",
    "strategy_compare",
    "forex_research",
}
```

---

## LLM Configuration

Vibe-Trading requires an OpenAI-compatible endpoint internally.
Point it at Hermes/Ollama for zero cost:

```bash
export OPENAI_BASE_URL=http://localhost:8642/v1
export OPENAI_API_KEY=<hermes-api-key>
```

Or use OpenRouter (low cost):
```bash
export OPENAI_BASE_URL=https://openrouter.ai/api/v1
export OPENAI_API_KEY=$OPENROUTER_API_KEY
```

---

## What Is NOT Done Yet

- [ ] Supabase `trading_research_runs` table
- [ ] Hermes auto-call on YouTube trading video
- [ ] Improvement loop (baseline → analyze → retest)
- [ ] OpenClaw MCP config applied
- [ ] Client portal integration
