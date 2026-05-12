-- Intelligence Quality Layer Migration
-- Adds: knowledge quality metadata, memory domains, freshness, source citations,
--       strategy versions, backtest runs, paper trading persistence, social content queue

-- ── knowledge_items: unified knowledge brain records ──────────────────────────

create table if not exists public.knowledge_items (
  id              uuid primary key default gen_random_uuid(),
  domain          text not null default 'operations',
    -- trading | grants | business_opportunities | funding | credit |
    -- onboarding | marketing | operations | social | system
  title           text not null,
  content         text not null,
  source_url      text,
  source_notebook text,
  source_type     text default 'email',
    -- email | notebooklm | manual | transcript | report | web
  quality_score   integer,
  quality_label   text,
    -- high | medium | low | reject
  freshness_status text default 'unknown',
    -- fresh | acceptable | stale | expired | unknown
  stale_after_days integer,
  expires_at      timestamptz,
  last_verified_at timestamptz,
  source_checked_at timestamptz,
  status          text not null default 'pending_review',
    -- pending_review | approved | rejected | archived
  reviewed_by     text,
  approved_at     timestamptz,
  review_notes    text,
  dry_run         boolean not null default false,
  metadata        jsonb not null default '{}'::jsonb,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now()
);

create index if not exists knowledge_items_domain_status_idx
  on public.knowledge_items(domain, status, updated_at desc);

create index if not exists knowledge_items_quality_idx
  on public.knowledge_items(quality_label, quality_score desc);

alter table public.knowledge_items enable row level security;

create policy "Admins can manage knowledge items"
  on public.knowledge_items for all
  using (
    auth.jwt() ->> 'role' in ('admin', 'super_admin')
    or auth.jwt() ->> 'email' = current_setting('app.admin_email', true)
  );

create policy "Users can read approved knowledge"
  on public.knowledge_items for select
  using (status = 'approved' and dry_run = false);

-- ── strategy_versions: version-controlled trading strategies ──────────────────

create table if not exists public.strategy_versions (
  id              uuid primary key default gen_random_uuid(),
  strategy_id     text not null,
  version         integer not null default 1,
  strategy_name   text not null,
  asset_class     text,
  timeframe       text,
  parameters      jsonb not null default '{}'::jsonb,
    -- entry_logic, exit_logic, stop_loss, take_profit, session, etc.
  risk_profile    jsonb not null default '{}'::jsonb,
  ai_confidence   integer,
  win_rate        numeric(5,2),
  profit_factor   numeric(5,2),
  max_drawdown_pct numeric(5,2),
  expectancy      numeric(8,2),
  backtest_runs   integer default 0,
  paper_runs      integer default 0,
  is_active       boolean not null default false,
  is_archived     boolean not null default false,
  edge_health     text default 'unknown',
    -- stable | warning | critical | unknown
  changed_by      text,
  change_reason   text,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now(),
  unique(strategy_id, version)
);

create index if not exists strategy_versions_active_idx
  on public.strategy_versions(strategy_id, is_active, version desc);

alter table public.strategy_versions enable row level security;

create policy "Admins can manage strategies"
  on public.strategy_versions for all
  using (auth.jwt() ->> 'role' in ('admin', 'super_admin'));

create policy "Users can read active strategies"
  on public.strategy_versions for select
  using (is_active = true and is_archived = false);

-- ── backtest_runs: persisted backtesting results ──────────────────────────────

create table if not exists public.backtest_runs (
  id              uuid primary key default gen_random_uuid(),
  strategy_id     text not null,
  strategy_version integer,
  dataset_name    text,
  dataset_source  text,
    -- tradingview_csv | oanda_practice | synthetic | manual_json
  start_date      date,
  end_date        date,
  total_trades    integer,
  winning_trades  integer,
  losing_trades   integer,
  win_rate        numeric(5,2),
  profit_factor   numeric(5,2),
  expectancy      numeric(8,2),
  max_drawdown_pct numeric(5,2),
  total_pnl       numeric(12,2),
  sharpe_ratio    numeric(5,2),
  equity_curve    jsonb,
    -- array of {date, balance} objects
  session_breakdown jsonb,
    -- {london: {win_rate, trades}, ny_open: {...}, ...}
  parameter_set   jsonb,
  meets_min_criteria boolean default false,
  run_by          text,
  notes           text,
  created_at      timestamptz not null default now()
);

