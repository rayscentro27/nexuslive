# Telegram Default-Deny Enforcement

Generated: 2026-05-14

## Enforced Allowlist
- `conversational_reply`
- `critical_alert`
- `explicit_operator_requested_digest` (user requested)
- `coding_agent_completion_ack` (user requested)

## Enforced Denylist (added/confirmed)
- `opportunity_summary`
- `grant_summary`
- `research_summary`
- `ingestion_summary`
- `worker_summary`
- `scheduler_summary`
- `queue_summary`
- `topic_brief`
- `run_summary`
- `auto_digest`
- `full_report`
- `opportunities_detected`
- missing event type => denied

## Files Updated
- `lib/telegram_notification_policy.py`
- `workflows/lib/telegram_notification_policy.js`
- `lib/hermes_gate.py`
- `nexuslive/lib/hermes_gate.py`
- `nexuslive/workflows/lib/telegram_notification_policy.js` (added)

## Notes
- `hermes_gate` now normalizes legacy event aliases (`command_reply`, `direct_chat_reply`, etc.) into the allowlisted intent model.
- Background and summary tokens are hard-denied.
