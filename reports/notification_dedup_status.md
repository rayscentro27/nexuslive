# Notification Dedup Status

## Active dedup/throttle controls

- `workflows/lib/telegram_spam_guard.js`
  - Hash dedup for event+message payload
  - Cooldown suppression (`TELEGRAM_NOTIFICATION_COOLDOWN_SECONDS`, default 900)
  - Hourly cap (`MAX_RESEARCH_NOTIFICATIONS_PER_HOUR`, default 6)
  - Kill switch (`DISABLE_RESEARCH_SPAM_NOTIFICATIONS`)

- Research sender gating
  - `TELEGRAM_RESEARCH_ALERTS_ENABLED` required for research/ingestion desk sends
  - `TELEGRAM_RESEARCH_PER_SOURCE_ALERTS` required for per-source supernode alerts

## Remaining policy posture

- No live trading paths were enabled.
- Hermes core messaging was not disabled.
- Notifications are throttled/reduced, not permanently removed.
