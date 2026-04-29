create extension if not exists pgcrypto;

create table if not exists public.credit_approval_results (
  id uuid primary key default gen_random_uuid(),
  source_name text,
  source_url text,
  card_name text,
  bank_name text,
  product_type text,
  approved boolean,
  credit_limit numeric,
  credit_score integer,
  annual_income numeric,
  state text,
  bureau text,
  credit_history_age text,
  application_date date,
  raw_payload jsonb default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists public.card_approval_patterns (
  id uuid primary key default gen_random_uuid(),
  card_name text,
  bank_name text,
  product_type text,
  score_bucket text,
  income_bucket text,
  history_bucket text,
  bureau text,
  state text,
  sample_size integer default 0,
  approval_rate numeric,
  avg_limit numeric,
  median_limit numeric,
  min_score integer,
  max_limit numeric,
  confidence_score numeric,
  last_seen_at timestamptz,
  updated_at timestamptz not null default now()
);

create table if not exists public.lending_institutions (
  id uuid primary key default gen_random_uuid(),
  institution_name text,
  institution_type text,
  product_types text[] default '{}',
  min_score integer,
  max_funding numeric,
  geo_restrictions text,
  membership_required boolean default false,
  business_checking_available boolean default false,
  business_credit_card_available boolean default false,
  business_loc_available boolean default false,
  sba_available boolean default false,
  relationship_notes text,
  recommended_prep_steps jsonb default '[]'::jsonb,
  source_url text,
  created_at timestamptz not null default now()
);

create table if not exists public.user_business_score_inputs (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid,
  user_id uuid,
  duns_status text,
  paydex_score numeric,
  experian_business_score numeric,
  equifax_business_score numeric,
  nav_grade text,
  reporting_tradelines_count integer,
  business_bank_account_age_months integer,
  monthly_deposits numeric,
  average_balance numeric,
  nsf_count integer,
  revenue_consistency text,
  uploaded_report_url text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.banking_relationships (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid,
  user_id uuid,
  institution_name text,
  account_type text,
  account_open_date date,
  account_age_days integer,
  average_balance numeric,
  monthly_deposits numeric,
  deposit_consistency text,
  prior_products text[] default '{}',
  target_for_funding boolean not null default false,
  relationship_score numeric,
  verification_status text not null default 'self_reported',
  proof_url text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.funding_recommendations (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid,
  user_id uuid,
  tier integer,
  recommendation_type text,
  institution_name text,
  product_name text,
  product_type text,
  approval_score numeric,
  approval_score_without_relationship numeric,
  relationship_boost numeric,
  expected_limit_low numeric,
  expected_limit_high numeric,
  confidence_level text,
  reason text,
  prep_steps jsonb default '[]'::jsonb,
  evidence_summary jsonb default '{}'::jsonb,
  disclaimer text not null default 'Results vary. Approval is determined by the lender and is not guaranteed.',
  status text not null default 'recommended',
  created_at timestamptz not null default now()
);

create table if not exists public.application_results (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid,
  user_id uuid,
  recommendation_id uuid references public.funding_recommendations(id) on delete set null,
  result_status text,
  approved_amount numeric,
  proof_url text,
  verified boolean not null default false,
  created_at timestamptz not null default now()
);

create table if not exists public.success_fee_invoices (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid,
  user_id uuid,
  application_result_id uuid references public.application_results(id) on delete cascade,
  funding_amount numeric,
  fee_rate numeric not null default 0.10,
  invoice_amount numeric,
  status text not null default 'pending',
  created_at timestamptz not null default now()
);

create table if not exists public.referral_earnings (
  id uuid primary key default gen_random_uuid(),
  referrer_user_id uuid,
  referred_user_id uuid,
  application_result_id uuid references public.application_results(id) on delete cascade,
  funding_amount numeric,
  platform_fee numeric,
  referral_rate numeric not null default 0.02,
  referral_amount numeric,
  status text not null default 'pending',
  created_at timestamptz not null default now()
);

create table if not exists public.user_tier_progress (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid,
  user_id uuid,
  current_tier integer not null default 1,
  tier_1_status text,
  tier_2_status text,
  tier_3_status text,
  reported_tier_1_results_count integer not null default 0,
  verified_results_count integer not null default 0,
  business_readiness_score numeric,
  relationship_score numeric,
  last_recalculated_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists credit_approval_results_card_idx
  on public.credit_approval_results (card_name, bank_name, application_date desc);
create index if not exists card_approval_patterns_card_idx
  on public.card_approval_patterns (card_name, bank_name, product_type);
create index if not exists lending_institutions_type_idx
  on public.lending_institutions (institution_type);
create index if not exists user_business_score_inputs_user_idx
  on public.user_business_score_inputs (tenant_id, user_id, created_at desc);
create index if not exists banking_relationships_user_idx
  on public.banking_relationships (tenant_id, user_id, created_at desc);
create index if not exists funding_recommendations_user_idx
  on public.funding_recommendations (tenant_id, user_id, created_at desc);
create index if not exists application_results_user_idx
  on public.application_results (tenant_id, user_id, created_at desc);
create index if not exists success_fee_invoices_user_idx
  on public.success_fee_invoices (tenant_id, user_id, created_at desc);
create index if not exists referral_earnings_referrer_idx
  on public.referral_earnings (referrer_user_id, created_at desc);
create unique index if not exists user_tier_progress_user_unique
  on public.user_tier_progress (tenant_id, user_id);

drop trigger if exists trg_user_business_score_inputs_touch on public.user_business_score_inputs;
create trigger trg_user_business_score_inputs_touch
before update on public.user_business_score_inputs
for each row execute function public.touch_updated_at();

drop trigger if exists trg_banking_relationships_touch on public.banking_relationships;
create trigger trg_banking_relationships_touch
before update on public.banking_relationships
for each row execute function public.touch_updated_at();

drop trigger if exists trg_card_approval_patterns_touch on public.card_approval_patterns;
create trigger trg_card_approval_patterns_touch
before update on public.card_approval_patterns
for each row execute function public.touch_updated_at();

drop trigger if exists trg_user_tier_progress_touch on public.user_tier_progress;
create trigger trg_user_tier_progress_touch
before update on public.user_tier_progress
for each row execute function public.touch_updated_at();
