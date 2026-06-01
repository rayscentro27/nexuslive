# Hermes Memory Classification Rules
*Version 1.0 — Phase 3 (2026-06-01)*
*Owner: Ray Davis / Nexus AI*

This document defines the canonical memory classification scheme for all Hermes
memory sources. Every memory source must be classified before it may influence
Telegram responses. Classification is enforced by automated tests after every
memory-layer change.

---

## Classification Types

### 1. active_live_answer
Sources that Hermes MAY use for normal Telegram answers.

**Allowed:**
- Current artifact registry (`nexus_artifact_registry.py`)
- Current action queue (`docs/reports/actions/hermes_action_queue.jsonl`)
- Current decision log (`docs/reports/hermes_decision_log.jsonl`)
- Current source intake (`docs/reports/intake/`)
- Current content artifacts (`docs/reports/content/*.md`, `docs/content/newsletter/*.md`)
- Active operating rules (`operational_philosophy` from hermes_executive_memory via active reader)
- Active goals (from hermes_executive_memory via active reader when populated)
- Live provider policy (`hermes_provider_policy.py`)
- Active approved lessons (`docs/reports/ray_feedback/`, `docs/reports/hermes_mistake_memory.json`)
- Knowledge gaps (`docs/reports/knowledge_gaps/*.jsonl`)
- Proactive notification log (`docs/reports/hermes_proactive_notifications.jsonl`)
- Supabase: hermes_executive_memory (via active_memory_reader ONLY)
- Supabase: worker_heartbeats, trades, signals, job_events, owner_approval_queue
- Supabase: leads, funding_applications, user_profiles, invite_codes
- Supabase: knowledge_items, business_opportunities, hermes_aggregates
- Supabase: executive_briefings (most recent only, age < 48h)
- Supabase: hermes_response_patterns (with embedded fallback)
- Supabase: worker_failure_events, worker_daily_quotas, human_approval_requests

**Rule:** If a source is unavailable → return "data unavailable" or empty state, NEVER a stale hardcoded substitute.

---

### 2. historical_only
Sources that contain valid data but must NOT be presented as current operational state.

**Allowed only when Ray explicitly requests history:**
- Old handoffs (`docs/reports/handoffs/`, `docs/reports/hermes_handoffs/`)
- Old executive memory snapshots (`.hermes_ops_memory.json`, `.hermes_cli_handoffs.json`)
- Old provider status snapshots (`docs/reports/supabase/`)
- Previous project phase notes (`docs/reports/phase2_memory_safety_*.md`)
- Old reports and audit records
- Supabase: ai_memory, approved_signals, signal_reviews, approved_strategies
- Supabase: strategy_reviews, content_outputs, strategy_performance, paper_trades
- Supabase: agent_capabilities, memory_links
- Artifact flags: `artifacts/source_flags/`, `artifacts/watcher_flags/`
- Knowledge intake: `reports/knowledge_intake/`

**Rule:** May only be surfaced via explicit commands: "show history", "show archived memory", "show old handoffs", etc.

---

### 3. deprecated
Superseded source types that should not be written to or read from.

**Deprecated:**
- Old Executive Memory monetization handler (hermes_internal_first.py — patched in commit 07ba042)
- Stale `_exec_mem.load_memory()` calls for live monetization answers
- Old generic evidence dump for monetization questions (replaced by hermes_monetization_today.py)
- Old provider status assumptions from initial setup phase
- Old command routing for monetization that mapped to generic evidence

**Rule:** No new code should read from deprecated sources. Existing reads must be removed or guarded in future phases.

---

### 4. blocked_from_live
Sources that must NEVER reach Telegram as live state, regardless of what they contain.

**Blocked:**
- Stale "Ollama OFFLINE" default (from early executive memory)
- Stale "Beehiiv pending" default
- Stale "YouTube Studio pending" default
- Stale "OpenRouter not configured" default
- Old Executive Memory fallback dumps (`ARCHIVED EXECUTIVE MEMORY — NOT CURRENT TRUTH`)
- Fake operational claims (fabricated pending counts, fake task names like "NitroTrades")
- Fabricated commit hashes
- `[artifact_inventory]` raw label string in conversational responses
- `[revenue_plan]` raw label string in conversational responses
- `format_evidence_response()` output for monetization/revenue/business questions
- `build_evidence_only_response()` output for conversational questions
- `.hermes_executive_memory.json` local file contents (safe-empty sentinel only)
- `hermes_executive_memory.load_memory()` for live Telegram answers (use active_memory_reader)
- "I can answer from verified artifacts." as a response to monetization questions
- "Monetization evidence:" as a response header to conversational questions
- "Evidence used:" + raw artifact path list as a response to conversational questions

**Rule:** If any blocked_from_live marker appears in a Telegram response → automated test FAILS.

---

### 5. debug_only
Sources that may be accessed by Hermes only when Ray explicitly requests debug/raw output.

**Debug-only sources:**
- Raw artifact file paths (`docs/reports/evidence/`)
- Raw memory dumps (`show stale memory debug`, `show archived executive memory`)
- Archived executive memory defaults
- Developer diagnostics and source hunt reports
- `build_evidence_only_response()` artifact path lists
- `format_evidence_response()` raw output (only for "show raw evidence" commands)
- `.hermes_executive_memory.json` contents (source=empty_safe_fallback, only for debug)

**Trigger commands (explicit debug requests only):**
- "show raw evidence"
- "show debug memory"
- "show archived executive memory"
- "show stale memory debug"
- "show artifact inventory"
- "show evidence paths"
- "debug evidence"

**Rule:** These sources must NOT be reachable via normal conversational phrases.

---

### 6. needs_review
Sources whose classification is uncertain, conflicting, or requires Ray's decision.

**Needs review:**
- Supabase: provider_health (may contain stale OFFLINE records)
- Supabase: ai_task_queue (unclear if feeds Telegram answers)
- Supabase: nexus_skills (unclear if actively populated)
- Supabase: agent_dispatch_tasks (unclear if Telegram-facing)

**Rule:** Sources in needs_review must be treated as historical_only until classified. They must not influence live answers.

---

## Enforcement Contract

All memory classification decisions are enforced by:

1. `scripts/test_memory_classification_blocks_stale_defaults.py` — verifies stale defaults are blocked
2. `scripts/test_memory_classification_rules.py` — verifies this document exists and has all sections
3. `scripts/test_memory_source_map_exists.py` — verifies audit reports exist
4. `scripts/test_memory_v2_dry_run_generator.py` — verifies dry-run records have correct fields
5. `scripts/test_memory_classification_no_supabase_writes.py` — verifies no writes
6. `scripts/test_memory_classification_counts.py` — verifies count thresholds

---

## Migration Rule for hermes_memory_v2

When a memory source is migrated to `hermes_memory_v2`:
- `status` field must match this classification
- `scope` field maps: active_live_answer → `live_answer`, historical_only → `historical`, blocked_from_live → `blocked_from_telegram`, deprecated → `historical`, debug_only → `debug_only`
- `migration_notes` must explain why the source was deprecated/blocked if applicable
- No source with `status: "blocked"` or `scope: "blocked_from_telegram"` may ever be returned by a live Telegram query path

---

## Version History

| Version | Date | Changes |
|---|---|---|
| 1.0 | 2026-06-01 | Initial classification after Phase 3 audit |
