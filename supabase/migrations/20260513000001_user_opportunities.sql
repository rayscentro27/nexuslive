-- User Opportunities Intelligence Migration
-- Scored, vetted opportunity queue per user
-- Safe: read-only analytics write path; controlled by OPPORTUNITY_RESEARCH_WRITES_ENABLED

create table if not exists public.user_opportunities (
  id                    uuid primary key default gen_random_uuid(),
  user_id               uuid not null references auth.users(id) on delete cascade,

  -- Opportunity identity
  opportunity_id        text not null,
  opportunity_name      text not null,
  category              text not null,
    -- grant | loan | credit | sba | microloan | business | trading

  -- Source + discovery
  source                text,
    -- nexus_catalog | user_submitted | research_worker | community
  source_url_hint       text,
    -- category slug for frontend nav (not a raw URL)

  -- Scoring
  feasibility_score     integer not null default 0,
    -- 0–100. How likely this user qualifies today.
  opportunity_score     integer not null default 0,
    -- 0–100. Overall opportunity quality (risk-adjusted value).

  -- Risk/cost signals
  startup_cost          integer not null default 0,
    -- estimated minimum dollars to pursue (0 = free)
  risk_level            text not null default 'unknown',
    -- low | medium | high | unknown
  monetization_type     text,
    -- grant | loan | revenue | equity | service | product

  -- Nexus evaluation state
  nexus_status          text not null default 'pending',
    -- pending | researching | reviewing | tested | validated | flagged | rejected
  tested_by_nexus       boolean not null default false,
  max_amount            integer,

  -- Education content
  educational_summary   text,
    -- Plain-language: why it may work, risks, requirements, effort
  action_steps          jsonb,
    -- [{step, description, link_hint}]
  failure_points        text,
  typical_timeline_days integer,

  -- Worker-generated metadata
  reasons               jsonb,
    -- [{reason text}] — why this user matched
  scored_at             timestamptz,

  created_at            timestamptz not null default now(),
  updated_at            timestamptz not null default now(),

  unique (user_id, opportunity_id)
);

-- ── Indexes ───────────────────────────────────────────────────────────────────

create index if not exists idx_user_opp_user_id
  on public.user_opportunities (user_id);

create index if not exists idx_user_opp_category
  on public.user_opportunities (category);

create index if not exists idx_user_opp_feasibility
  on public.user_opportunities (feasibility_score desc);

create index if not exists idx_user_opp_status
  on public.user_opportunities (nexus_status);

-- ── updated_at trigger ────────────────────────────────────────────────────────

create or replace function public.set_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists user_opportunities_updated_at on public.user_opportunities;
create trigger user_opportunities_updated_at
  before update on public.user_opportunities
  for each row execute function public.set_updated_at();

-- ── Row-Level Security ────────────────────────────────────────────────────────

alter table public.user_opportunities enable row level security;

-- Users may only read their own opportunities
create policy "users_read_own_opportunities"
  on public.user_opportunities
  for select
  using (auth.uid() = user_id);

-- Service role (workers) may write all rows
create policy "service_role_manage_opportunities"
  on public.user_opportunities
  for all
  using (auth.jwt() ->> 'role' = 'service_role');
