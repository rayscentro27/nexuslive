# Telegram Sender Map — 2026-05-11

## All Outbound Telegram Send Paths

### 1. `telegram_bot.py::send_message()` → `hermes_gate.send_direct_response()`
- **Classification**: Conversational reply — ALLOWED
- **event_type**: `direct_chat_reply`
- **Gate check**: policy allows + content filter applied

### 2. `telegram_bot.py::_conversational_reply()` (via `send_message()`)
- **Classification**: Conversational reply — ALLOWED
- **event_type**: `direct_chat_reply`
- **Notes**: Now uses improved system prompt + internal-first routing

### 3. `operations_center/scheduler.py::_notify()` → `hermes_gate.send()`
- **Classification**: Scheduled/auto report — FORBIDDEN unless critical
- **Gate**: Checks `TELEGRAM_AUTO_REPORTS_ENABLED` first; returns early if false
- **Policy**: Also blocked by `telegram_policy_allows_send()` with `source='scheduler'`
- **Status**: SUPPRESSED ✓ (TELEGRAM_AUTO_REPORTS_ENABLED=false)

### 4. `operations_center/scheduler.py::_notify_dual()` → `_notify()` + `_email_notify()`
- **Classification**: Dual send (short Telegram + full email) — FORBIDDEN auto Telegram
- **Gate**: Same as #3 — suppressed if auto_reports disabled
- **Status**: Telegram suppressed, email only ✓

### 5. `ceo_agent/comms_reliability.py` → `hermes_gate.send_direct_response()`
- **Classification**: Short completion notice — ALLOWED
- **event_type**: `command_reply`
- **Use case**: Connectivity health check confirmation

### 6. `monitoring/monitoring_worker.py::_send_telegram()` → `hermes_gate.send()`
- **Classification**: System alert — CRITICAL only allowed
- **event_type**: `system_alert`, `monitoring_alert`
- **Status**: Blocked by policy (`source='worker'` denied) unless critical override

### 7. `monitoring/ai_usage_tracker.py::_send_telegram()`
- **Classification**: Budget alert — sends critical only via `hermes_gate.send_critical()`
- **Notes**: Routine usage reports go to `record_digest_item()` (no Telegram)
- **Status**: Critical alerts only ✓

### 8. `hermes_status_bot.py::send()` → `hermes_gate.send_direct_response()`
- **Classification**: Command reply — ALLOWED when polling active
- **event_type**: `command_reply`
- **Status**: `HERMES_STATUS_POLLING_ENABLED=false` (bot disabled) ✓

### 9. `services/nexus-research-worker/src/lib/telegram.js::sendTelegram()`
- **Classification**: Research digest — FORBIDDEN
- **Status**: Hardcoded early return (dead code path) + `ENABLE_TELEGRAM_DIGESTS=false` ✓

### 10. `signal-router/tradingview_router.py::notify_telegram()`
- **Classification**: Trading signal — FORBIDDEN
- **Status**: Skips send if `TELEGRAM_BOT_TOKEN` or `TELEGRAM_CHAT_ID` not set in plist ✓

## Forbidden Message Content (now content-filtered at gate)

Patterns blocked even if event_type passes policy:
- `🏛️ nexus research`
- `🏛️ nexus intelligence brief`
- `🏛️ nexus research run complete`
- `key findings:`
- `sources:`
- `research artifacts saved`
- `intelligence brief`

When blocked: message is NOT sent to Telegram. Save to report file or email instead.
Telegram may send: "✅ Research report saved. I kept the full summary out of Telegram."
