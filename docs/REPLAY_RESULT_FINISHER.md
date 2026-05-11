# Replay Result Finisher

Consumes running `paper_trade_runs`, writes deterministic `replay_results`,
and marks the runs `finished`.

Workers:

- `research_intelligence/paper_trade_run_cleanup.py`
- `research_intelligence/replay_result_finisher.py`

Usage:

```bash
python3 -m research_intelligence.paper_trade_run_cleanup --limit 100
python3 -m research_intelligence.replay_result_finisher --limit 20
```

What they do:

1. `paper_trade_run_cleanup` keeps one canonical running row per proposal/signal/symbol/strategy combination
2. marks obvious duplicates `error`
3. `replay_result_finisher` resolves running rows into deterministic replay outcomes using the replay-lab rules:
   - `forex_static_rr`: static R:R from `entry_price`, `stop_loss`, and `take_profit`
   - `options_historical_profile`: normalized `strategy_type` when present, otherwise inferred from `strategy_id`, blended with `ai_confidence`
4. inserts `replay_results`
5. marks the source run `finished`
