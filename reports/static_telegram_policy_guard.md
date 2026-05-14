# Static Telegram Policy Guard

Generated: 2026-05-14

## Guard file
- `scripts/test_telegram_policy.py`

## Guard behavior
- Fails when non-test Python files contain raw Telegram bypass signatures:
  - `sendMessage`
  - `bot.send_message(`
  - `context.bot.send_message(`
  - `telegram.Bot(`
- Only allowlisted bypass file: `lib/hermes_gate.py`.

## Result
- Final run: `31/31` passed.
