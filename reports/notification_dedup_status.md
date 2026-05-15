# Notification Dedup Status
Date: 2026-05-15

## Status: ACTIVE ✅

## Active Dedup / Throttle Controls

### workflows/lib/telegram_spam_guard.js
- SHA-256 hash of `eventType::messageText` for exact-match dedup
- Cooldown window: `TELEGRAM_NOTIFICATION_COOLDOWN_SECONDS` (default 900s = 15 min)
- Hourly cap: `MAX_RESEARCH_NOTIFICATIONS_PER_HOUR` (default 6)
- Kill switch: `DISABLE_RESEARCH_SPAM_NOTIFICATIONS=true`
- State file: `reports/runtime/telegram_spam_guard_state.json`

### workflows/lib/telegram_notification_policy.js
- Blocked event types by default: `research_summary`, `topic_brief`, `run_summary`, `auto_digest`, `ingestion_summary`, `queue_summary`, `scheduler_summary`, `worker_summary`
- Only `conversational_reply`, `critical_alert`, `explicit_operator_requested_digest`, `coding_agent_completion_ack` are allowed
- `TELEGRAM_OPERATIONAL_NOTIFICATIONS_ENABLED=false` (default) suppresses non-critical operational sends

### lib/hermes_gate.py (Python)
- 5/hr global rate limit
- Per-event cooldowns (critical=1h, summary=24h)
- SHA-256 hash dedup with TTL
- `TELEGRAM_MANUAL_ONLY=true` → `_auto_reports_enabled()` returns False → all non-critical auto sends blocked
- `_HARD_DENY_EVENT_TOKENS`: "research", "signal", "trading", "alert_" etc.
- `_FORBIDDEN_CONTENT_PATTERNS`: "nexus research run complete", "intelligence brief"

## Research Sender Gating

| File | Gate Required |
|------|---------------|
| `telegram_research_alert.js` | `TELEGRAM_RESEARCH_ALERTS_ENABLED=true` |
| `telegram_brief_alert.js` | `TELEGRAM_RESEARCH_ALERTS_ENABLED=true` |
| Per-source alerts | `TELEGRAM_RESEARCH_PER_SOURCE_ALERTS=true` (additional) |

## Policy Posture

- No live trading paths enabled
- Hermes core conversational messaging not affected
- Notifications throttled and policy-gated, not permanently disabled
- Critical alerts still flow if `TELEGRAM_CRITICAL_ALERTS_ENABLED=true` (default true)
