# Travel Mode Guardrails

## Status
- Phase K partially advanced; key safety defaults preserved.

## Preserved Guardrails
- Trading execution safety flags unchanged.
- Telegram default-deny and hermes-gated send model preserved.
- Centralized read-only operational snapshot avoids mutation risk.

## Observed Existing Gap
- JS bypass guard in `scripts/smoke_ai_ops.sh` still reports legacy direct sender paths across multiple files.
- This gap pre-existed this pass and requires a dedicated cleanup sprint.

## Recommended Follow-up
- Systematically migrate remaining raw JS Telegram senders to policy wrappers and rerun `scripts/test_telegram_js_bypass.py` until clean.