create index if not exists backtest_runs_strategy_idx
  on public.backtest_runs(strategy_id, created_at desc);

alter table public.backtest_runs enable row level security;

create policy "Admins can manage backtest runs"
  on public.backtest_runs for all
  using (auth.jwt() ->> 'role' in ('admin', 'super_admin'));

create policy "Users can read backtest runs"
  on public.backtest_runs for select
  using (true);

-- ── paper_trade_runs: persisted paper trading records ────────────────────────
-- Table may already exist (created in earlier session); we extend it safely.

create table if not exists public.paper_trade_runs (
  id              uuid primary key default gen_random_uuid(),
  strategy_id     text not null,
  market          text not null default 'unknown',
  direction       text not null default 'long',
  entry_price     numeric(14,6) not null default 0,
  stop_loss       numeric(14,6) not null default 0,
  take_profit     numeric(14,6) not null default 0,
  status          text not null default 'open',
  dry_run         boolean not null default true,
  created_at      timestamptz not null default now()
);

-- Add columns that may not exist yet (safe for both new and existing tables)
do $$
begin
  if not exists (select 1 from information_schema.columns where table_schema='public' and table_name='paper_trade_runs' and column_name='account_id') then
    alter table public.paper_trade_runs add column account_id uuid;
  end if;
  if not exists (select 1 from information_schema.columns where table_schema='public' and table_name='paper_trade_runs' and column_name='strategy_version') then
    alter table public.paper_trade_runs add column strategy_version integer;
  end if;
  if not exists (select 1 from information_schema.columns where table_schema='public' and table_name='paper_trade_runs' and column_name='strategy_name') then
    alter table public.paper_trade_runs add column strategy_name text;
  end if;
  if not exists (select 1 from information_schema.columns where table_schema='public' and table_name='paper_trade_runs' and column_name='exit_price') then
    alter table public.paper_trade_runs add column exit_price numeric(14,6);
  end if;
  if not exists (select 1 from information_schema.columns where table_schema='public' and table_name='paper_trade_runs' and column_name='size_lots') then
    alter table public.paper_trade_runs add column size_lots numeric(8,4) not null default 0.01;
  end if;
  if not exists (select 1 from information_schema.columns where table_schema='public' and table_name='paper_trade_runs' and column_name='pnl_pips') then
    alter table public.paper_trade_runs add column pnl_pips numeric(8,2);
  end if;
  if not exists (select 1 from information_schema.columns where table_schema='public' and table_name='paper_trade_runs' and column_name='pnl_usd') then
    alter table public.paper_trade_runs add column pnl_usd numeric(10,2);
  end if;
  if not exists (select 1 from information_schema.columns where table_schema='public' and table_name='paper_trade_runs' and column_name='fees_usd') then
    alter table public.paper_trade_runs add column fees_usd numeric(8,2) default 0;
  end if;
  if not exists (select 1 from information_schema.columns where table_schema='public' and table_name='paper_trade_runs' and column_name='slippage_pips') then
    alter table public.paper_trade_runs add column slippage_pips numeric(6,2) default 0;
  end if;
  if not exists (select 1 from information_schema.columns where table_schema='public' and table_name='paper_trade_runs' and column_name='exit_reason') then
    alter table public.paper_trade_runs add column exit_reason text;
  end if;
  if not exists (select 1 from information_schema.columns where table_schema='public' and table_name='paper_trade_runs' and column_name='session') then
    alter table public.paper_trade_runs add column session text;
  end if;
  if not exists (select 1 from information_schema.columns where table_schema='public' and table_name='paper_trade_runs' and column_name='ai_confidence') then
    alter table public.paper_trade_runs add column ai_confidence integer;
  end if;
  if not exists (select 1 from information_schema.columns where table_schema='public' and table_name='paper_trade_runs' and column_name='hermes_review') then
    alter table public.paper_trade_runs add column hermes_review jsonb;
  end if;
  if not exists (select 1 from information_schema.columns where table_schema='public' and table_name='paper_trade_runs' and column_name='journal_notes') then
    alter table public.paper_trade_runs add column journal_notes text;
  end if;
  if not exists (select 1 from information_schema.columns where table_schema='public' and table_name='paper_trade_runs' and column_name='opened_at') then
    alter table public.paper_trade_runs add column opened_at timestamptz not null default now();
  end if;
  if not exists (select 1 from information_schema.columns where table_schema='public' and table_name='paper_trade_runs' and column_name='closed_at') then
    alter table public.paper_trade_runs add column closed_at timestamptz;
  end if;
  if not exists (select 1 from information_schema.columns where table_schema='public' and table_name='paper_trade_runs' and column_name='updated_at') then
    alter table public.paper_trade_runs add column updated_at timestamptz not null default now();
  end if;
