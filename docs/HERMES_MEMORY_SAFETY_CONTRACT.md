# Hermes Memory Safety Contract

**Effective:** Phase 2 (June 2026)
**Scope:** All Hermes memory/fallback paths exposed to Telegram users
**Enforcement:** Automated tests verify compliance after every memory-layer change

## Purpose

Prevent stale, hardcoded, or default memory values from reaching Telegram
users as if they were live operational state.

## Rules

### Rule 1 — No stale defaults in live paths

Functions that load memory for Telegram injection MUST return empty/neutral
data when the canonical source (Supabase) is unreachable or empty. They MUST
NOT fall back to hardcoded defaults that impersonate live state.

```
GOOD:  "Executive memory unavailable — run `nexus executive status`"
BAD:   "Ollama OFFLINE, Beehiiv pending, OpenRouter not configured"
```

### Rule 2 — Archived defaults exist for reference only

Hardcoded default values MAY exist in a dedicated `load_archived_*` function
for reference, seeding, or migration tooling. They MUST NOT be reachable
from any `load_memory()` or `build_*_context()` path.

### Rule 3 — Active Memory Reader is the single entry point

All Telegram-facing code that reads executive memory MUST go through
`lib/hermes_active_memory_reader.py`. No direct imports of
`lib/hermes_executive_memory` from bot code.

### Rule 4 — Quality escalation never dumps stale data

The quality-guard fallback (`_fallback_data_block`) MUST return a clean
clarification message, not a data block containing stale or hardcoded
executive memory values.

### Rule 5 — Every memory write logs source

All writes to Supabase memory tables must include an `updated_by` field
identifying the calling component.

## Enforcement

- `test_no_stale_executive_memory_fallback.py` — verifies Rule 4
- `test_active_memory_reader_smoke.py` — verifies Rule 3
- `test_executive_memory_no_stale_defaults.py` — verifies Rule 1
- `test_telegram_memory_isolation.py` — verifies Rule 2
- `test_archived_memory_commands.py` — verifies archive route works
- CI gate: all six Phase 2 tests must pass before merge

## Violation Procedure

If a memory safety violation is detected:
1. The offending path is blocked at the import level (patch import to active reader)
2. A warning is logged with `HERMES_SAFETY_VIOLATION` tag
3. The Phase 2 report is updated with the finding
