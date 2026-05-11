-- =============================================================================
-- Autonomous project intake + run orchestration
-- Target project: ygqglfbhxiumqdisauar
--
-- Purpose:
-- 1. Allow Nexus to accept structured autonomous project requests
-- 2. Store the generated cross-worker execution plan
-- 3. Track project-level execution state separately from worker heartbeats
-- =============================================================================

create extension if not exists "pgcrypto";

create table if not exists public.autonomous_projects (
  id               uuid primary key default gen_random_uuid(),
  project_name     text not null,
  project_type     text not null,
  objective        text not null,
  owner            text,
  priority         text not null default 'normal',
  autonomy_mode    text not null default 'assisted',
  status           text not null default 'planned',
  deadline         timestamptz,
  constraints      jsonb not null default '[]'::jsonb,
  deliverables     jsonb not null default '[]'::jsonb,
  requested_roles  jsonb not null default '[]'::jsonb,
  metadata         jsonb not null default '{}'::jsonb,
  approved_by      text,
  approved_at      timestamptz,
  completed_at     timestamptz,
  created_at       timestamptz not null default now(),
  updated_at       timestamptz not null default now()
);

create index if not exists autonomous_projects_status_idx
  on public.autonomous_projects (status, priority, created_at desc);

create index if not exists autonomous_projects_type_idx
  on public.autonomous_projects (project_type, created_at desc);

create table if not exists public.autonomous_project_runs (
  id                uuid primary key default gen_random_uuid(),
  project_id        uuid not null references public.autonomous_projects(id) on delete cascade,
  run_order         integer not null,
  stage_name        text not null,
  role_id           text not null,
  job_type          text not null,
  status            text not null default 'planned',
  approval_required boolean not null default false,
  rationale         text,
  payload           jsonb not null default '{}'::jsonb,
  execution_result  jsonb not null default '{}'::jsonb,
  started_at        timestamptz,
  completed_at      timestamptz,
  created_at        timestamptz not null default now(),
  updated_at        timestamptz not null default now()
);

create index if not exists autonomous_project_runs_project_idx
  on public.autonomous_project_runs (project_id, run_order);

create index if not exists autonomous_project_runs_status_idx
  on public.autonomous_project_runs (status, created_at desc);

select pg_notify('pgrst', 'reload schema');