end $$;

-- Create indexes only when the column exists
do $$
begin
  if exists (select 1 from information_schema.columns where table_schema='public' and table_name='paper_trade_runs' and column_name='opened_at') then
    if not exists (select 1 from pg_indexes where tablename='paper_trade_runs' and indexname='paper_trade_runs_status_idx') then
      execute 'create index paper_trade_runs_status_idx on public.paper_trade_runs(status, opened_at desc)';
    end if;
    if not exists (select 1 from pg_indexes where tablename='paper_trade_runs' and indexname='paper_trade_runs_strategy_idx') then
      execute 'create index paper_trade_runs_strategy_idx on public.paper_trade_runs(strategy_id, opened_at desc)';
    end if;
  end if;
end $$;

alter table public.paper_trade_runs enable row level security;

do $$
begin
  if not exists (select 1 from pg_policies where tablename='paper_trade_runs' and policyname='Admins can manage paper trades') then
    create policy "Admins can manage paper trades"
      on public.paper_trade_runs for all
      using (auth.jwt() ->> 'role' in ('admin', 'super_admin'));
  end if;
  if not exists (select 1 from pg_policies where tablename='paper_trade_runs' and policyname='Users can read own paper trades') then
    create policy "Users can read own paper trades"
      on public.paper_trade_runs for select
      using (true);
  end if;
end $$;

-- ── social_content_queue: pending social media content for review ─────────────

create table if not exists public.social_content_queue (
  id              uuid primary key default gen_random_uuid(),
  platform        text not null,
    -- facebook | instagram | tiktok | youtube | linkedin | twitter
  content_text    text not null,
  media_url       text,
  hashtags        text[],
  scheduled_at    timestamptz,
  status          text not null default 'draft',
    -- draft | pending_approval | approved | rejected | published | cancelled
  approved_by     text,
  approved_at     timestamptz,
  rejected_reason text,
  published_at    timestamptz,
  generated_by    text,
    -- hermes | operator | manual | ai_employee
  campaign_tag    text,
  notes           text,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now()
);

create index if not exists social_content_status_platform_idx
  on public.social_content_queue(status, platform, scheduled_at);

alter table public.social_content_queue enable row level security;

do $$
begin
  if not exists (select 1 from pg_policies where tablename='social_content_queue' and policyname='Admins can manage social content') then
    create policy "Admins can manage social content"
      on public.social_content_queue for all
      using (auth.jwt() ->> 'role' in ('admin', 'super_admin'));
  end if;
end $$;

-- ── business_opportunities: real business opportunity catalog ─────────────────

create table if not exists public.business_opportunities (
  id                  uuid primary key default gen_random_uuid(),
  name                text not null,
  category            text not null default 'online',
    -- ai-enabled | online | service | government | funding | other
  startup_cost_min    integer default 0,
  startup_cost_max    integer default 0,
  skills_needed       text,
  time_to_launch_weeks integer,
  revenue_potential   text,
    -- low | low-medium | medium | medium-high | high | very-high
  risk_level          text default 'medium',
    -- low | low-medium | medium | medium-high | high
  first_step          text,
  nexus_fit_score     integer,
  source_url          text,
  freshness_status    text default 'fresh',
  is_active           boolean not null default true,
  created_at          timestamptz not null default now(),
  updated_at          timestamptz not null default now()
);

