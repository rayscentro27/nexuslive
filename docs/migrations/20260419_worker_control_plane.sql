-- =============================================================================
-- Nexus worker control plane
-- Target project: ygqglfbhxiumqdisauar
--
-- Purpose:
-- 1. Define desired-state records for autonomous workers/services
-- 2. Create an append-only action log for operator/Hermes control requests
-- 3. Keep the first control slice non-destructive and auditable
-- =============================================================================

create extension if not exists "pgcrypto";

create table if not exists public.worker_control_plane (
  worker_id         text primary key,
  worker_type       text not null,
  enabled           boolean not null default true,
  desired_state     text not null default 'running',
  schedule_seconds  integer,
  maintenance_mode  boolean not null default false,
  control_mode      text not null default 'manual',
  runtime_label     text,
  notes             text,
  metadata          jsonb not null default '{}'::jsonb,
  last_changed_by   text,
  last_changed_at   timestamptz not null default now(),
  created_at        timestamptz not null default now(),
  updated_at        timestamptz not null default now()
);

create index if not exists worker_control_plane_type_idx
  on public.worker_control_plane (worker_type, enabled);

create index if not exists worker_control_plane_runtime_idx
  on public.worker_control_plane (runtime_label);

create table if not exists public.worker_control_actions (
  id                 uuid primary key default gen_random_uuid(),
  target_worker_id   text not null,
  action_type        text not null,
  payload            jsonb not null default '{}'::jsonb,
  status             text not null default 'pending',
  validation_result  jsonb not null default '{}'::jsonb,
  execution_result   jsonb not null default '{}'::jsonb,
  requested_by       text not null,
  requested_at       timestamptz not null default now(),
  approved_by        text,
  approved_at        timestamptz,
  executed_at        timestamptz,
  created_at         timestamptz not null default now(),
  updated_at         timestamptz not null default now()
);

create index if not exists worker_control_actions_status_idx
  on public.worker_control_actions (status, requested_at);

create index if not exists worker_control_actions_target_idx
  on public.worker_control_actions (target_worker_id, requested_at desc);

insert into public.worker_control_plane (
  worker_id,
  worker_type,
  enabled,
  desired_state,
  schedule_seconds,
  control_mode,
  runtime_label,
  notes
)
values
  ('nexus-orchestrator', 'orchestrator', true, 'running', null, 'automatic', 'com.nexus.orchestrator', 'Primary workflow dispatcher'),
  ('nexus-research-worker', 'worker', true, 'running', null, 'automatic', 'com.nexus.research-worker', 'Queue-based research worker'),
  ('research-orchestrator-transcript', 'scheduler', true, 'running', 7200, 'automatic', 'com.nexus.research-orchestrator-transcript', 'YouTube transcript ingestion'),
  ('research-orchestrator-grants-browser', 'scheduler', true, 'running', 14400, 'automatic', 'com.nexus.research-orchestrator-grants-browser', 'Grant browser ingestion'),
  ('grant-worker', 'scheduler', true, 'running', 14400, 'automatic', 'com.nexus.grant-worker', 'Grant opportunity scoring'),
  ('opportunity-worker', 'scheduler', true, 'running', 7200, 'automatic', 'com.nexus.opportunity-worker', 'Opportunity scoring'),
  ('openclaw-gateway', 'gateway', true, 'running', null, 'manual', 'ai.openclaw.gateway', 'Shared local AI gateway'),
  ('hermes-gateway', 'gateway', true, 'running', null, 'manual', 'ai.hermes.gateway', 'Hermes runtime service')
on conflict (worker_id) do update
set
  worker_type      = excluded.worker_type,
  enabled          = excluded.enabled,
  desired_state    = excluded.desired_state,
  schedule_seconds = excluded.schedule_seconds,
  control_mode     = excluded.control_mode,
  runtime_label    = excluded.runtime_label,
  notes            = excluded.notes,
  updated_at       = now();

select pg_notify('pgrst', 'reload schema');
