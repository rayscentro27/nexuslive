alter table public.funding_recommendations
  add column if not exists last_generated_at timestamptz,
  add column if not exists generation_reason text,
  add column if not exists recommendation_version text default 'v1',
  add column if not exists source_snapshot jsonb default '{}'::jsonb;

create table if not exists public.funding_recommendation_jobs (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid,
  user_id uuid not null,
  reason text not null,
  force boolean not null default false,
  source_table text,
  source_row_id uuid,
  status text not null default 'pending',
  error text,
  created_at timestamptz not null default now(),
  processed_at timestamptz
);

create table if not exists public.funding_recommendation_runs (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid,
  user_id uuid not null,
  reason text not null,
  force boolean not null default false,
  status text not null default 'started',
  recommendations_created integer not null default 0,
  recommendations_updated integer not null default 0,
  recommendations_archived integer not null default 0,
  skipped_reason text,
  error text,
  source_snapshot jsonb default '{}'::jsonb,
  created_at timestamptz not null default now(),
  completed_at timestamptz
);

create index if not exists funding_recommendation_jobs_status_idx
  on public.funding_recommendation_jobs (status, created_at desc);
create index if not exists funding_recommendation_jobs_user_idx
  on public.funding_recommendation_jobs (tenant_id, user_id, created_at desc);
create index if not exists funding_recommendation_runs_user_idx
  on public.funding_recommendation_runs (tenant_id, user_id, created_at desc);
create index if not exists funding_recommendations_active_idx
  on public.funding_recommendations (tenant_id, user_id, status, last_generated_at desc);

create or replace function public.enqueue_funding_recommendation_job(
  p_user_id uuid,
  p_tenant_id uuid,
  p_reason text,
  p_force boolean default false,
  p_source_table text default null,
  p_source_row_id uuid default null
)
returns uuid as $$
declare
  v_job_id uuid;
begin
  insert into public.funding_recommendation_jobs (
    tenant_id, user_id, reason, force, source_table, source_row_id, status
  )
  values (
    p_tenant_id, p_user_id, p_reason, p_force, p_source_table, p_source_row_id, 'pending'
  )
  returning id into v_job_id;
  return v_job_id;
end;
$$ language plpgsql security definer;

create or replace function public.trg_enqueue_funding_recommendation_on_business_input()
returns trigger as $$
begin
  perform public.enqueue_funding_recommendation_job(
    new.user_id,
    new.tenant_id,
    'business_score_inputs_updated',
    false,
    tg_table_name,
    new.id
  );
  return new;
end;
$$ language plpgsql;

create or replace function public.trg_enqueue_funding_recommendation_on_relationship()
returns trigger as $$
begin
  perform public.enqueue_funding_recommendation_job(
    new.user_id,
    new.tenant_id,
    'banking_relationship_updated',
    false,
    tg_table_name,
    new.id
  );
  return new;
end;
$$ language plpgsql;

create or replace function public.trg_enqueue_funding_recommendation_on_application_result()
returns trigger as $$
begin
  perform public.enqueue_funding_recommendation_job(
    new.user_id,
    new.tenant_id,
    'application_result_submitted',
    false,
    tg_table_name,
    new.id
  );
  return new;
end;
$$ language plpgsql;

create or replace function public.trg_enqueue_funding_recommendation_on_profile()
returns trigger as $$
begin
  if coalesce(new.onboarding_complete, false) = true
     and coalesce(old.onboarding_complete, false) = false then
    perform public.enqueue_funding_recommendation_job(
      new.id,
      null,
      'onboarding_completed',
      false,
      tg_table_name,
      new.id
    );
  end if;
  return new;
end;
$$ language plpgsql;

drop trigger if exists trg_funding_business_input_job on public.user_business_score_inputs;
create trigger trg_funding_business_input_job
after insert or update on public.user_business_score_inputs
for each row execute function public.trg_enqueue_funding_recommendation_on_business_input();

drop trigger if exists trg_funding_relationship_job on public.banking_relationships;
create trigger trg_funding_relationship_job
after insert or update on public.banking_relationships
for each row execute function public.trg_enqueue_funding_recommendation_on_relationship();

drop trigger if exists trg_funding_application_result_job on public.application_results;
create trigger trg_funding_application_result_job
after insert or update on public.application_results
for each row execute function public.trg_enqueue_funding_recommendation_on_application_result();

drop trigger if exists trg_funding_profile_job on public.user_profiles;
create trigger trg_funding_profile_job
after update on public.user_profiles
for each row execute function public.trg_enqueue_funding_recommendation_on_profile();
