-- Client Readiness Engine — Intake and Assisted Execution Layer
-- Migration: 20260429200000_client_readiness_engine.sql

-- ── Master readiness profile (aggregate scores + status) ──────────────────

create table if not exists public.client_readiness_profiles (
  id                  uuid primary key default gen_random_uuid(),
  tenant_id           uuid,
  user_id             uuid not null,
  overall_score       numeric(5,2) default 0,
  score_breakdown     jsonb default '{}',
  completion_pct      numeric(5,4) default 0,
  grant_ready         boolean default false,
  trading_eligible    boolean default false,
  created_at          timestamptz default now(),
  updated_at          timestamptz default now()
);

create index if not exists crp_user_idx on public.client_readiness_profiles (user_id, tenant_id);
create unique index if not exists crp_user_tenant_uniq on public.client_readiness_profiles (user_id, coalesce(tenant_id, '00000000-0000-0000-0000-000000000000'::uuid));

-- ── Business Foundation Profile ────────────────────────────────────────────

create table if not exists public.business_foundation_profiles (
  id                           uuid primary key default gen_random_uuid(),
  tenant_id                    uuid,
  user_id                      uuid not null,
  legal_business_name          text,
  entity_type                  text,
  state_formed                 text,
  ein_status                   text,
  business_address_status      text,
  business_phone_status        text,
  business_email_domain_status text,
  website_status               text,
  naics_code                   text,
  industry                     text,
  time_in_business_months      integer,
  monthly_revenue              numeric(14,2),
  employee_count               integer,
  business_bank_account_status text,
  created_at                   timestamptz default now(),
  updated_at                   timestamptz default now()
);

create index if not exists bfp_user_idx on public.business_foundation_profiles (user_id, tenant_id);
create unique index if not exists bfp_user_tenant_uniq on public.business_foundation_profiles (user_id, coalesce(tenant_id, '00000000-0000-0000-0000-000000000000'::uuid));

-- ── Credit Profile Inputs ─────────────────────────────────────────────────

create table if not exists public.credit_profile_inputs (
  id                           uuid primary key default gen_random_uuid(),
  tenant_id                    uuid,
  user_id                      uuid not null,
  personal_credit_score_estimate integer,
  experian_score               integer,
  equifax_score                integer,
  transunion_score             integer,
  credit_utilization           numeric(5,4),
  inquiries_count              integer,
  negative_items_count         integer,
  age_of_credit_history        numeric(6,1),
  credit_report_uploaded       boolean default false,
  credit_report_file_url       text,
  duns_status                  text,
  paydex_score                 integer,
  business_tradelines_count    integer,
  created_at                   timestamptz default now(),
  updated_at                   timestamptz default now()
);

create index if not exists cpi_user_idx on public.credit_profile_inputs (user_id, tenant_id);
create unique index if not exists cpi_user_tenant_uniq on public.credit_profile_inputs (user_id, coalesce(tenant_id, '00000000-0000-0000-0000-000000000000'::uuid));

-- ── Banking Setup Profiles ────────────────────────────────────────────────

create table if not exists public.banking_setup_profiles (
  id                    uuid primary key default gen_random_uuid(),
  tenant_id             uuid,
  user_id               uuid not null,
  current_business_bank text,
  account_age_months    integer,
  average_balance       numeric(14,2),
  monthly_deposits      numeric(14,2),
  nsf_count             integer default 0,
  target_banks          jsonb default '[]',
  target_credit_unions  jsonb default '[]',
  proof_url             text,
  verification_status   text default 'unverified',
  created_at            timestamptz default now(),
  updated_at            timestamptz default now()
);

create index if not exists bsp_user_idx on public.banking_setup_profiles (user_id, tenant_id);
create unique index if not exists bsp_user_tenant_uniq on public.banking_setup_profiles (user_id, coalesce(tenant_id, '00000000-0000-0000-0000-000000000000'::uuid));

-- ── Grant Eligibility Profiles ────────────────────────────────────────────
-- Note: any protected-class or demographic fields are optional, user-provided only,
-- and used solely for grant matching purposes as disclosed to the user.

create table if not exists public.grant_eligibility_profiles (
  id                          uuid primary key default gen_random_uuid(),
  tenant_id                   uuid,
  user_id                     uuid not null,
  business_location_state     text,
  business_location_city      text,
  industry                    text,
  revenue_range               text,
  employee_count              integer,
  business_stage              text,
  use_of_funds                text,
  certifications              jsonb default '[]',
  optional_eligibility_tags   jsonb default '[]',
  grant_documents_uploaded    boolean default false,
  notes                       text,
  created_at                  timestamptz default now(),
  updated_at                  timestamptz default now()
);

comment on column public.grant_eligibility_profiles.optional_eligibility_tags is
  'Optional, user-provided eligibility tags (e.g. minority-owned, veteran-owned). Used only for grant matching as disclosed. Never required.';

create index if not exists gep_user_idx on public.grant_eligibility_profiles (user_id, tenant_id);
create unique index if not exists gep_user_tenant_uniq on public.grant_eligibility_profiles (user_id, coalesce(tenant_id, '00000000-0000-0000-0000-000000000000'::uuid));

-- ── Trading Eligibility Profiles ──────────────────────────────────────────

create table if not exists public.trading_eligibility_profiles (
  id                        uuid primary key default gen_random_uuid(),
  tenant_id                 uuid,
  user_id                   uuid not null,
  capital_reserve           numeric(14,2),
  risk_tolerance            text,
  education_video_completed boolean default false,
  disclaimer_accepted       boolean default false,
  paper_trading_completed   boolean default false,
  broker_connected          boolean default false,
  preferred_markets         jsonb default '[]',
  eligibility_status        text default 'locked',
  created_at                timestamptz default now(),
  updated_at                timestamptz default now()
);

create index if not exists tep_user_idx on public.trading_eligibility_profiles (user_id, tenant_id);
create unique index if not exists tep_user_tenant_uniq on public.trading_eligibility_profiles (user_id, coalesce(tenant_id, '00000000-0000-0000-0000-000000000000'::uuid));

-- ── Readiness Tasks ───────────────────────────────────────────────────────

create table if not exists public.readiness_tasks (
  id               uuid primary key default gen_random_uuid(),
  tenant_id        uuid,
  user_id          uuid not null,
  category         text not null,
  task_type        text not null,
  task_title       text not null,
  task_description text,
  guidance_content jsonb default '{}',
  execution_tools  jsonb default '[]',
  education_notes  text,
  status           text default 'pending',
  priority         text default 'medium',
  unlocks_feature  text,
  due_date         date,
  created_at       timestamptz default now(),
  updated_at       timestamptz default now()
);

create index if not exists rt_user_idx on public.readiness_tasks (user_id, tenant_id, status);
create index if not exists rt_priority_idx on public.readiness_tasks (user_id, priority, status);
