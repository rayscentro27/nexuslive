-- User Intelligence + Operational Analytics Migration
-- Adds: user_intelligence, analytics_events, transcript_queue tables

-- ── user_intelligence: unified AI-scored user profile ────────────────────────

create table if not exists public.user_intelligence (
  id                    uuid primary key default gen_random_uuid(),
  user_id               uuid not null references auth.users(id) on delete cascade,

  -- composite intelligence scores (0-100)
  user_intelligence_score   integer not null default 0,
  engagement_score          integer not null default 0,
  readiness_score           integer not null default 0,
  operational_health        text not null default 'unknown',
    -- green | yellow | red | unknown

  -- component scores
  onboarding_score          integer not null default 0,
  funding_readiness_score   integer not null default 0,
  trading_activation_score  integer not null default 0,
  credit_health_score       integer not null default 0,
  grant_engagement_score    integer not null default 0,
  business_setup_score      integer not null default 0,

  -- journey state
  onboarding_complete       boolean not null default false,
  onboarding_step           text,
  last_active_feature       text,
  features_activated        text[] not null default '{}',
  days_since_signup         integer not null default 0,
  session_count             integer not null default 0,
  total_time_minutes        integer not null default 0,

  -- next best action
  next_best_action          text,
  next_best_action_priority text default 'medium',
    -- critical | high | medium | low
  next_best_action_category text,
    -- onboarding | funding | credit | trading | grants | business

  -- scoring metadata
  scored_at                 timestamptz not null default now(),
  scoring_version           text not null default 'v1',
  raw_signals               jsonb not null default '{}'::jsonb,

  created_at                timestamptz not null default now(),
  updated_at                timestamptz not null default now(),

  constraint user_intelligence_user_id_unique unique (user_id)
);

create index if not exists user_intelligence_score_idx
  on public.user_intelligence(user_intelligence_score desc, updated_at desc);

create index if not exists user_intelligence_health_idx
  on public.user_intelligence(operational_health, updated_at desc);

alter table public.user_intelligence enable row level security;

do $$
begin
  if not exists (
    select 1 from pg_policies
    where tablename = 'user_intelligence' and policyname = 'Users can read own intelligence'
  ) then
    create policy "Users can read own intelligence"
      on public.user_intelligence for select
      using (auth.uid() = user_id);
  end if;
end $$;

do $$
begin
  if not exists (
    select 1 from pg_policies
    where tablename = 'user_intelligence' and policyname = 'Admins can manage user intelligence'
  ) then
    create policy "Admins can manage user intelligence"
      on public.user_intelligence for all
      using (
        auth.jwt() ->> 'role' in ('admin', 'super_admin')
        or auth.jwt() ->> 'email' = current_setting('app.admin_email', true)
      );
  end if;
end $$;

-- ── analytics_events: platform behavioral event stream ───────────────────────

create table if not exists public.analytics_events (
  id           uuid primary key default gen_random_uuid(),
  user_id      uuid references auth.users(id) on delete set null,
  session_id   text,

  event_type   text not null,
    -- page_view | feature_click | onboarding_step | cta_click |
    -- grant_viewed | opportunity_viewed | trade_started | invite_sent |
    -- funding_applied | credit_checked | strategy_approved | error
  event_name   text not null,
  feature      text,
    -- dashboard | funding | trading | grants | credit | onboarding |
    -- referral | settings | admin | chat
  page         text,
  value        numeric,
  duration_ms  integer,
  metadata     jsonb not null default '{}'::jsonb,
  created_at   timestamptz not null default now()
);

create index if not exists analytics_events_user_idx
  on public.analytics_events(user_id, created_at desc);

create index if not exists analytics_events_type_idx
  on public.analytics_events(event_type, event_name, created_at desc);

create index if not exists analytics_events_feature_idx
  on public.analytics_events(feature, created_at desc);

alter table public.analytics_events enable row level security;

do $$
begin
  if not exists (
    select 1 from pg_policies
    where tablename = 'analytics_events' and policyname = 'Users can insert own events'
  ) then
    create policy "Users can insert own events"
      on public.analytics_events for insert
      with check (auth.uid() = user_id or user_id is null);
  end if;
end $$;

