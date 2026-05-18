-- Nexus AI Workforce Infrastructure
-- Extends existing ai_task_queue / provider_health systems with:
-- agent_capabilities, nexus_skills, nexus_cli_tools,
-- agent_dispatch_tasks, agent_dispatch_subtasks, agent_dispatch_events,
-- human_approval_requests
-- Note: ai_task_queue, ai_task_workers, provider_health already exist.

-- ── agent_capabilities ────────────────────────────────────────────────────────
-- Registry of all available agents and what they can do.

create table if not exists public.agent_capabilities (
  id                   uuid primary key default gen_random_uuid(),
  agent_key            text unique not null,
  display_name         text not null,
  agent_type           text not null,
  description          text,
  supported_task_types text[] not null default '{}',
  allowed_risk_levels  text[] not null default '{"low"}',
  requires_approval    boolean not null default true,
  workspace_scope      text default 'nexus-ai',
  is_enabled           boolean not null default true,
  priority             integer not null default 100,
  created_at           timestamptz not null default now(),
  updated_at           timestamptz not null default now()
);

alter table public.agent_capabilities enable row level security;
create policy "Admins manage agent capabilities" on public.agent_capabilities
  for all using (auth.jwt() ->> 'role' in ('admin', 'super_admin')
    or auth.jwt() ->> 'email' = current_setting('app.admin_email', true));
create policy "Service role: agent capabilities" on public.agent_capabilities
  for all to service_role using (true);

-- ── nexus_skills ─────────────────────────────────────────────────────────────
-- Skill library — prompt templates and allowed actions for each skill.

create table if not exists public.nexus_skills (
  id               uuid primary key default gen_random_uuid(),
  skill_key        text unique not null,
  display_name     text not null,
  category         text not null,
  description      text,
  version          text not null default '1.0',
  prompt_template  text,
  required_inputs  jsonb not null default '{}',
  allowed_actions  text[] not null default '{}',
  risk_level       text not null default 'low',
  requires_approval boolean not null default true,
  success_count    integer not null default 0,
  failure_count    integer not null default 0,
  last_used_at     timestamptz,
  is_enabled       boolean not null default true,
  created_at       timestamptz not null default now(),
  updated_at       timestamptz not null default now()
);

alter table public.nexus_skills enable row level security;
create policy "Admins manage skills" on public.nexus_skills
  for all using (auth.jwt() ->> 'role' in ('admin', 'super_admin')
    or auth.jwt() ->> 'email' = current_setting('app.admin_email', true));
create policy "Service role: skills" on public.nexus_skills
  for all to service_role using (true);

-- ── nexus_cli_tools ───────────────────────────────────────────────────────────
-- Registry of available CLI commands agents can invoke.

create table if not exists public.nexus_cli_tools (
  id                   uuid primary key default gen_random_uuid(),
  cli_key              text unique not null,
  command_name         text not null,
  description          text,
  supported_task_types text[] not null default '{}',
  expected_output      text,
  risk_level           text not null default 'low',
  requires_approval    boolean not null default true,
  is_enabled           boolean not null default true,
  created_at           timestamptz not null default now(),
  updated_at           timestamptz not null default now()
);

alter table public.nexus_cli_tools enable row level security;
create policy "Admins manage CLI tools" on public.nexus_cli_tools
  for all using (auth.jwt() ->> 'role' in ('admin', 'super_admin')
    or auth.jwt() ->> 'email' = current_setting('app.admin_email', true));
create policy "Service role: CLI tools" on public.nexus_cli_tools
  for all to service_role using (true);

-- ── agent_dispatch_tasks ──────────────────────────────────────────────────────
-- High-level tasks submitted by Ray/admin that get planned and dispatched.

create table if not exists public.agent_dispatch_tasks (
  id                   uuid primary key default gen_random_uuid(),
  source               text not null default 'telegram',
  requested_by         uuid,
  original_prompt      text not null,
  normalized_goal      text,
  task_type            text,
  risk_level           text not null default 'low',
  status               text not null default 'received'
    check (status in ('received','needs_clarification','planned','running',
                      'blocked','awaiting_approval','completed','failed')),
  clarification_question text,
  approved_by          uuid,
  approval_required    boolean not null default false,
  selected_strategy    jsonb,
  final_summary        text,
  created_at           timestamptz not null default now(),
  updated_at           timestamptz not null default now(),
  completed_at         timestamptz
);

create index if not exists agent_dispatch_tasks_status_idx
  on public.agent_dispatch_tasks(status, created_at desc);

