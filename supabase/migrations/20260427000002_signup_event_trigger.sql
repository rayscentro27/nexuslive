-- ── 1. Create user_profiles row when a new auth user is confirmed ─────────────
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger AS $$
BEGIN
  INSERT INTO public.user_profiles (id, full_name, role, subscription_plan, created_at, updated_at)
  VALUES (
    NEW.id,
    COALESCE(NEW.raw_user_meta_data->>'full_name', ''),
    'client',
    'free',
    now(),
    now()
  )
  ON CONFLICT (id) DO NOTHING;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW
  EXECUTE FUNCTION public.handle_new_user();


-- ── 2. Emit client_registered event when a profile row is created ─────────────
CREATE OR REPLACE FUNCTION public.emit_client_registered()
RETURNS trigger AS $$
DECLARE
  v_email text;
BEGIN
  SELECT email INTO v_email FROM auth.users WHERE id = NEW.id;

  INSERT INTO public.system_events (event_type, payload, status)
  VALUES (
    'client_registered',
    jsonb_build_object(
      'client_id',  NEW.id,
      'email',      COALESCE(v_email, ''),
      'full_name',  COALESCE(NEW.full_name, ''),
      'plan',       COALESCE(NEW.subscription_plan, 'free'),
      'role',       COALESCE(NEW.role, 'client')
    ),
    'pending'
  );
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_user_profile_created ON public.user_profiles;
CREATE TRIGGER on_user_profile_created
  AFTER INSERT ON public.user_profiles
  FOR EACH ROW
  EXECUTE FUNCTION public.emit_client_registered();
