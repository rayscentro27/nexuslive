-- Browser task queue: one row per autonomous browser task
create table if not exists public.browser_tasks (
  id              bigserial primary key,
  created_at      timestamptz not null default now(),
  task_type       text not null,             -- oracle_check|stripe_check|nexuslive_check|supabase_check|open
  payload         jsonb default '{}',        -- task-specific params (url, task description, etc.)
  status          text not null default 'pending',  -- pending|running|done|error
  requested_by    text not null default 'system',
  started_at      timestamptz,
  finished_at     timestamptz,
  result          jsonb,                     -- full result dict from worker
  error           text,
  screenshot_url  text                       -- future: S3/Supabase storage URL
);

create index if not exists browser_tasks_status_idx on public.browser_tasks (status, created_at);
create index if not exists browser_tasks_type_idx   on public.browser_tasks (task_type);

-- Telegram bot can insert tasks via RPC; service role needed for reads
alter table public.browser_tasks enable row level security;

create policy "service role full access"
  on public.browser_tasks
  using (true)
  with check (true);
