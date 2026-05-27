# Hermes ↔ Vibe-Trading Integration Plan

## Architecture

```
Hermes (executive AI)
  └── vibe_trading_adapter.py   ← ONLY entry point Hermes may call
        └── vibe-trading CLI    ← subprocess, isolated venv
              └── Reports/JSON  ← saved to integrations/vibe_trading/reports/
                    └── Supabase (future)
```

**Hermes should NEVER call vibe-trading raw CLI directly.**
**All calls go through `vibe_trading_adapter.run_vibe_trading_task()`.**

---

## Hermes Workflow

### Before running any backtest
1. Search Supabase `trading_strategy_tests` for existing results on same strategy/symbol.
2. If result < 7 days old and parameters match: return cached result, skip API call.
3. If no cached result: run adapter.

### Improvement loop
```
baseline_strategy
  → analyze_weakness (drawdown, low win rate, overfit signals)
  → change 1-2 variables (e.g. RSI period, entry threshold)
  → retest
  → compare_metrics (Sharpe, drawdown, win rate, trade count)
  → reject_overfitting (if in-sample vs out-of-sample gap > 15%)
  → save_approved_candidate to Supabase
```

### Cost check before every run
- If `NEXUS_ALLOW_PAID_LLM=false`: use local/OpenRouter deepseek fallback
- If market data requires paid API: abort, log as `cost_blocked`, alert Hermes CEO channel
- If `NEXUS_REQUIRE_HUMAN_APPROVAL_FOR_PAID_TOOLS=true`: post approval request to Discord CEO Command

---

## Future Supabase Tables

| Table | Purpose |
|---|---|
| `trading_research_runs` | Every adapter call: prompt, result, cost, timestamp |
| `trading_strategy_tests` | Backtest results: symbol, strategy, metrics |
| `trading_strategy_versions` | Versioned strategy parameter sets |
| `trading_strategy_metrics` | Sharpe, drawdown, win rate, trade count per version |
| `trading_video_sources` | YouTube transcript → strategy extraction pipeline |
| `trading_strategy_rules` | Extracted testable rules from video intelligence |
| `trading_hermes_recommendations` | Hermes synthesis: approved strategies, rejected overfits |

---

## YouTube → Backtest Workflow

```
1. YouTube intelligence worker identifies trading video
2. transcript extracted + stored in trading_video_sources
3. Hermes extracts testable rules (entry, exit, stop, timeframe, instrument)
4. Hermes rejects vague rules ("follow the trend", "trust your gut")
5. Hermes calls vibe_trading_adapter with structured backtest prompt
6. Result saved to trading_strategy_tests
7. Hermes posts educational verdict to Discord CEO Command
8. Verdict: VALIDATED / REJECTED_OVERFIT / INSUFFICIENT_DATA
```

---

## Safety Rules for Hermes

- `task_type` MUST be one of: `backtest`, `market_research`, `strategy_compare`, `forex_research`
- Never pass user-facing text directly to the adapter without sanitization
- Never enable `VIBE_TRADING_ENABLE_SHELL_TOOLS=1`
- Never run with `NEXUS_DRY_RUN=false` for any live-execution pathway
- Post every result to Discord Ops channel with safety_mode confirmation
- Require explicit `NEXUS_ALLOW_PAID_LLM=true` before using paid LLM providers
