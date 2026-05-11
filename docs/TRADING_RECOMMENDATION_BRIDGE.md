# Trading Recommendation Bridge

Converts strong trading `research_artifacts` rows into first-class
`reviewed_signal_proposals` and companion `risk_decisions` rows.

Worker:

- `research_intelligence/trading_recommendation_bridge.py`

Usage:

```bash
python3 -m research_intelligence.trading_recommendation_bridge --limit 3
```

What it does:

1. Reads recent `research_artifacts` where `topic = trading`
2. Filters out noisy or weak artifacts
3. Writes deterministic `reviewed_signal_proposals` rows
   - includes raw `strategy_id`
   - infers normalized `strategy_type` when the artifact title/context is specific enough
4. Writes deterministic companion `risk_decisions` rows
5. Makes those bridged proposals available to:
   - `recommendation_packet_engine`
   - `approval_handoff_worker`
   - `trading_task_executor`
   - `paper_trade_runs`

Notes:

- The bridge is intentionally conservative and does not invent price levels.
- Asset type is mapped to `forex` unless the artifact clearly looks options-oriented.
- `strategy_type` is best-effort and falls back to null when the source title is too generic.
- The worker is idempotent because proposal and risk row IDs are deterministic per artifact.
