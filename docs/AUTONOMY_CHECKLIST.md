# Autonomy Checklist

Updated: 2026-04-23

## Done

- OpenRouter paid completions are working.
- Scheduler is running.
- Hermes/email status commands exist.
- Trading autonomy status script exists:
  - `scripts/trading_autonomy_status.py --format json|brief`
- Email `[STATUS]` replies now use a cleaner summary-first format.
- Email loop guard added:
  - only explicit `[TASKS]` triggers task creation
  - self-sent mailbox replies are skipped
  - generic `Nexus ...` scheduler emails no longer get misclassified as tasks
- Shared status source added:
  - `scripts/autonomy_status.py --format json|brief|attention|full`

## Still Open

- Hermes Telegram ingestion is not reliable.
- Gmail auth state is inconsistent between manual checks and launch-agent processing.
- Hermes runtime still shows fallback/noisy model behavior in logs.
- Scheduler-side Telegram-capable notification code still exists separately from Hermes.
- Trading engine receiver health still needs live verification after status/runtime hardening.

## Definition Of Done

- Hermes reliably ingests and replies to fresh Telegram operator commands.
- Email `[STATUS]` reliably ingests and replies without auth drift.
- Status surfaces all read from the same source of truth.
- No self-reply or subject-classification loops remain.
- Failures are surfaced once, clearly, without spam.

## Suggested Order

1. Hermes Telegram intake
2. Gmail auth consistency
3. Status-source adoption everywhere
4. Remaining notification-path cleanup
5. Failure recovery / restart policy review
