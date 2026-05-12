create table if not exists public.user_subscriptions (
  id                      uuid primary key default gen_random_uuid(),
  user_id                 uuid not null references auth.users(id) on delete cascade,
  email                   text,
  plan                    text not null default 'free',
  status                  text not null default 'active',
  stripe_customer_id      text,
  stripe_subscription_id  text,
  stripe_price_id         text,
  current_period_start    timestamptz,
  current_period_end      timestamptz,
  created_at              timestamptz not null default now(),
  updated_at              timestamptz not null default now(),
  constraint user_subscriptions_user_id_key unique (user_id)
);

alter table public.user_subscriptions enable row level security;

create policy "Users can read own subscription"
  on public.user_subscriptions for select
  using (auth.uid() = user_id);

-- Service role bypasses RLS so the webhook can write without policy restrictions
