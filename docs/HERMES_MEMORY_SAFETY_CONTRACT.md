# Hermes Memory Safety Contract

**Effective:** Phase 2 (June 2026)
**Scope:** All Hermes memory/fallback paths exposed to Telegram users
**Enforcement:** Automated tests verify compliance after every memory-layer change

## Purpose

Prevent stale, hardcoded, or default memory values from reaching Telegram
users as if they were live operational state.

---

## Memory Categories

### 1. Live Answer Memory
Allowed for normal Telegram answers:
- Current artifact registry
- Current action queue
- Current decision log
- Current source intake
- Current content artifacts
- Active goals
- Active operating rules
- Live provider policy

### 2. Historical Memory
Allowed only when Ray explicitly asks for history:
- Old executive memory
- Old handoffs
- Old provider status snapshots
- Old planning notes
- Archived reports

### 3. Deprecated Memory
Never allowed for live answers:
- Stale "Ollama OFFLINE" default
- Beehiiv pending default
- YouTube Studio pending default
- OpenRouter not configured default
- Old demo response examples
- Fake approval counts
- Fake operational claims
- Old NitroTrades-style fabricated task details

### 4. Debug Memory
Allowed only when Ray explicitly asks:
- "show debug memory"
- "show archived executive memory"
- "show stale memory debug"

---

## Core Rule

**Normal Telegram answers must not use hardcoded stale executive memory
or stale fallback blocks.**

## Rules

### Rule 1 — No stale defaults in live paths

Functions that load memory for Telegram injection MUST return empty/neutral
data when the canonical source (Supabase) is unreachable or empty. They MUST
NOT fall back to hardcoded defaults that impersonate live state.

```
GOOD:  "I could not resolve that from active memory."
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

### Rule 5 — Historical and debug memory require explicit opt-in

Archived executive memory, stale defaults, and debug memory dumps MUST
only be shown when Ray explicitly requests them with dedicated commands.
Every such response MUST include a "NOT CURRENT TRUTH" or "DEBUG ONLY"
warning label.

### Rule 6 — Every memory write logs source

All writes to Supabase memory tables must include an `updated_by` field
identifying the calling component.

## Enforcement

- `test_memory_safety_contract_exists.py` — contract document exists
- `test_stale_executive_defaults_blocked.py` — Rules 1, 2
- `test_quality_fallback_no_stale_memory.py` — Rule 4
- `test_active_memory_reader.py` — Rule 3
- `test_telegram_no_stale_memory_fallback.py` — core rule
- `test_archived_memory_explicit_only.py` — Rule 5
- `test_memory_sources_command.py` — source transparency
- CI gate: all seven Phase 2 tests must pass before merge

## Violation Procedure

If a memory safety violation is detected:
1. The offending path is blocked at the import level (patch import to active reader)
2. A warning is logged with `HERMES_SAFETY_VIOLATION` tag
3. The Phase 2 report is updated with the finding
