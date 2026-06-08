-- Nexus System Map (Phase 1) — additive only.
--
-- Reuses existing tables where possible:
--   * AI providers      -> existing  model_providers
--   * AI model routing   -> existing  model_routing_rules
--   * CLI registry       -> existing  nexus_cli_tools (extended below)
--   * Agent capabilities -> existing  agent_capabilities
--
-- New tables (no existing equivalent):
--   * nexus_system_repos          — installed git repositories
--   * nexus_system_processes      — running OS processes / services
--   * nexus_task_routing_rules    — task_type -> tool/repo routing (broader than
--                                    model_routing_rules, which only routes AI models)
--
-- All tables: RLS enabled, admin-only access (consistent with nexus_os_* tables).
-- DO NOT run db reset. This migration is additive and idempotent.

-- ─────────────────────────────────────────────────────────────────────────────
-- 1. nexus_system_repos
-- ─────────────────────────────────────────────────────────────────────────────
create table if not exists public.nexus_system_repos (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  path text not null unique,
  remote_url text,
  branch text,
  latest_commit text,
  status text,                       -- dirty/clean summary
  purpose text,
  module text,
  active_state text,                 -- active | legacy | experimental | unknown
  risk_level text,                   -- low | review | secrets-present
  safe_for_hermes boolean default false,
  language text,
  package_manager text,
  untracked_count integer default 0,
  metadata jsonb default '{}'::jsonb,
  scanned_at timestamptz default now()
);

-- ─────────────────────────────────────────────────────────────────────────────
-- 2. nexus_system_processes
-- ─────────────────────────────────────────────────────────────────────────────
create table if not exists public.nexus_system_processes (
  id uuid primary key default gen_random_uuid(),
  name text not null unique,
  command text,
  pid integer,
  port text,
  status text,                       -- running | stopped | failed | unknown
  repo_path text,
  purpose text,
  log_path text,
  restart_command text,
  can_restart boolean default false, -- Hermes may auto-restart only if true
  approval_required boolean default true,
  risk_level text,                   -- low | medium | high
  hermes_can_query boolean default true,
  metadata jsonb default '{}'::jsonb,
  scanned_at timestamptz default now()
);

-- ─────────────────────────────────────────────────────────────────────────────
-- 3. nexus_task_routing_rules
-- ─────────────────────────────────────────────────────────────────────────────
create table if not exists public.nexus_task_routing_rules (
  id uuid primary key default gen_random_uuid(),
  task_type text not null unique,
  preferred_tool text,
  fallback_tool text,
  preferred_repo text,
  required_context text,
  safety_gate text,
  approval_required boolean default true,
  notes text,
  active boolean default true,
  metadata jsonb default '{}'::jsonb,
  updated_at timestamptz default now()
);

-- ─────────────────────────────────────────────────────────────────────────────
-- 4. Extend existing nexus_cli_tools with system-map fields (additive, idempotent)
-- ─────────────────────────────────────────────────────────────────────────────
alter table public.nexus_cli_tools add column if not exists version text;
alter table public.nexus_cli_tools add column if not exists install_path text;
alter table public.nexus_cli_tools add column if not exists installed boolean default true;
alter table public.nexus_cli_tools add column if not exists health_status text;
alter table public.nexus_cli_tools add column if not exists network_risk text;
alter table public.nexus_cli_tools add column if not exists cost_risk text;
alter table public.nexus_cli_tools add column if not exists can_run_locally boolean;
alter table public.nexus_cli_tools add column if not exists last_scanned_at timestamptz;

-- ─────────────────────────────────────────────────────────────────────────────
-- RLS — admin-only, consistent with nexus_os_* tables
-- ─────────────────────────────────────────────────────────────────────────────
alter table public.nexus_system_repos       enable row level security;
alter table public.nexus_system_processes   enable row level security;
alter table public.nexus_task_routing_rules enable row level security;

do $$
declare
  t text;
begin
  foreach t in array array['nexus_system_repos','nexus_system_processes','nexus_task_routing_rules']
  loop
    execute format('drop policy if exists "%s_admin_all" on public.%I;', t, t);
    execute format($f$
      create policy "%s_admin_all" on public.%I
        for all
        using (
          exists (
            select 1 from public.user_profiles up
            where up.id = auth.uid() and up.role in ('admin','super_admin')
          )
        )
        with check (
          exists (
            select 1 from public.user_profiles up
            where up.id = auth.uid() and up.role in ('admin','super_admin')
          )
        );
    $f$, t, t);
  end loop;
end $$;

-- Helpful indexes
create index if not exists idx_nexus_system_repos_module on public.nexus_system_repos(module);
create index if not exists idx_nexus_system_processes_status on public.nexus_system_processes(status);
create index if not exists idx_nexus_task_routing_active on public.nexus_task_routing_rules(active);
