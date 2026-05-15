# Telegram Spam Stabilization — Implementation Report
Date: 2026-05-15

## Status: STABILIZED ✅

## Fixes Applied

### Fix 1 — telegram_research_alert.js: Honor TELEGRAM_RESEARCH_ALERTS_ENABLED

**File:** `workflows/autonomous_research_supernode/telegram_research_alert.js`

Added module-level constant:
```javascript
const RESEARCH_ALERTS_ENABLED =
  process.env.TELEGRAM_RESEARCH_ALERTS_ENABLED === "true";
```

Added as second check in `sendTelegramMessage()` (after policy check):
```javascript
if (!RESEARCH_ALERTS_ENABLED) {
  console.log("[telegram-research-alert] TELEGRAM_RESEARCH_ALERTS_ENABLED=false — suppressed.");
  return false;
}
```

Added per-source guard in `sendResearchAlert()`:
```javascript
const perSourceEnabled = process.env.TELEGRAM_RESEARCH_PER_SOURCE_ALERTS === "true";
if (!perSourceEnabled) { return false; }
```

### Fix 2 — telegram_brief_alert.js: Honor TELEGRAM_RESEARCH_ALERTS_ENABLED

**File:** `workflows/autonomous_research_supernode/telegram_brief_alert.js`

Same `RESEARCH_ALERTS_ENABLED` module-level constant and `sendTelegramMessage()` gate applied.

### Fix 3 — Notification Policy Module

**File:** `workflows/lib/telegram_notification_policy.js`

`shouldSendTelegramNotification("research_summary")` returns `{ ok: false, reason: "blocked_event_type" }` because `"research_summary"` is in the `BLOCKED` set. This fires as the FIRST check in `sendTelegramMessage()` — before reaching the `RESEARCH_ALERTS_ENABLED` check.

Blocked event types include:
`research_summary`, `topic_brief`, `run_summary`, `auto_digest`, `ingestion_summary`, `queue_summary`, `scheduler_summary`, `worker_summary`, `opportunity_summary`, `grant_summary`.

### Fix 4 — Spam Guard Module

**File:** `workflows/lib/telegram_spam_guard.js`

`shouldSendTelegram(eventType, text)` enforces:
- **Hourly cap:** max 6 messages/hr (configurable via `MAX_RESEARCH_NOTIFICATIONS_PER_HOUR`)
- **Cooldown dedup:** SHA-256 hash of `eventType::text` — 15-minute cooldown per unique message (configurable via `TELEGRAM_NOTIFICATION_COOLDOWN_SECONDS`)
- **Kill switch:** `DISABLE_RESEARCH_SPAM_NOTIFICATIONS=true` to block all sends through this guard

State persisted to `reports/runtime/telegram_spam_guard_state.json`.

## Defense-in-Depth Order (per `sendTelegramMessage()`)

```
1. shouldSendTelegramNotification("research_summary")
   → blocked_event_type → STOP (never reaches Telegram)

2. RESEARCH_ALERTS_ENABLED check
   → false → STOP (belt + suspenders)

3. Missing credentials check
   → STOP if no token/chat_id

4. shouldSendTelegram(eventType, text)
   → hourly_cap / cooldown_duplicate → STOP (rate limit)

5. Telegram API call
   → only if all 4 gates pass (not possible with current .env)
```

## .env Flags Verified

Both `nexus-ai/.env` and `nexus-ai/workflows/autonomous_research_supernode/.env` confirm:
```
TELEGRAM_RESEARCH_ALERTS_ENABLED=false
TELEGRAM_MANUAL_ONLY=true
SCHEDULER_TELEGRAM_ENABLED=false
CEO_TELEGRAM_ENABLED=false
```

## Kill Switches Available

| Env Var | Default | Effect |
|---------|---------|--------|
| `TELEGRAM_RESEARCH_ALERTS_ENABLED` | `false` | Master gate for all research Telegram sends |
| `TELEGRAM_RESEARCH_PER_SOURCE_ALERTS` | (unset = false) | Per-source alerts within a run |
| `DISABLE_RESEARCH_SPAM_NOTIFICATIONS` | `false` | Emergency block in spam_guard.js |
| `MAX_RESEARCH_NOTIFICATIONS_PER_HOUR` | `6` | Hourly cap (spam_guard.js) |
| `TELEGRAM_NOTIFICATION_COOLDOWN_SECONDS` | `900` | Dedup window in seconds (spam_guard.js) |
| `SCHEDULER_TELEGRAM_ENABLED` | `false` | Python scheduler Telegram gate |
| `TELEGRAM_MANUAL_ONLY` | `true` | Blocks all auto-report sends in hermes_gate.py |