alter table public.business_opportunities enable row level security;

do $$
begin
  if not exists (select 1 from pg_policies where tablename='business_opportunities' and policyname='Anyone can read active opportunities') then
    create policy "Anyone can read active opportunities"
      on public.business_opportunities for select using (true);
  end if;
  if not exists (select 1 from pg_policies where tablename='business_opportunities' and policyname='Admins can manage opportunities') then
    create policy "Admins can manage opportunities"
      on public.business_opportunities for all
      using (auth.jwt() ->> 'role' in ('admin', 'super_admin'));
  end if;
end $$;

-- ── strategies_catalog: public strategy catalog ───────────────────────────────

create table if not exists public.strategies_catalog (
  id              uuid primary key default gen_random_uuid(),
  strategy_id     text not null unique,
  name            text not null,
  asset_class     text,
  timeframe       text,
  risk_level      text,
  ai_confidence   integer,
  backtest_win_rate numeric(5,2),
  max_drawdown_pct numeric(5,2),
  best_session    text,
  demo_ready      boolean default false,
  backtest_ready  boolean default false,
  paper_ready     boolean default false,
  edge_health     text default 'unknown',
  source_type     text default 'transcript',
    -- transcript | backtested | paper-tested | demo-only
  is_active       boolean default true,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now()
);

alter table public.strategies_catalog enable row level security;

do $$
begin
  if not exists (select 1 from pg_policies where tablename='strategies_catalog' and policyname='Anyone can read active strategies') then
    create policy "Anyone can read active strategies"
      on public.strategies_catalog for select using (true);
  end if;
  if not exists (select 1 from pg_policies where tablename='strategies_catalog' and policyname='Admins can manage strategies catalog') then
    create policy "Admins can manage strategies catalog"
      on public.strategies_catalog for all
      using (auth.jwt() ->> 'role' in ('admin', 'super_admin'));
  end if;
end $$;

-- Seed strategies_catalog with transcript-derived strategies
insert into public.strategies_catalog (strategy_id, name, asset_class, timeframe, risk_level, ai_confidence, backtest_win_rate, max_drawdown_pct, best_session, demo_ready, backtest_ready, paper_ready, edge_health, source_type)
values
  ('london_breakout', 'London Breakout', 'FOREX', '15m', 'medium', 71, 68, 8, 'London', true, true, true, 'stable', 'transcript'),
  ('spy_trend', 'SPY Trend Continuation', 'Equities', '5m', 'medium', 64, 61, 10, 'NY Open', true, true, true, 'stable', 'transcript'),
  ('btc_structure', 'BTC/ETH Trend Structure', 'Crypto', '1h', 'high', 58, 55, 15, 'Asia/NY', true, false, true, 'warning', 'transcript'),
  ('purple_cloud', 'Purple Cloud Trend System', 'Multi', '4h', 'low', 74, 72, 6, 'London', true, false, true, 'stable', 'transcript'),
  ('futures_reversal', 'Futures Morning Reversal', 'Futures', '5m', 'high', 61, 57, 12, 'NY Open', true, true, true, 'stable', 'transcript'),
  ('options_watchlist', 'High-IV Options Watchlist', 'Options', 'daily', 'high', 55, 52, 18, 'NY Open', false, false, false, 'warning', 'transcript'),
  ('polymarket_btc', 'Polymarket BTC Late Window', 'Crypto', '5m', 'high', 50, 48, 20, 'Any', false, false, false, 'warning', 'transcript'),
  ('tv_mcp_builder', 'TV MCP Agent Builder', 'Multi', 'any', 'medium', 65, 60, 10, 'Any', true, true, true, 'stable', 'transcript')
on conflict (strategy_id) do update set
  ai_confidence = excluded.ai_confidence,
  edge_health = excluded.edge_health,
  updated_at = now();
