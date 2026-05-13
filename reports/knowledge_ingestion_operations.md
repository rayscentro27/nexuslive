# Knowledge Ingestion Operations

- Mode: continuous operational intelligence ingestion
- Safety posture verified: `NEXUS_DRY_RUN=true`, `LIVE_TRADING=false`, `TRADING_LIVE_EXECUTION_ENABLED=false`, `NEXUS_AUTO_TRADING=false`
- Added admin ingestion operations snapshot in AI OPS status API and config panel
- Added queue/status/source summaries, proposed/approved/rejected counts, transcript availability, failure count, and latest sources preview
- Added Hermes retrieval paths for pending review, ingestion status, trending concepts, top quality sources, and active opportunity validation

## Notes

- Ingestion remains review-first (no auto-approval)
- URL normalization and duplicate controls are enabled for ingestion quality
