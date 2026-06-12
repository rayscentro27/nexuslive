-- ============================================================================
-- DRAFT MIGRATION — Profile Completion persistence + portal notification
-- STATUS: DRAFT / REVIEW ONLY — NOT APPLIED. Do NOT place in supabase/migrations/
--         or run `supabase db push` until Ray explicitly approves.
--
-- Why: user_profiles.onboarding_complete never persists (frontend never sets it),
--      and the only existing trigger on user_profiles (trg_funding_profile_job)
--      enqueues a FUNDING RECOMMENDATION JOB — it does NOT create a portal
--      notifications row. So completing a profile produces no notification.
--
-- This migration adds, WITHOUT touching the existing funding trigger:
--   1) RPC complete_user_profile(...) — atomic, self-only completion path.
--   2) A separate trigger that inserts ONE idempotent 'onboarding' notification
--      when onboarding_complete transitions false -> true.
--
-- Safety: additive only. No DROP of data/columns. No change to existing policies
--         or the existing funding trigger. SECURITY DEFINER functions are scoped
--         to the profile owner (auth.uid() / NEW.id) to preserve tenant isolation.
-- ============================================================================

-- 1) Atomic completion RPC (self-service; a user can only complete THEIR profile)
create or replace function public.complete_user_profile(p_readiness_score integer default null)
returns public.user_profiles
language plpgsql
security definer
set search_path = public
as $$
declare
  v_row public.user_profiles;
begin
  if auth.uid() is null then
    raise exception 'not authenticated';
  end if;

  update public.user_profiles
     set onboarding_complete = true,
         readiness_score = coalesce(p_readiness_score, nullif(readiness_score, 0), 50),
         updated_at = now()
   where id = auth.uid()            -- tenant/user isolation: only the caller's own row
   returning * into v_row;

  if not found then
    raise exception 'profile not found for current user';
  end if;

  return v_row;  -- the false->true transition fires the notification trigger below
end;
$$;

grant execute on function public.complete_user_profile(integer) to authenticated;

-- 2) Idempotent portal-notification on completion (separate from funding trigger)
create or replace function public.fn_notify_on_onboarding_complete()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  -- Idempotency: never create a second onboarding notification for this user.
  if exists (
        select 1 from public.notifications
         where user_id = NEW.id
           and type in ('onboarding', 'onboarding_completed')
     ) then
    return NEW;
  end if;

  insert into public.notifications (user_id, type, title, body, priority, action_url, action_label)
  values (
    NEW.id,                                   -- tenant-safe: profile owner only
    'onboarding',
    'Profile complete 🎉',
    'Your profile is complete. We are reviewing your funding readiness and will surface your next steps shortly.',
    2,
    '/app',
    'View dashboard'
  );
  return NEW;
end;
$$;

-- Fire ONLY on the false->true transition of onboarding_complete.
drop trigger if exists trg_user_profiles_onboarding_notification on public.user_profiles;
create trigger trg_user_profiles_onboarding_notification
  after update of onboarding_complete on public.user_profiles
  for each row
  when (
    coalesce(NEW.onboarding_complete, false) = true
    and coalesce(OLD.onboarding_complete, false) = false
  )
  execute function public.fn_notify_on_onboarding_complete();

-- ============================================================================
-- ROLLBACK (if applied and needs reverting):
--   drop trigger if exists trg_user_profiles_onboarding_notification on public.user_profiles;
--   drop function if exists public.fn_notify_on_onboarding_complete();
--   drop function if exists public.complete_user_profile(integer);
-- (No data is deleted by this migration; rollback only removes the new objects.)
-- ============================================================================
