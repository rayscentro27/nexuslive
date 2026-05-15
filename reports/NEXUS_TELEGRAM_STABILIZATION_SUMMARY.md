# Nexus Telegram Spam Stabilization — Complete Summary
Date: 2026-05-15

## Status: STABILIZED ✅

---

## Root Cause

**Source:** `workflows/autonomous_research_supernode/research_orchestrator.js`

Two macOS launchd jobs (transcript every 2h, grants-browser every 4h) triggered the Node.js research orchestrator. The orchestrator called `telegram_research_alert.js` and `telegram_brief_alert.js` which made direct Telegram API calls, bypassing Python's `hermes_gate.py` entirely.

`TELEGRAM_RESEARCH_ALERTS_ENABLED=false` was already in both `.env` files but was never read by the JS files — it was dead config.

---

## Containment

### Files Modified

| File | Change |
|------|--------|
| `workflows/autonomous_research_supernode/telegram_research_alert.js` | Added `RESEARCH_ALERTS_ENABLED` env check + policy/spam guard imports |
| `workflows/autonomous_research_supernode/telegram_brief_alert.js` | Added `RESEARCH_ALERTS_ENABLED` env check + policy/spam guard imports |

### Files Created

| File | Purpose |
|------|---------|
| `workflows/lib/telegram_spam_guard.js` | SHA-256 dedup + 15-min cooldown + hourly cap + kill switch |
| `workflows/lib/telegram_notification_policy.js` | Policy allowlist/blocklist — "research_summary" is blocked by default |

### Defense-in-Depth (per sendTelegramMessage call)

1. `shouldSendTelegramNotification("research_summary")` → `blocked_event_type` → STOP
2. `RESEARCH_ALERTS_ENABLED` env check → `false` → STOP
3. Credentials check → STOP if missing
4. `shouldSendTelegram(...)` → hourly cap / cooldown → STOP
5. Telegram API call → only if all 4 pass (impossible with current .env)

---

## Phase C — Escalation Loop Audit

No active escalation loops found:
- `research_request_service.py`: 30-min same-query cooldown already in place
- `research_processing_worker.py`: errors reject tickets (not re-queue)
- `hermes_supabase_first.py`: operational queries firewalled from ticket creation
- No Telegram calls in any research Python worker

---

## Kill Switches

| Env Var | Default | Description |
|---------|---------|-------------|
| `TELEGRAM_RESEARCH_ALERTS_ENABLED` | `false` | Master gate — JS research sends |
| `TELEGRAM_RESEARCH_PER_SOURCE_ALERTS` | unset | Per-source alerts (off unless set) |
| `DISABLE_RESEARCH_SPAM_NOTIFICATIONS` | `false` | Emergency spam_guard kill switch |
| `MAX_RESEARCH_NOTIFICATIONS_PER_HOUR` | `6` | Hourly rate cap |
| `TELEGRAM_NOTIFICATION_COOLDOWN_SECONDS` | `900` | Dedup window |
| `SCHEDULER_TELEGRAM_ENABLED` | `false` | Python scheduler gate |
| `TELEGRAM_MANUAL_ONLY` | `true` | Blocks all Python auto-report sends |

---

## Safety Verification

| Check | Status |
|-------|--------|
| `NEXUS_DRY_RUN=true` | ✅ preserved |
| `LIVE_TRADING=false` | ✅ preserved |
| `TRADING_LIVE_EXECUTION_ENABLED=false` | ✅ preserved |
| `NEXUS_AUTO_TRADING=false` | ✅ preserved |
| No knowledge deleted | ✅ |
| No valid notifications disabled permanently | ✅ |
| Hermes core messaging unaffected | ✅ |
| No secrets exposed | ✅ |

---

## Reports

| Report | Contents |
|--------|----------|
| `telegram_spam_root_cause.md` | Exact origin, trigger frequency, why gate was bypassed |
| `telegram_spam_stabilization.md` | All fixes applied, defense-in-depth order, kill switch table |
| `research_escalation_loop_fix.md` | Escalation loop audit, query cooldown status |
| `notification_dedup_status.md` | Active dedup controls across all layers |
| `NEXUS_TELEGRAM_STABILIZATION_SUMMARY.md` | This file |
