# Default-Deny Telegram Policy

## Policy modules

- Python: `lib/telegram_notification_policy.py`
- JS: `workflows/lib/telegram_notification_policy.js`

## Default behavior

- Deny when `event_type` is missing.
- Deny all operational notification classes unless explicitly allowlisted.
- Operational kill switch defaults to disabled:
  - `TELEGRAM_OPERATIONAL_NOTIFICATIONS_ENABLED=false`

## Allowed classes

- `conversational_reply`
- `critical_alert` (gated by `TELEGRAM_CRITICAL_ALERTS_ENABLED`)
- `explicit_operator_requested_digest`
- `coding_agent_completion_ack` (explicit request path)

## Explicitly blocked classes

- `research_summary`
- `ingestion_summary`
- `queue_summary`
- `scheduler_summary`
- `worker_summary`
- `ticket_summary`
- `provider_summary`
- `auto_digest`
- `full_report`
