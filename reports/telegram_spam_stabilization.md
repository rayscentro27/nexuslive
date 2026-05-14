# Telegram Spam Stabilization

## Immediate containment implemented

- Added shared spam guard: `workflows/lib/telegram_spam_guard.js`
  - message hash dedup
  - cooldown suppression (`TELEGRAM_NOTIFICATION_COOLDOWN_SECONDS`, default 900)
  - hourly cap (`MAX_RESEARCH_NOTIFICATIONS_PER_HOUR`, default 6)
  - temporary kill switch (`DISABLE_RESEARCH_SPAM_NOTIFICATIONS`)

- Applied guard to high-noise research senders:
  - `workflows/autonomous_research_supernode/telegram_research_alert.js`
  - `workflows/autonomous_research_supernode/telegram_brief_alert.js`
  - `workflows/research_ingestion/telegram_research_ingestion_alert.js`
  - `workflows/research_desk/telegram_research_alert.js`

- Added explicit research notification gate requirement:
  - `TELEGRAM_RESEARCH_ALERTS_ENABLED=true` required for ingestion/research-desk alert sends

- Reduced fanout at source:
  - Per-source supernode alerts now require `TELEGRAM_RESEARCH_PER_SOURCE_ALERTS=true` (default suppressed)

## Operational result

- High-frequency duplicate/looping research alerts are now suppressed via cooldown + hash dedup + hourly cap.
- Telegram remains available for meaningful updates while removing repeated low-value churn.