do $$
begin
  if not exists (
    select 1 from pg_policies
    where tablename = 'analytics_events' and policyname = 'Admins can read all events'
  ) then
    create policy "Admins can read all events"
      on public.analytics_events for select
      using (
        auth.jwt() ->> 'role' in ('admin', 'super_admin')
        or auth.jwt() ->> 'email' = current_setting('app.admin_email', true)
      );
  end if;
end $$;

-- ── transcript_queue: ingestion pipeline for transcripts ─────────────────────

create table if not exists public.transcript_queue (
  id              uuid primary key default gen_random_uuid(),
  title           text not null,
  source_url      text,
  source_type     text not null default 'youtube',
    -- youtube | podcast | webinar | notebooklm | upload | manual
  raw_content     text not null,
  cleaned_content text,
  chunk_count     integer not null default 0,

  -- classification
  domain          text not null default 'operations',
    -- trading | grants | business_opportunities | funding | credit | operations | marketing
  tags            text[] not null default '{}',

  -- quality signals
  quality_score   integer,
  quality_label   text,
    -- high | medium | low | reject
  duplicate_of    uuid references public.transcript_queue(id),

  -- extraction state
  status          text not null default 'pending',
    -- pending | processing | strategies_extracted | knowledge_added | rejected | archived
  strategies_extracted integer not null default 0,
  knowledge_items_added integer not null default 0,
  extraction_notes text,

  -- tracking
  submitted_by    text,
  reviewed_by     text,
  approved_at     timestamptz,
  processed_at    timestamptz,
  metadata        jsonb not null default '{}'::jsonb,

  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now()
);

create index if not exists transcript_queue_status_idx
  on public.transcript_queue(status, created_at desc);

create index if not exists transcript_queue_domain_idx
  on public.transcript_queue(domain, quality_label, created_at desc);

alter table public.transcript_queue enable row level security;

do $$
begin
  if not exists (
    select 1 from pg_policies
    where tablename = 'transcript_queue' and policyname = 'Admins can manage transcript queue'
  ) then
    create policy "Admins can manage transcript queue"
      on public.transcript_queue for all
      using (
        auth.jwt() ->> 'role' in ('admin', 'super_admin')
        or auth.jwt() ->> 'email' = current_setting('app.admin_email', true)
      );
  end if;
end $$;

-- ── provider_health: AI provider uptime + rate-limit tracking ────────────────

create table if not exists public.provider_health (
  id              uuid primary key default gen_random_uuid(),
  provider_name   text not null,
    -- claude_cli | codex | opencode | ollama | openrouter | groq | notebooklm
  status          text not null default 'unknown',
    -- healthy | degraded | rate_limited | down | unknown
  last_checked_at timestamptz not null default now(),
  last_healthy_at timestamptz,
  error_count_1h  integer not null default 0,
  rate_limit_hits integer not null default 0,
  avg_latency_ms  integer,
  notes           text,
  metadata        jsonb not null default '{}'::jsonb,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now(),

  constraint provider_health_name_unique unique (provider_name)
);

alter table public.provider_health enable row level security;

do $$
begin
  if not exists (
    select 1 from pg_policies
    where tablename = 'provider_health' and policyname = 'Admins can manage provider health'
  ) then
    create policy "Admins can manage provider health"
      on public.provider_health for all
      using (
        auth.jwt() ->> 'role' in ('admin', 'super_admin')
        or auth.jwt() ->> 'email' = current_setting('app.admin_email', true)
      );
  end if;
end $$;

-- Seed known providers
insert into public.provider_health (provider_name, status, notes) values
  ('claude_cli',   'unknown', 'Claude Code CLI — primary coding agent'),
  ('codex',        'unknown', 'OpenAI Codex CLI'),
  ('opencode',     'unknown', 'OpenCode CLI agent'),
  ('ollama',       'unknown', 'Local Ollama — qwen3:8b, llama3.2:3b'),
  ('openrouter',   'unknown', 'OpenRouter multi-model gateway'),
  ('groq',         'unknown', 'Groq fast inference — Llama 3'),
  ('notebooklm',   'unknown', 'Google NotebookLM research workspace')
on conflict (provider_name) do nothing;
