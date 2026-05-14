# Telegram Summary Path Removal

Generated: 2026-05-14

## Removed / Disabled Paths
- Removed launch agents:
  - `com.nexus.opportunity-worker.plist`
  - `com.nexus.grant-worker.plist`
  - `com.nexus.research-orchestrator-transcript.plist`
  - `com.nexus.research-orchestrator-grants-browser.plist`
- Opportunity/grant brief sender functions now call policy and are denied by default.

## Architecture Outcome
- Autonomous summary fanout for opportunity/grant brief channels is disabled at both scheduler/launch and sender policy layers.
- Conversational Telegram route remains active through `telegram_bot.py` + `hermes_gate.send_direct_response`.

## Remaining Work
- Static audit still finds non-test direct Telegram senders outside `hermes_gate` wrappers; these should be migrated in a separate hardening pass.
