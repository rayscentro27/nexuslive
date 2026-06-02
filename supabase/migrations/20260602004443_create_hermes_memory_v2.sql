-- =============================================================================
-- Hermes Memory v2 — Clean Active Memory Layer
-- Migration: 20260602004443_create_hermes_memory_v2
-- Phase: 4A (schema only — no data backfill in this migration)
--
-- SAFETY: This migration only creates the table and indexes.
-- No existing tables are modified. No records are deleted.
-- Data backfill requires a separate Ray-approved Phase 4B migration.
--
-- TODO (before applying): Review RLS policy below. The project uses
-- service_role-only RLS for internal Hermes tables (see hermes_executive_memory).
-- If a different access pattern is needed (e.g. anon reads for dashboard),
-- update the policy before applying.
-- =============================================================================

-- ---------------------------------------------------------------------------
-- updated_at trigger function — uses project-standard touch_updated_at()
-- Guard: only create if it doesn't exist (the function is defined in earlier
-- migrations; this is a safety fallback in case of isolated apply).
-- ---------------------------------------------------------------------------
create or replace function public.touch_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

-- ---------------------------------------------------------------------------
-- Table: public.hermes_memory_v2
-- ---------------------------------------------------------------------------
create table if not exists public.hermes_memory_v2 (
    id                   uuid        primary key default gen_random_uuid(),
    memory_id            text        unique not null,
    title                text        not null,
    summary              text        not null,
    memory_type          text        not null,
    status               text        not null,
    scope                text        not null,
    source               text,
    source_table         text,
    source_record_id     text,
    evidence_path        text,
    related_action_id    text,
    related_decision_id  text,
    related_goal_id      text,
    related_source_id    text,
    related_artifact_id  text,
    related_scout        text,
    confidence           numeric     check (confidence is null or (confidence >= 0 and confidence <= 1)),
    priority             integer     not null default 0,
    tags                 jsonb       not null default '[]'::jsonb,
    payload              jsonb       not null default '{}'::jsonb,
    created_at           timestamptz not null default now(),
    updated_at           timestamptz not null default now(),
    deprecated_at        timestamptz,
    deprecated_reason    text,
    replacement_memory_id text,
    migration_status     text        not null default 'pending',
    migration_notes      text,

    -- CHECK: memory_type must be a recognized category
    constraint chk_hmv2_memory_type check (memory_type in (
        'operating_rule',
        'ray_preference',
        'project_context',
        'goal',
        'tool_registry',
        'scout_registry',
        'approval_policy',
        'provider_status_snapshot',
        'source_intake',
        'action',
        'decision',
        'artifact',
        'lesson',
        'template',
        'fallback_rule',
        'archived_note',
        'debug_note'
    )),

    -- CHECK: status controls lifecycle
    constraint chk_hmv2_status check (status in (
        'active',
        'archived',
        'deprecated',
        'blocked',
        'needs_review'
    )),

    -- CHECK: scope gates Telegram access
    constraint chk_hmv2_scope check (scope in (
        'live_answer',
        'historical',
        'debug_only',
        'training',
        'audit',
        'blocked_from_telegram'
    )),

    -- CHECK: migration_status tracks phase progress
    constraint chk_hmv2_migration_status check (migration_status in (
        'pending',
        'dry_run',
        'approved',
        'applied',
        'rolled_back'
    ))
);

-- ---------------------------------------------------------------------------
-- Indexes
-- ---------------------------------------------------------------------------

-- Primary lookup by memory_id (already enforced by UNIQUE, explicit for clarity)
create unique index if not exists idx_hmv2_memory_id
    on public.hermes_memory_v2 (memory_id);

-- Live-answer filter — the most common Hermes query path
create index if not exists idx_hmv2_status
    on public.hermes_memory_v2 (status);

create index if not exists idx_hmv2_scope
    on public.hermes_memory_v2 (scope);

-- Category-based queries
create index if not exists idx_hmv2_memory_type
    on public.hermes_memory_v2 (memory_type);

-- Recency queries
create index if not exists idx_hmv2_updated_at
    on public.hermes_memory_v2 (updated_at desc);

-- Source linkage — used to check if a Supabase record has been migrated
create index if not exists idx_hmv2_source_ref
    on public.hermes_memory_v2 (source_table, source_record_id)
    where source_table is not null;

-- Relation indexes — for cross-entity lookups
create index if not exists idx_hmv2_related_action
    on public.hermes_memory_v2 (related_action_id)
    where related_action_id is not null;

create index if not exists idx_hmv2_related_decision
    on public.hermes_memory_v2 (related_decision_id)
    where related_decision_id is not null;

create index if not exists idx_hmv2_related_goal
    on public.hermes_memory_v2 (related_goal_id)
    where related_goal_id is not null;

-- GIN indexes for JSONB containment queries (tags, payload)
create index if not exists idx_hmv2_tags
    on public.hermes_memory_v2 using gin (tags);

create index if not exists idx_hmv2_payload
    on public.hermes_memory_v2 using gin (payload);

-- ---------------------------------------------------------------------------
-- updated_at trigger
-- ---------------------------------------------------------------------------
drop trigger if exists trg_hermes_memory_v2_touch on public.hermes_memory_v2;
create trigger trg_hermes_memory_v2_touch
    before update on public.hermes_memory_v2
    for each row execute function public.touch_updated_at();

-- ---------------------------------------------------------------------------
-- Row Level Security
-- Matches project convention: service_role has full access.
-- TODO: Review before applying if dashboard/anon access is needed.
-- ---------------------------------------------------------------------------
alter table public.hermes_memory_v2 enable row level security;

create policy "service_role_all_hmv2"
    on public.hermes_memory_v2 for all
    using (auth.role() = 'service_role');

-- ---------------------------------------------------------------------------
-- End of migration
-- DO NOT add INSERT/UPDATE/DELETE statements here.
-- Data backfill is a separate Ray-approved Phase 4B migration.
-- ---------------------------------------------------------------------------
