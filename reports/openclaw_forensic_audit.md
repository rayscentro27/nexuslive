# OpenClaw Forensic Audit

Generated: 2026-05-14

## Runtime Checks
- `ps aux | rg -i "openclaw|18789"` => no OpenClaw service process.
- `lsof -i -P | rg "18789|openclaw"` => no listener on 18789.
- No `ai.openclaw.gateway` launch label found in current user launch list.

## Code/Routing Checks
- OpenClaw references remain in:
  - `lib/model_router.py` (both repos)
  - `lib/nexus_model_caller.py` (both repos)
  - docs/tests/readmes
- Default routing toggle changed from `OPENCLAW_ENABLED=true` default to `false` default in both repos.

## Determination
1. Is OpenClaw running? **No**.
2. Is Hermes still connected to OpenClaw at runtime? **Not by active local service**.
3. Any provider routing dependency still present in code? **Yes, legacy optional path remains**.
4. Dormant legacy code? **Yes (mostly dormant references/docs/tests)**.
5. Will removal break core Hermes conversation? **Not if OpenClaw remains disabled; conversational path can use other providers**.
