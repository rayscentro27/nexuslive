-- Nexus AI Task Dispatch System

create table if not exists ai_task_queue (
  id uuid primary key default gen_random_uuid(),
  created_by text not null,
  source text not null check (source in ('telegram','dashboard','system')),
  assigned_worker text not null,
  task_type text not null,
  priority text not null default 'medium',
  title text not null,
  instructions text not null,
  status text not null default 'queued' check (status in ('queued','assigned','running','waiting_review','completed','failed','rejected','paused')),
  created_at timestamptz not null default now(),
  started_at timestamptz,
  completed_at timestamptz,
  requires_approval boolean not null default false,
  repo_target text,
  estimated_scope text,
  result_summary text,
  error_summary text
);

create index if not exists idx_ai_task_queue_status_created on ai_task_queue(status, created_at desc);
create index if not exists idx_ai_task_queue_worker_status on ai_task_queue(assigned_worker, status, created_at desc);

create table if not exists ai_task_workers (
  worker_id text primary key,
  role text not null,
  specialties jsonb not null default '[]'::jsonb,
  capabilities jsonb not null default '[]'::jsonb,
  allowed_actions jsonb not null default '[]'::jsonb,
  active boolean not null default true,
  health_status text not null default 'ready',
  concurrency_limit integer not null default 1,
  runtime_environment text not null default 'local_cli',
  updated_at timestamptz not null default now()
);

create table if not exists ai_task_results (
  id uuid primary key default gen_random_uuid(),
  task_id uuid not null references ai_task_queue(id) on delete cascade,
  worker_id text not null,
  status text not null,
  result_summary text,
  error_summary text,
  created_at timestamptz not null default now()
);

create index if not exists idx_ai_task_results_task_created on ai_task_results(task_id, created_at desc);

create table if not exists ai_task_activity_log (
  id uuid primary key default gen_random_uuid(),
  task_id uuid references ai_task_queue(id) on delete set null,
  worker_id text,
  activity_type text not null,
  activity_summary text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists idx_ai_task_activity_task_created on ai_task_activity_log(task_id, created_at desc);
