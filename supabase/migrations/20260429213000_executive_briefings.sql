create extension if not exists pgcrypto;

create table if not exists public.executive_briefings (
  id uuid primary key default gen_random_uuid(),
  briefing_type text not null,
  content text not null,
  urgency text default 'medium',
  generated_by text default 'system',
  created_at timestamptz default now()
);

create index if not exists executive_briefings_type_idx
  on public.executive_briefings (briefing_type);

create index if not exists executive_briefings_created_at_idx
  on public.executive_briefings (created_at desc);
