# Autonomous Safe Intelligence Flow

## Status
- Phase C preserved and reinforced with read-only centralized visibility and policy-safe operation.

## Current Safe Flow
- Allowed unattended behavior:
  - playlist and NotebookLM ingestion paths
  - transcript queue accumulation
  - semantic extraction and retrieval telemetry
  - proposed knowledge generation and review queues
  - dashboard/workforce state updates
- Disallowed behavior remains blocked:
  - autonomous Telegram summary fanout
  - autonomous financial execution
  - auto-approval of all knowledge

## Controls Preserved
- `NEXUS_DRY_RUN=true`
- `LIVE_TRADING=false`
- `TRADING_LIVE_EXECUTION_ENABLED=false`
- `NEXUS_AUTO_TRADING=false`
- Telegram default-deny policy and hermes-gated send path retained.

## Outcome
- Nexus can continue learning and surfacing operations during travel without reintroducing outbound spam or execution risk.
