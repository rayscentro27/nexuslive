-- AI usage log: one row per API call
create table if not exists public.ai_usage_log (
  id              bigserial primary key,
  created_at      timestamptz not null default now(),
  caller          text not null,
  model           text not null default 'hermes',
  provider        text not null default 'hermes',
  prompt_tokens   int  not null default 0,
  completion_tokens int not null default 0,
  total_tokens    int  not null default 0,
  prompt_chars    int  not null default 0,
  response_chars  int  not null default 0,
  latency_ms      int  not null default 0,
  cost_usd        numeric(12,8) not null default 0,
  status          text not null default 'ok',
  meta            jsonb default '{}'
);

create index if not exists ai_usage_log_created_at_idx on public.ai_usage_log (created_at desc);
create index if not exists ai_usage_log_caller_idx     on public.ai_usage_log (caller);
create index if not exists ai_usage_log_model_idx      on public.ai_usage_log (model);

-- Monthly budget config: one row per provider
create table if not exists public.ai_token_budget (
  id              serial primary key,
  provider        text not null unique,
  monthly_limit_usd  numeric(10,4) not null default 50.0,
  alert_pct       int  not null default 80,
  current_month   text not null default to_char(now(), 'YYYY-MM'),
  month_spend_usd numeric(12,8) not null default 0,
  last_synced_at  timestamptz,
  updated_at      timestamptz not null default now()
);

insert into public.ai_token_budget (provider, monthly_limit_usd, alert_pct)
values
  ('openrouter', 50.00, 80),
  ('anthropic',  20.00, 80),
  ('gemini',     10.00, 80),
  ('hermes',      0.00, 80)
on conflict (provider) do nothing;
