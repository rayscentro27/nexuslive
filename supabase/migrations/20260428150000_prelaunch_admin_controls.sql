create extension if not exists pgcrypto;

create table if not exists public.admin_user_access_overrides (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null unique,
  email text,
  membership_level text not null check (membership_level in ('starter', 'growth', 'funding_pro', 'admin_test')),
  tester_access boolean not null default false,
  waiver_reason text,
  waived_by text not null,
  waived_at timestamptz not null default now(),
  expires_at timestamptz,
  revoked_by text,
  revoked_at timestamptz,
  revoke_reason text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.prelaunch_testers (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null unique,
  email text,
  tester_access boolean not null default true,
  welcome_email_last_sent_at timestamptz,
  welcome_email_last_preview_at timestamptz,
  assigned_by text not null,
  assigned_at timestamptz not null default now(),
  notes text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create or replace function public.touch_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

drop trigger if exists trg_admin_user_access_overrides_touch on public.admin_user_access_overrides;
create trigger trg_admin_user_access_overrides_touch
before update on public.admin_user_access_overrides
for each row execute function public.touch_updated_at();

drop trigger if exists trg_prelaunch_testers_touch on public.prelaunch_testers;
create trigger trg_prelaunch_testers_touch
before update on public.prelaunch_testers
for each row execute function public.touch_updated_at();
