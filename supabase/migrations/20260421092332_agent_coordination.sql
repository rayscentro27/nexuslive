-- Agent Coordination Schema (public schema, coord_ prefix)

-- Activity log: every agent logs what files/changes it made
create table if not exists public.coord_activity (
  id           bigserial primary key,
  agent        text not null,        -- 'claude-code', 'codex', 'hermes'
  action       text not null,        -- 'created', 'modified', 'deleted', 'deployed', 'note'
  file_path    text,
  description  text not null,
  metadata     jsonb default '{}',
  created_at   timestamptz default now()
);

-- Task queue: user posts instructions; agents pick up their tasks
create table if not exists public.coord_tasks (
  id           bigserial primary key,
  assigned_to  text not null,        -- 'claude-code', 'codex', 'all'
  posted_by    text default 'user',
  title        text not null,
  description  text,
  priority     text default 'normal',
  status       text default 'pending',
  claimed_at   timestamptz,
  completed_at timestamptz,
  created_at   timestamptz default now()
);

-- Shared context: key/value state both agents should know
create table if not exists public.coord_context (
  id           bigserial primary key,
  key          text not null unique,
  value        text not null,
  updated_by   text not null,
  updated_at   timestamptz default now()
);

create index if not exists coord_activity_agent_idx on public.coord_activity (agent, created_at desc);
create index if not exists coord_tasks_agent_idx on public.coord_tasks (assigned_to, status);

-- Seed initial context
insert into public.coord_context (key, value, updated_by) values
  ('active_project', 'nexus-ai', 'system'),
  ('coordination_version', '1.0', 'system')
on conflict (key) do nothing;
