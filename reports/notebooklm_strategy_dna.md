# NotebookLM Strategy DNA Extraction

## Scope
Trading notebooks: forex, options, crypto, stocks.

## Structured Strategy DNA Schema
- strategy_name
- category
- market_type
- entry_trigger
- confirmation
- invalidation
- stop_loss
- take_profit
- volatility_fit
- session_fit
- liquidity_fit
- fakeout_behavior
- risk_profile
- drawdown_profile
- lesson_learned
- confidence

## Current Status
- Strategy DNA primitives exist in `lib/strategy_intelligence.py` and adaptive trading intelligence modules.
- Direct, automated extraction from NotebookLM ingest payloads is partial and not fully wired.

## Completion Actions
1. Parse notebook summaries/insights into schema fields with null-safe defaults.
2. Tag each strategy DNA row with source notebook, source URLs, and sync timestamp.
3. Add confidence calibration from source quality + cross-notebook repetition.
4. Write to Supabase proposed state first; require approval before promotion.

## Promotion Logic
- Promote to Hall of Fame candidate only when:
  - confidence >= threshold,
  - risk and invalidation fields present,
  - contradiction risk low.

## Safety
- Keep all outputs as research intelligence, not live trading directives.
