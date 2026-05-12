create table if not exists public.subscription_plans (
  id text primary key,
  name text not null,
  price numeric(10,2) not null default 0,
  commission_rate numeric(5,2) not null default 0,
  stripe_price_id text not null default '',
  features text[] not null default '{}',
  active boolean not null default true,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

alter table public.subscription_plans enable row level security;

create policy "Anyone can read subscription plans"
  on public.subscription_plans for select
  using (true);

create policy "Admins can manage subscription plans"
  on public.subscription_plans for all
  using (auth.jwt() ->> 'role' = 'admin' or auth.jwt() ->> 'email' like '%@nexuslive%');

insert into public.subscription_plans (id, name, price, commission_rate, stripe_price_id, features, active)
values
  ('free', 'Free', 0, 0, '',
   array['Basic Business Setup Guide','Limited Document Storage (500MB)','Public Grants Search','Community Support','Basic Credit Tips'],
   true),
  ('pro', 'Pro', 50, 10, 'price_1TPSP62MIMiohBBF1w0j3cUQ',
   array['Full Business Formation Suite','Unlimited Document Storage','AI-Powered Grant Matching','Priority Advisor Access','Advanced Credit Analysis','Trading Lab Access'],
   true),
  ('elite', 'Elite', 100, 10, 'price_1TPSPR2MIMiohBBFBuoyvOzu',
   array['Dedicated Capital Strategist','Custom Funding Roadmaps','Concierge Business Setup','Multi-user Management','API Access & Integrations','White-label Portal Options'],
   true)
on conflict (id) do update set
  stripe_price_id = excluded.stripe_price_id,
  price = excluded.price,
  commission_rate = excluded.commission_rate,
  features = excluded.features,
  updated_at = now();
