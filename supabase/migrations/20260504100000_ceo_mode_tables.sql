-- CEO Mode tables: aggregation, auto-fix, leads, revenue, launch, comms, approvals

-- Part 1: hermes_aggregates — classified event log replacing raw noise
create table if not exists public.hermes_aggregates (
  id                uuid primary key default gen_random_uuid(),
  event_source      text not null,                        -- which agent/worker generated it
  event_type        text not null,                        -- raw event name
  classification    text not null default 'informational', -- critical_alert | actionable | informational | suppress
  raw_event         jsonb,
  aggregated_summary text,
  alert_sent        boolean not null default false,
  alert_cooldown_until timestamptz,
  created_at        timestamptz not null default now()
);

create index if not exists hermes_aggregates_classification_idx on public.hermes_aggregates(classification);
create index if not exists hermes_aggregates_created_at_idx on public.hermes_aggregates(created_at desc);
alter table public.hermes_aggregates enable row level security;
create policy "hermes_aggregates_admin" on public.hermes_aggregates
  for all using (
    exists (select 1 from public.user_profiles where id = auth.uid() and role in ('admin','super_admin'))
  );

-- Part 4: hermes_autofix_actions — log of automated remediation actions
create table if not exists public.hermes_autofix_actions (
  id           uuid primary key default gen_random_uuid(),
  issue_type   text not null,
  description  text not null,
  action_taken text not null,
  classification text not null default 'safe',   -- safe | needs_owner_approval
  status       text not null default 'pending',  -- pending | completed | failed | awaiting_approval
  outcome      text,
  error_detail text,
  created_at   timestamptz not null default now(),
  completed_at timestamptz
);

create index if not exists hermes_autofix_status_idx on public.hermes_autofix_actions(status);
create index if not exists hermes_autofix_created_at_idx on public.hermes_autofix_actions(created_at desc);
alter table public.hermes_autofix_actions enable row level security;
create policy "hermes_autofix_admin" on public.hermes_autofix_actions
  for all using (
    exists (select 1 from public.user_profiles where id = auth.uid() and role in ('admin','super_admin'))
  );

-- Part 5: leads — 10-stage funnel
create table if not exists public.leads (
  id               uuid primary key default gen_random_uuid(),
  source           text not null default 'organic',   -- organic | referral | ad | content | partner | manual
  name             text,
  email            text,
  phone            text,
  business_name    text,
  status           text not null default 'new',       -- new | contacted | qualified | proposal | negotiation | won | lost | cold
  lead_score       integer not null default 0,        -- 0-100
  estimated_value  numeric(12,2),
  notes            text,
  last_contacted_at timestamptz,
  next_followup_at  timestamptz,
  converted_at      timestamptz,
  assigned_to       text,                             -- agent name or 'owner'
  created_at       timestamptz not null default now(),
  updated_at       timestamptz not null default now()
);

create index if not exists leads_status_idx on public.leads(status);
create index if not exists leads_next_followup_idx on public.leads(next_followup_at);
create index if not exists leads_created_at_idx on public.leads(created_at desc);
alter table public.leads enable row level security;
create policy "leads_admin" on public.leads
  for all using (
    exists (select 1 from public.user_profiles where id = auth.uid() and role in ('admin','super_admin'))
  );

-- Part 6: revenue_events — 12 event types
create table if not exists public.revenue_events (
  id          uuid primary key default gen_random_uuid(),
  event_type  text not null,   -- subscription_start | upgrade | downgrade | churn | grant_payout |
                               --   loan_funded | commission_earned | concierge_fee | referral_bonus |
                               --   partner_deal | content_sale | training_sale
  amount      numeric(14,2) not null default 0,
  currency    text not null default 'USD',
  client_id   uuid references auth.users(id) on delete set null,
  lead_id     uuid references public.leads(id) on delete set null,
  description text,
  notes       text,
  period_month text,           -- YYYY-MM for MRR tracking
  created_at  timestamptz not null default now()
);

create index if not exists revenue_events_type_idx on public.revenue_events(event_type);
create index if not exists revenue_events_period_idx on public.revenue_events(period_month);
create index if not exists revenue_events_created_at_idx on public.revenue_events(created_at desc);
alter table public.revenue_events enable row level security;
create policy "revenue_events_admin" on public.revenue_events
  for all using (
    exists (select 1 from public.user_profiles where id = auth.uid() and role in ('admin','super_admin'))
  );

-- Part 7: launch_metrics — daily/weekly KPI tracking
create table if not exists public.launch_metrics (
  id           uuid primary key default gen_random_uuid(),
  metric_name  text not null,
  metric_value numeric(14,4) not null default 0,
  target_value numeric(14,4),
  unit         text,           -- count | usd | pct | score
  period       text not null default 'daily',  -- daily | weekly | monthly
  period_label text,           -- e.g. '2026-05-04' or '2026-W18'
  notes        text,
  created_at   timestamptz not null default now()
);

create unique index if not exists launch_metrics_unique_idx on public.launch_metrics(metric_name, period, period_label);
create index if not exists launch_metrics_period_idx on public.launch_metrics(period_label desc);
alter table public.launch_metrics enable row level security;
create policy "launch_metrics_admin" on public.launch_metrics
  for all using (
    exists (select 1 from public.user_profiles where id = auth.uid() and role in ('admin','super_admin'))
  );

-- Part 9: hermes_comms_log — reliable communication delivery tracking
create table if not exists public.hermes_comms_log (
  id              uuid primary key default gen_random_uuid(),
  channel         text not null,       -- telegram | email | sms
  recipient       text not null,
  subject         text,
  body_preview    text,
  idempotency_key text unique,         -- prevent duplicate sends
  status          text not null default 'pending',  -- pending | sent | failed | retrying
  retry_count     integer not null default 0,
  max_retries     integer not null default 3,
  last_attempt_at timestamptz,
  next_retry_at   timestamptz,
  sent_at         timestamptz,
  error_detail    text,
  created_at      timestamptz not null default now()
);

create index if not exists hermes_comms_log_status_idx on public.hermes_comms_log(status);
create index if not exists hermes_comms_log_channel_idx on public.hermes_comms_log(channel);
create index if not exists hermes_comms_log_created_at_idx on public.hermes_comms_log(created_at desc);
alter table public.hermes_comms_log enable row level security;
create policy "hermes_comms_log_admin" on public.hermes_comms_log
  for all using (
    exists (select 1 from public.user_profiles where id = auth.uid() and role in ('admin','super_admin'))
  );

-- Part 11: owner_approval_queue — actions requiring owner sign-off
create table if not exists public.owner_approval_queue (
  id            uuid primary key default gen_random_uuid(),
  action_type   text not null,         -- e.g. bulk_outreach | budget_change | schema_change | content_publish
  description   text not null,
  payload       jsonb,
  requested_by  text not null,         -- agent name
  priority      text not null default 'normal',  -- urgent | normal | low
  status        text not null default 'pending', -- pending | approved | rejected | needs_edits
  review_notes  text,
  expires_at    timestamptz,
  created_at    timestamptz not null default now(),
  reviewed_at   timestamptz
);

create index if not exists owner_approval_status_idx on public.owner_approval_queue(status);
create index if not exists owner_approval_priority_idx on public.owner_approval_queue(priority, created_at desc);
alter table public.owner_approval_queue enable row level security;
create policy "owner_approval_admin" on public.owner_approval_queue
  for all using (
    exists (select 1 from public.user_profiles where id = auth.uid() and role in ('admin','super_admin'))
  );
