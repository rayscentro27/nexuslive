# Deprecated Worker Cleanup

Generated: 2026-05-14

## Removed
- `~/Library/LaunchAgents/com.nexus.opportunity-worker.plist`
- `~/Library/LaunchAgents/com.nexus.grant-worker.plist`
- `~/Library/LaunchAgents/com.nexus.research-orchestrator-transcript.plist`
- `~/Library/LaunchAgents/com.nexus.research-orchestrator-grants-browser.plist`

## Hardened
- `workflows/ai_workforce/opportunity_worker/opportunity_brief_generator.js` now policy-gated (denied event type).
- `workflows/ai_workforce/grant_worker/grant_brief_generator.js` now policy-gated (denied event type).
- `lib/hermes_gate.py` tightened allow/deny handling.

## Preserved
- Hermes conversational Telegram behavior.
- Supabase ingestion paths.
- Workforce/intelligence UI updates already in progress.
- Critical alert path (policy-controlled).
