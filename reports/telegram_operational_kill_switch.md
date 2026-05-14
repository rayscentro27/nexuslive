# Telegram Operational Kill Switch

## Added control

- `TELEGRAM_OPERATIONAL_NOTIFICATIONS_ENABLED=false` (default)

## Behavior when false

- Blocks all non-conversational operational Telegram notifications.
- Keeps direct conversational reply path available.
- Critical alerts only pass if both:
  - event type is `critical_alert`
  - `TELEGRAM_CRITICAL_ALERTS_ENABLED=true`

## Rationale

- Removes spam risk from recurring workers and summary fanout.
- Maintains operator safety visibility via explicit critical path.
