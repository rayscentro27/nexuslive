# Hermes Memory v2 — Schema Reference

## Purpose

`hermes_memory_v2` is the clean active memory layer for Hermes. It does not replace
existing tables immediately. Records are migrated into it only after Ray explicitly approves
each batch (Phase 4B+).

**Live Telegram answers** must read only records where `status = active` AND `scope =
live_answer`. All other records are archived, blocked, or debug-only and must never surface
in normal Hermes responses.

Old memory tables (`ai_memory`, `hermes_executive_memory`, etc.) remain untouched until
an explicit Ray-approved migration executes. During the transition period they remain the
source of truth for any classification that has not yet been migrated.

---

## Core Live-Answer Rule

```
Normal Telegram answers may ONLY use:
  status = 'active'
  scope  = 'live_answer'
```

| status | scope | Allowed in Telegram? |
|---|---|---|
| active | live_answer | YES |
| active | historical | NO — only on explicit "show history" request |
| active | debug_only | NO — only on explicit debug request |
| archived | any | NO — only on explicit history request |
| deprecated | any | NEVER |
| blocked | any | NEVER |
| needs_review | any | NO — pending human review |

---

## Table: `public.hermes_memory_v2`

### Columns

| Column | Type | Notes |
|---|---|---|
| `id` | `uuid` | PK, auto-generated |
| `memory_id` | `text` | Unique human-readable ID (e.g. `mv2-provider-health-abc123`) |
| `title` | `text` | Short human-readable title |
| `summary` | `text` | 1–3 sentence description for retrieval |
| `memory_type` | `text` | One of the allowed types below |
| `status` | `text` | Lifecycle status — see allowed values |
| `scope` | `text` | Determines whether Hermes may use this for live answers |
| `source` | `text` | Origin system (e.g. `supabase`, `local_filesystem`, `operator`) |
| `source_table` | `text` | Supabase table name if sourced from Supabase |
| `source_record_id` | `text` | Row ID in the source table |
| `evidence_path` | `text` | File path or URL to supporting evidence |
| `related_action_id` | `text` | Links to an action record |
| `related_decision_id` | `text` | Links to a decision record |
| `related_goal_id` | `text` | Links to a goal record |
| `related_source_id` | `text` | Links to a source/research record |
| `related_artifact_id` | `text` | Links to a content artifact |
| `related_scout` | `text` | Scout agent that produced this record |
| `confidence` | `numeric` | 0.0–1.0 confidence score |
| `priority` | `integer` | Higher = more important (default 0) |
| `tags` | `jsonb` | Array of string tags for filtering |
| `payload` | `jsonb` | Arbitrary structured metadata |
| `created_at` | `timestamptz` | Record creation time |
| `updated_at` | `timestamptz` | Last update (auto-maintained by trigger) |
| `deprecated_at` | `timestamptz` | When this record was deprecated |
| `deprecated_reason` | `text` | Why it was deprecated |
| `replacement_memory_id` | `text` | Points to the record that replaced this one |
| `migration_status` | `text` | Phase migration tracking: `pending`, `dry_run`, `approved`, `applied`, `rolled_back` |
| `migration_notes` | `text` | Free-form notes about migration decisions |

---

## Allowed Values

### `memory_type`

| Value | Description |
|---|---|
| `operating_rule` | Core operating constraints for Hermes |
| `ray_preference` | Ray's stated preferences and working style |
| `project_context` | Active project context and phase information |
| `goal` | Business or operational goal |
| `tool_registry` | Registered tool or integration |
| `scout_registry` | Scout agent registration and capability |
| `approval_policy` | What requires Ray approval before acting |
| `provider_status_snapshot` | Point-in-time snapshot of an AI provider health |
| `source_intake` | Research source or knowledge intake record |
| `action` | A queued or completed action |
| `decision` | A Hermes decision and its rationale |
| `artifact` | A content artifact (draft, template, etc.) |
| `lesson` | A learned lesson or post-mortem insight |
| `template` | A reusable response or content template |
| `fallback_rule` | A fallback response rule for Hermes |
| `archived_note` | Historical note kept for reference only |
| `debug_note` | Debugging or diagnostic information |

### `status`

| Value | Description |
|---|---|
| `active` | Currently valid and usable |
| `archived` | Retained for history, not used for live answers |
| `deprecated` | Replaced by a newer record — must never be used live |
| `blocked` | Explicitly blocked from Telegram — contains stale or misleading data |
| `needs_review` | Awaiting human review before classification |

### `scope`

| Value | Description |
|---|---|
| `live_answer` | Safe for normal Hermes Telegram responses |
| `historical` | Historical context only — use only when Ray asks for history |
| `debug_only` | Debug/diagnostic use only |
| `training` | Training data for model fine-tuning |
| `audit` | Audit trail records |
| `blocked_from_telegram` | Must never appear in Telegram responses |

---

## Indexes

- `memory_id` — unique index (primary lookup)
- `status` — fast filter for active/archived/blocked
- `scope` — fast filter for live_answer
- `memory_type` — category-based queries
- `updated_at DESC` — recency queries
- `(source_table, source_record_id)` — source linkage lookups
- `related_action_id` — action linkage
- `related_decision_id` — decision linkage
- `related_goal_id` — goal linkage
- `tags` — GIN index for JSONB array containment queries
- `payload` — GIN index for JSONB key queries

---

## Phase Transition Model

```
Phase 3/3B  — Audit and classify existing sources (DRY RUN only)
Phase 4A    — Schema definition + migration plan + guardrails (NO WRITES)
Phase 4B    — Ray-approved apply: create table, backfill first batch
Phase 4C+   — Incremental migration of remaining sources
```

Records in `hermes_memory_v2` during migration carry:

- `migration_status = 'dry_run'` — proposed, not yet applied
- `migration_status = 'approved'` — Ray has approved this batch
- `migration_status = 'applied'` — written to Supabase
- `migration_status = 'rolled_back'` — migration was undone

---

## Safety Constraints

1. `status IN ('active', 'archived', 'deprecated', 'blocked', 'needs_review')` — enforced by CHECK
2. `scope IN ('live_answer', 'historical', 'debug_only', 'training', 'audit', 'blocked_from_telegram')` — enforced by CHECK
3. `memory_type` must be one of 17 allowed values — enforced by CHECK
4. `memory_id` must be unique — enforced by UNIQUE constraint
5. RLS: `service_role` access only (matches project convention)
6. `deprecated` and `blocked` records are never returned in live-answer queries
