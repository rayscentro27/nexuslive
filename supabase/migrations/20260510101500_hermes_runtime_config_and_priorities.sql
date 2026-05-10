-- Hermes runtime configuration + operational priorities

create table if not exists public.hermes_runtime_config (
  id bigserial primary key,
  config_key text not null unique,
  config_value jsonb not null default '{}'::jsonb,
  enabled boolean not null default true,
  updated_by text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists hermes_runtime_config_enabled_idx
  on public.hermes_runtime_config(enabled, updated_at desc);

create table if not exists public.operational_priorities (
  id bigserial primary key,
  title text not null,
  category text not null default 'operations',
  status text not null default 'active',
  priority_score integer not null default 50,
  blocked_reason text,
  owner text,
  source_ref text,
  metadata jsonb not null default '{}'::jsonb,
  updated_by text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists operational_priorities_status_score_idx
  on public.operational_priorities(status, priority_score desc, updated_at desc);

insert into public.hermes_runtime_config(config_key, config_value, enabled, updated_by)
values
  ('hermes_personality', '{"style":"operational_chief_of_staff","tone":"concise_calm_direct","internal_first":true,"long_output_channel":"email_report"}'::jsonb, true, 'migration'),
  ('hermes_telegram_rules', '{"mode":"travel_mode","max_chars":700,"allow_long":false}'::jsonb, true, 'migration'),
  ('hermes_confidence_rules', '{"stale_hours":72,"labels":["INTERNAL_CONFIRMED","INTERNAL_PARTIAL","INTERNAL_STALE","GENERAL_FALLBACK","NEEDS_RAYMOND_DECISION"]}'::jsonb, true, 'migration')
on conflict (config_key) do nothing;
