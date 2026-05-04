-- grants_catalog: public grant opportunities shown in GrantsFinder
create table if not exists public.grants_catalog (
  id            uuid primary key default gen_random_uuid(),
  title         text not null,
  description   text,
  grantor       text,
  category      text not null default 'federal',  -- federal | state | local | nonprofit | business
  amount_min    integer,
  amount_max    integer,
  deadline      date,
  official_url  text,
  eligibility   text,
  states        text[],
  is_active     boolean not null default true,
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now()
);

alter table public.grants_catalog enable row level security;

-- All authenticated users can read active grants
create policy "grants_catalog_read" on public.grants_catalog
  for select using (is_active = true);

-- Admins can manage grants catalog
create policy "grants_catalog_admin" on public.grants_catalog
  for all using (
    exists (
      select 1 from public.user_profiles
      where id = auth.uid() and role in ('admin', 'super_admin')
    )
  );

-- grant_review_requests: user-submitted grant research requests reviewed by admins
create table if not exists public.grant_review_requests (
  id            uuid primary key default gen_random_uuid(),
  user_id       uuid not null references auth.users(id) on delete cascade,
  keyword       text,
  business_type text,
  city          text,
  state         text,
  grant_url     text,
  notes         text,
  status        text not null default 'pending',  -- pending | in_review | completed | rejected
  response      text,
  completed_at  timestamptz,
  created_at    timestamptz not null default now()
);

alter table public.grant_review_requests enable row level security;

-- Users can read and insert their own requests
create policy "grant_requests_user_read" on public.grant_review_requests
  for select using (auth.uid() = user_id);

create policy "grant_requests_user_insert" on public.grant_review_requests
  for insert with check (auth.uid() = user_id);

-- Admins can manage all requests
create policy "grant_requests_admin" on public.grant_review_requests
  for all using (
    exists (
      select 1 from public.user_profiles
      where id = auth.uid() and role in ('admin', 'super_admin')
    )
  );

-- Seed initial grants catalog
insert into public.grants_catalog (title, description, grantor, category, amount_min, amount_max, eligibility, official_url)
values
  ('Women Entrepreneurs Fund',
   'Funding for women-owned small businesses to start, grow, and expand.',
   'SBA', 'federal', 5000, 25000,
   'Women-owned businesses with less than 500 employees',
   'https://www.sba.gov/funding-programs/grants'),

  ('Small Business Growth Grant',
   'For businesses under 5 years old looking to scale operations.',
   'NASE', 'nonprofit', 10000, 50000,
   'Businesses operating for fewer than 5 years',
   'https://www.nase.org/benefits/business-grants'),

  ('Minority Business Initiative Grant',
   'Minority-owned business development and expansion fund.',
   'MBDA', 'federal', 15000, 15000,
   'Minority-owned businesses in underserved communities',
   'https://www.mbda.gov'),

  ('InnovateTech Startup Grant',
   'For tech startups in STEM sectors pursuing innovation.',
   'NSF', 'federal', 25000, 100000,
   'STEM-focused startups with proof of concept',
   'https://www.nsf.gov/funding/'),

  ('Community Development Block Grant',
   'HUD-funded grant for businesses in low-income communities.',
   'HUD', 'federal', 50000, 500000,
   'Businesses serving low-to-moderate income communities',
   'https://www.hud.gov/program_offices/comm_planning/cdbg'),

  ('Rural Business Development Grant',
   'USDA grant for small businesses in rural areas.',
   'USDA', 'federal', 10000, 500000,
   'Small businesses and cooperatives in rural areas',
   'https://www.rd.usda.gov/programs-services/business-programs/rural-business-development-grants'),

  ('Economic Injury Disaster Loan (EIDL)',
   'Low-interest federal disaster loans for working capital.',
   'SBA', 'federal', 1000, 2000000,
   'Small businesses impacted by economic injury',
   'https://www.sba.gov/funding-programs/loans/covid-19-relief-options/eidl'),

  ('IFundWomen Universal Grant',
   'Crowdfunding-matched grant for women entrepreneurs.',
   'IFundWomen', 'nonprofit', 5000, 10000,
   'Women-owned businesses at any stage',
   'https://ifundwomen.com/grants')
on conflict do nothing;