alter table public.agent_dispatch_tasks enable row level security;
create policy "Admins manage dispatch tasks" on public.agent_dispatch_tasks
  for all using (auth.jwt() ->> 'role' in ('admin', 'super_admin')
    or auth.jwt() ->> 'email' = current_setting('app.admin_email', true));
create policy "Service role: dispatch tasks" on public.agent_dispatch_tasks
  for all to service_role using (true);

-- ── agent_dispatch_subtasks ───────────────────────────────────────────────────

create table if not exists public.agent_dispatch_subtasks (
  id                    uuid primary key default gen_random_uuid(),
  parent_task_id        uuid not null references public.agent_dispatch_tasks(id) on delete cascade,
  title                 text not null,
  description           text,
  task_type             text,
  assigned_agent_key    text,
  assigned_skill_key    text,
  assigned_cli_key      text,
  assigned_provider_key text,
  status                text not null default 'queued'
    check (status in ('queued','running','completed','failed','blocked','skipped')),
  dependency_ids        uuid[] not null default '{}',
  output_summary        text,
  output_ref            jsonb,
  error_message         text,
  created_at            timestamptz not null default now(),
  updated_at            timestamptz not null default now(),
  completed_at          timestamptz
);

create index if not exists agent_dispatch_subtasks_parent_idx
  on public.agent_dispatch_subtasks(parent_task_id, status);

alter table public.agent_dispatch_subtasks enable row level security;
create policy "Admins manage subtasks" on public.agent_dispatch_subtasks
  for all using (auth.jwt() ->> 'role' in ('admin', 'super_admin')
    or auth.jwt() ->> 'email' = current_setting('app.admin_email', true));
create policy "Service role: subtasks" on public.agent_dispatch_subtasks
  for all to service_role using (true);

-- ── agent_dispatch_events ─────────────────────────────────────────────────────

create table if not exists public.agent_dispatch_events (
  id          uuid primary key default gen_random_uuid(),
  task_id     uuid not null references public.agent_dispatch_tasks(id) on delete cascade,
  subtask_id  uuid references public.agent_dispatch_subtasks(id) on delete set null,
  event_type  text not null,
  message     text,
  metadata    jsonb not null default '{}',
  created_at  timestamptz not null default now()
);

create index if not exists agent_dispatch_events_task_idx
  on public.agent_dispatch_events(task_id, created_at desc);

alter table public.agent_dispatch_events enable row level security;
create policy "Admins read dispatch events" on public.agent_dispatch_events
  for all using (auth.jwt() ->> 'role' in ('admin', 'super_admin')
    or auth.jwt() ->> 'email' = current_setting('app.admin_email', true));
create policy "Service role: dispatch events" on public.agent_dispatch_events
  for all to service_role using (true);

-- ── human_approval_requests ───────────────────────────────────────────────────

create table if not exists public.human_approval_requests (
  id               uuid primary key default gen_random_uuid(),
  task_id          uuid references public.agent_dispatch_tasks(id) on delete cascade,
  subtask_id       uuid references public.agent_dispatch_subtasks(id) on delete set null,
  approval_type    text not null,
  risk_level       text not null default 'medium',
  request_summary  text not null,
  proposed_action  jsonb,
  status           text not null default 'pending'
    check (status in ('pending','approved','rejected','expired')),
  reviewed_by      uuid,
  reviewed_at      timestamptz,
  created_at       timestamptz not null default now()
);

create index if not exists human_approval_requests_status_idx
  on public.human_approval_requests(status, created_at desc);

alter table public.human_approval_requests enable row level security;
create policy "Admins manage approvals" on public.human_approval_requests
  for all using (auth.jwt() ->> 'role' in ('admin', 'super_admin')
    or auth.jwt() ->> 'email' = current_setting('app.admin_email', true));
create policy "Service role: approvals" on public.human_approval_requests
  for all to service_role using (true);

-- ── Seed: agent_capabilities ──────────────────────────────────────────────────

insert into public.agent_capabilities
  (agent_key, display_name, agent_type, description, supported_task_types, allowed_risk_levels, requires_approval, priority)
