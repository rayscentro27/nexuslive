# Final Telegram Sender Migration

Generated: 2026-05-14

## Migration rule applied
- Removed direct Telegram API posts from failing Python modules.
- Routed remaining critical notifications through `lib/hermes_gate.py`.
- Routed summary-style notifications through policy checks that default-deny blocked event types.

## Summary paths hard-denied
- `opportunity_summary`, `grant_summary`, `research_summary`, `ingestion_summary`, `queue_summary`, `worker_summary`, `scheduler_summary`, `topic_brief`, `run_summary`, `auto_digest`, `full_report`, `opportunities_detected`.

## Result
- No non-test Python modules bypass `hermes_gate` according to static policy test.
- `scripts/test_telegram_policy.py` now passes 31/31.
