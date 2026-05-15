# Travel Telegram Hardening

- `python3 scripts/test_telegram_policy.py` → PASS (31/31)
- `python3 scripts/test_hermes_telegram_pipeline.py` → PASS (71/71)
- `python3 scripts/test_telegram_js_bypass.py` → PASS

Hardening status:
- No autonomous summary fanout re-enabled.
- Conversational and explicit request flows remain functional.
- Remaining JS senders are now default-manual gated in this pass.