values
  ('hermes_orchestrator', 'Hermes', 'hermes', 'Chief operations AI — coordinates all agents', array['coordination','analysis','routing','research_synthesis'], array['low','medium','high'], false, 1),
  ('claude_code', 'Claude Code', 'claude_code', 'Advanced coding and architecture tasks', array['coding','refactor','debugging','architecture','testing'], array['low','medium'], true, 10),
  ('codex_cli', 'Codex CLI', 'codex', 'Fast coding via Codex CLI', array['coding','scaffolding','utility_scripts'], array['low','medium'], true, 20),
  ('deepseek_tui', 'DeepSeek TUI', 'deepseek_tui', 'Sandboxed low-risk coding', array['coding','prototyping'], array['low'], true, 30),
  ('pyrunner_worker', 'Python Runner', 'pyrunner', 'Scheduled Python utility jobs', array['data_processing','reporting','ingestion'], array['low','medium'], true, 40),
  ('nexus_launch_engine', 'Launch Engine', 'launch_engine', 'Site/staging generation workflows', array['launch','staging','seo'], array['medium'], true, 50),
  ('nexus_comms_engine', 'Comms Engine', 'comms_engine', 'Draft emails/messages — never auto-send', array['drafting','outreach','followup'], array['low','medium'], true, 60),
  ('qa_worker', 'QA Worker', 'qa_worker', 'Test generation and review', array['testing','qa','validation'], array['low'], true, 70),
  ('research_worker', 'Research Worker', 'research_worker', 'Domain research and analysis', array['research','analysis','summarization'], array['low','medium'], true, 80),
  ('ops_monitor_worker', 'Ops Monitor', 'ops_monitor_worker', 'Infrastructure and health monitoring', array['monitoring','health_check','alerting'], array['low'], false, 90)
on conflict (agent_key) do update set updated_at = now();

-- ── Seed: nexus_skills ────────────────────────────────────────────────────────

insert into public.nexus_skills
  (skill_key, display_name, category, description, allowed_actions, risk_level, requires_approval)
values
  ('funding_readiness_v1', 'Funding Readiness', 'funding', 'Score and improve funding readiness factors', array['analyze','recommend'], 'low', false),
  ('credit_dispute_generator_v1', 'Credit Dispute Generator', 'credit', 'Generate credit dispute letters', array['draft','analyze'], 'medium', true),
  ('grant_research_v1', 'Grant Research', 'grants', 'Find and score grant opportunities', array['research','analyze','recommend'], 'low', false),
  ('business_launch_site_v1', 'Business Launch Site', 'launch', 'Generate business landing page', array['draft','generate'], 'medium', true),
  ('seo_cluster_builder_v1', 'SEO Cluster Builder', 'seo', 'Build topical SEO content clusters', array['research','draft'], 'low', true),
  ('ceo_digest_v1', 'CEO Digest', 'ops', 'Generate CEO operational summary', array['analyze','summarize'], 'low', false),
  ('client_followup_draft_v1', 'Client Follow-up Draft', 'comms', 'Draft client follow-up messages', array['draft'], 'medium', true),
  ('worker_health_audit_v1', 'Worker Health Audit', 'ops', 'Audit all active workers and services', array['monitor','analyze'], 'low', false),
  ('utility_python_job_v1', 'Utility Python Job', 'ops', 'Run scheduled Python utility scripts', array['execute'], 'medium', true),
  ('qa_review_v1', 'QA Review', 'qa', 'Review code/output for quality and safety', array['analyze','validate'], 'low', false)
on conflict (skill_key) do update set updated_at = now();

-- ── Seed: nexus_cli_tools ─────────────────────────────────────────────────────

insert into public.nexus_cli_tools
  (cli_key, command_name, description, supported_task_types, expected_output, risk_level, requires_approval)
values
  ('nexus_health', 'nexus health', 'System health check across all workers and providers', array['monitoring','health_check'], 'JSON health status', 'low', false),
  ('nexus_report', 'nexus report', 'Generate CEO or operational digest', array['reporting','summarization'], 'Markdown/JSON report', 'low', false),
  ('nexus_worker', 'nexus worker', 'Worker status, pause, resume commands', array['monitoring','management'], 'JSON worker status', 'low', true),
  ('nexus_funding', 'nexus funding', 'Funding readiness and strategy refresh', array['funding','analysis'], 'JSON readiness score', 'medium', true),
  ('nexus_comms', 'nexus comms', 'List pending communication drafts', array['comms','drafting'], 'JSON draft list', 'low', true),
  ('nexus_launch', 'nexus launch', 'Staging launch plan generation', array['launch','staging'], 'JSON launch plan', 'medium', true),
  ('nexus_grants', 'nexus grants', 'Grant catalog scan and eligibility check', array['grants','research'], 'JSON grant opportunities', 'low', false),
  ('nexus_seo', 'nexus seo', 'SEO cluster and keyword analysis', array['seo','marketing'], 'JSON SEO recommendations', 'low', true)
on conflict (cli_key) do update set updated_at = now();
