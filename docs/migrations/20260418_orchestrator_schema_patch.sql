-- =============================================================================
-- Nexus Orchestrator / Research Worker schema patch
-- Target project: ygqglfbhxiumqdisauar
--
-- Purpose:
-- 1. Align existing tables with current running code
-- 2. Create missing orchestration / monitoring tables
-- 3. Reload PostgREST schema cache
-- =============================================================================

create extension if not exists "pgcrypto";

-- -----------------------------------------------------------------------------
-- Existing tables: patch missing columns expected by live code
-- -----------------------------------------------------------------------------

alter table if exists public.worker_heartbeats
  add column if not exists metadata jsonb;

-- Preserve any existing data written to the older `meta` column.
update public.worker_heartbeats
set metadata = coalesce(metadata, meta, '{}'::jsonb)
where metadata is null;

alter table if exists public.job_queue
  add column if not exists workflow_id uuid;

-- -----------------------------------------------------------------------------
-- Missing orchestrator event intake table
-- -----------------------------------------------------------------------------

create table if not exists public.system_events (
  id               uuid primary key default gen_random_uuid(),
  event_type       text not null,
  payload          jsonb not null default '{}'::jsonb,
  status           text not null default 'pending',
  attempt_count    integer not null default 0,
  claimed_by       text,
  claimed_at       timestamptz,
  lease_expires_at timestamptz,
  completed_at     timestamptz,
  last_error       text,
  created_at       timestamptz not null default now(),
  updated_at       timestamptz not null default now()
);

create index if not exists system_events_status_created_idx
  on public.system_events (status, created_at);

create index if not exists system_events_lease_idx
  on public.system_events (lease_expires_at);

-- -----------------------------------------------------------------------------
-- Workflow run tracking
-- -----------------------------------------------------------------------------

create table if not exists public.orchestrator_workflow_runs (
  id            uuid primary key default gen_random_uuid(),
  workflow_type text not null,
  status        text not null default 'running',
  trigger_event uuid references public.system_events(id) on delete set null,
  tenant_id     uuid,
  metadata      jsonb not null default '{}'::jsonb,
  started_at    timestamptz not null default now(),
  completed_at  timestamptz,
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now()
);

create index if not exists orchestrator_workflow_runs_status_idx
  on public.orchestrator_workflow_runs (status, created_at);

create index if not exists orchestrator_workflow_runs_type_idx
  on public.orchestrator_workflow_runs (workflow_type, created_at);

-- -----------------------------------------------------------------------------
-- Monitoring alerts (deduped)
-- -----------------------------------------------------------------------------

create table if not exists public.monitoring_alerts (
  id                 uuid primary key default gen_random_uuid(),
  alert_key          text not null,
  severity           text not null,
  status             text not null default 'open',
  summary            text,
  details            jsonb not null default '{}'::jsonb,
  tenant_id          uuid,
  first_triggered_at timestamptz not null default now(),
  last_triggered_at  timestamptz not null default now(),
  last_notified_at   timestamptz,
  occurrences        integer not null default 1,
  resolved_at        timestamptz,
  created_at         timestamptz not null default now(),
  updated_at         timestamptz not null default now()
);

create index if not exists monitoring_alerts_key_open_idx
  on public.monitoring_alerts (alert_key)
  where resolved_at is null;

create index if not exists monitoring_alerts_status_idx
  on public.monitoring_alerts (status, severity, last_triggered_at);

-- -----------------------------------------------------------------------------
-- Raw system error log
-- -----------------------------------------------------------------------------

create table if not exists public.system_errors (
  id            uuid primary key default gen_random_uuid(),
  source        text,
  service       text,
  component     text,
  severity      text,
  error_code    text,
  error_message text,
  metadata      jsonb not null default '{}'::jsonb,
  created_at    timestamptz not null default now()
);

create index if not exists system_errors_created_idx
  on public.system_errors (created_at desc);

create index if not exists system_errors_service_idx
  on public.system_errors (service, created_at desc);

-- -----------------------------------------------------------------------------
-- Workflow outputs (read by digest / sweeper)
-- -----------------------------------------------------------------------------

create table if not exists public.workflow_outputs (
  id            uuid primary key default gen_random_uuid(),
  workflow_id   uuid not null references public.orchestrator_workflow_runs(id) on delete cascade,
  workflow_type text,
  summary       text,
  status        text,
  payload       jsonb not null default '{}'::jsonb,
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now()
);

create index if not exists workflow_outputs_workflow_idx
  on public.workflow_outputs (workflow_id);

-- -----------------------------------------------------------------------------
-- System digests (written by research worker daily digest)
-- -----------------------------------------------------------------------------

create table if not exists public.system_digests (
  id           uuid primary key default gen_random_uuid(),
  digest_type  text not null,
  window_hours integer,
  summary      text,
  payload      jsonb not null default '{}'::jsonb,
  created_at   timestamptz not null default now()
);

create index if not exists system_digests_type_created_idx
  on public.system_digests (digest_type, created_at desc);

-- -----------------------------------------------------------------------------
-- Schema cache reload for PostgREST
-- -----------------------------------------------------------------------------

select pg_notify('pgrst', 'reload schema');
