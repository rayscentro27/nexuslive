-- Job lifecycle tracking (start → complete | fail)
create table if not exists public.job_events (
  id           uuid        primary key default gen_random_uuid(),
  worker_name  text        not null,
  job_type     text        not null,
  status       text        not null check (status in ('started','completed','failed')),
  started_at   timestamptz not null default now(),
  completed_at timestamptz,
  duration_ms  int,
  error_msg    text,
  meta         jsonb       not null default '{}',
  created_at   timestamptz not null default now()
);

create index if not exists job_events_worker_name_idx on public.job_events (worker_name);
create index if not exists job_events_status_idx      on public.job_events (status);
create index if not exists job_events_created_at_idx  on public.job_events (created_at desc);

alter table public.job_events enable row level security;
create policy "service role full access" on public.job_events
  using (true) with check (true);

-- Error log for monitoring_worker spike detection
create table if not exists public.error_log (
  id         uuid        primary key default gen_random_uuid(),
  level      text        not null default 'error',
  source     text,
  message    text,
  meta       jsonb       not null default '{}',
  created_at timestamptz not null default now()
);

create index if not exists error_log_level_idx      on public.error_log (level);
create index if not exists error_log_created_at_idx on public.error_log (created_at desc);

alter table public.error_log enable row level security;
create policy "service role full access" on public.error_log
  using (true) with check (true);
