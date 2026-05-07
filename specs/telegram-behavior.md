# Telegram Behavior Spec

## Operating Mode
Telegram is manual-first and conversational-first.

## Core Rules
- No autonomous spam.
- No periodic auto-brief broadcasts unless explicitly enabled.
- Replies are sent when operator sends a message first.

## Manual-only Policy
- `TELEGRAM_MANUAL_ONLY=true` keeps outbound traffic user-initiated by default.
- Background worker completion should be persisted/logged, not pushed to chat.
- `TELEGRAM_AUTO_REPORTS_ENABLED=false` suppresses routine automated messages.

## Admin Command Behavior
- Existing command set remains backward compatible (`/status`, `/health`, `/brief`, `/research`, `/reset`, `/restart`).
- Unknown natural-language inputs should get conversational answers, not hard failures.

## Critical Alert Policy
- Only critical events may bypass routine suppression.
- Critical events still use deduplication and cooldown windows.
- Repeated identical critical failures should not spam the chat.

## Rate Limiting and Deduplication
- Global rate cap for automated channels.
- Event-level cooldown by event type/hash.
- Direct user responses bypass global cap but can include short-window duplicate guards.

## Feature Flags
- `TELEGRAM_ENABLED`: master enable/disable for Telegram sends.
- `TELEGRAM_AUTO_REPORTS_ENABLED`: enables/disables automated outbound reports.
- `TELEGRAM_MANUAL_ONLY`: forces manual-only policy for background workflows.
- `TELEGRAM_CONVERSATIONAL_MODE`: enables natural-language reply handling.

## Operator Control Surface
- Admin-only Control Center endpoint can update Telegram safety flags:
  - `POST /api/admin/ai-ops/telegram-mode`
- Read endpoint remains diagnostics only:
  - `GET /api/admin/ai-ops/status`
- Both endpoints require admin token and are not client-facing.
- Toggle writes are logged for auditability.
