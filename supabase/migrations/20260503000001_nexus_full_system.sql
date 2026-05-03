-- =============================================================================
-- NEXUS — Full System Migration v2
-- Adds: invite system, notifications, credit boost, business credit,
--       funding engine, grants, trading, AI employees, partner system
-- Safe to run repeatedly — uses IF NOT EXISTS throughout
-- =============================================================================

-- ─── PILOT / FREE ACCESS INVITE SYSTEM ───────────────────────────────────────

CREATE TABLE IF NOT EXISTS invited_users (
  id                    uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  name                  text        NOT NULL,
  email                 text        NOT NULL UNIQUE,
  phone                 text,
  notes                 text,
  access_type           text        NOT NULL DEFAULT 'free_full_access',
  subscription_required boolean     NOT NULL DEFAULT false,
  subscription_status   text        NOT NULL DEFAULT 'waived', -- 'waived' | 'active' | 'grace_period' | 'required'
  invited_by            uuid        REFERENCES auth.users(id),
  invite_status         text        NOT NULL DEFAULT 'pending', -- 'pending' | 'sent' | 'accepted' | 'expired'
  invite_sent_at        timestamptz,
  accepted_at           timestamptz,
  grace_period_days     integer     NOT NULL DEFAULT 14,
  grace_period_ends_at  timestamptz,
  signup_link           text,
  auth_user_id          uuid        REFERENCES auth.users(id),
  created_at            timestamptz NOT NULL DEFAULT now(),
  updated_at            timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS user_access_overrides (
  id                    uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id               uuid        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  subscription_required boolean     NOT NULL DEFAULT false,
  subscription_status   text        NOT NULL DEFAULT 'waived',
  access_type           text        NOT NULL DEFAULT 'free_full_access',
  override_reason       text,
  override_by           uuid        REFERENCES auth.users(id),
  effective_from        timestamptz NOT NULL DEFAULT now(),
  effective_until       timestamptz,
  created_at            timestamptz NOT NULL DEFAULT now(),
  updated_at            timestamptz NOT NULL DEFAULT now(),
  UNIQUE(user_id)
);

CREATE TABLE IF NOT EXISTS subscription_access_rules (
  id                    uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  rule_name             text        NOT NULL,
  applies_to            text        NOT NULL DEFAULT 'all', -- 'all' | 'pilot' | 'free_full_access'
  subscription_required boolean     NOT NULL DEFAULT true,
  grace_period_days     integer     NOT NULL DEFAULT 14,
  notification_days_before integer  NOT NULL DEFAULT 7,
  is_active             boolean     NOT NULL DEFAULT true,
  created_at            timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS subscription_notifications (
  id                    uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id               uuid        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  invited_user_id       uuid        REFERENCES invited_users(id),
  notification_type     text        NOT NULL, -- 'subscription_activating' | 'grace_period_start' | 'access_revoked' | 'welcome'
  subject               text        NOT NULL,
  body                  text        NOT NULL,
  sent_at               timestamptz,
  status                text        NOT NULL DEFAULT 'pending', -- 'pending' | 'sent' | 'failed'
  created_at            timestamptz NOT NULL DEFAULT now()
);

-- Enable RLS on invite tables
ALTER TABLE invited_users           ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_access_overrides   ENABLE ROW LEVEL SECURITY;
ALTER TABLE subscription_notifications ENABLE ROW LEVEL SECURITY;

-- Admin only policies for invite tables
CREATE POLICY IF NOT EXISTS "admin_manage_invited_users"
  ON invited_users FOR ALL
  USING (
    EXISTS (SELECT 1 FROM user_profiles WHERE id = auth.uid() AND role IN ('admin', 'super_admin'))
  );

CREATE POLICY IF NOT EXISTS "admin_manage_access_overrides"
  ON user_access_overrides FOR ALL
  USING (
    EXISTS (SELECT 1 FROM user_profiles WHERE id = auth.uid() AND role IN ('admin', 'super_admin'))
    OR user_id = auth.uid()
  );

CREATE POLICY IF NOT EXISTS "user_own_subscription_notifications"
  ON subscription_notifications FOR SELECT
  USING (user_id = auth.uid());

CREATE POLICY IF NOT EXISTS "admin_manage_subscription_notifications"
  ON subscription_notifications FOR ALL
  USING (
    EXISTS (SELECT 1 FROM user_profiles WHERE id = auth.uid() AND role IN ('admin', 'super_admin'))
  );

-- ─── NOTIFICATIONS ────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS notifications (
  id            uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id       uuid        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  type          text        NOT NULL DEFAULT 'system', -- 'action' | 'system' | 'ai' | 'urgent' | 'message' | 'funding' | 'grant' | 'trading' | 'subscription'
  title         text        NOT NULL,
  body          text,
  action_url    text,
  action_label  text,
  priority      integer     NOT NULL DEFAULT 1, -- 1=low, 2=medium, 3=high, 4=urgent
  read_at       timestamptz,
  dismissed_at  timestamptz,
  created_at    timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;

CREATE POLICY IF NOT EXISTS "user_own_notifications"
  ON notifications FOR ALL
  USING (user_id = auth.uid());

CREATE POLICY IF NOT EXISTS "admin_all_notifications"
  ON notifications FOR INSERT
  USING (
    EXISTS (SELECT 1 FROM user_profiles WHERE id = auth.uid() AND role IN ('admin', 'super_admin'))
  );

-- ─── CREDIT BOOST ENGINE ─────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS credit_boost_opportunities (
  id                  uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  name                text        NOT NULL,
  category            text        NOT NULL, -- 'rent_reporting' | 'authorized_user' | 'credit_builder' | 'utilization' | 'tradeline'
  description         text,
  impact_score_min    integer,
  impact_score_max    integer,
  impact_fundability  integer,
  estimated_timeline  text,
  cost_estimate       text,
  providers           jsonb,
  is_active           boolean     NOT NULL DEFAULT true,
  sort_order          integer     NOT NULL DEFAULT 0,
  created_at          timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS credit_boost_actions (
  id                  uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id             uuid        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  opportunity_id      uuid        REFERENCES credit_boost_opportunities(id),
  name                text        NOT NULL,
  status              text        NOT NULL DEFAULT 'considering', -- 'considering' | 'active' | 'completed' | 'cancelled'
  started_at          timestamptz,
  completed_at        timestamptz,
  notes               text,
  in_action_center    boolean     NOT NULL DEFAULT false,
  created_at          timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS rent_reporting_providers (
  id            uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  name          text        NOT NULL,
  description   text,
  monthly_cost  numeric(8,2),
  bureaus       text[],     -- ['experian','equifax','transunion']
  website_url   text,
  how_it_works  text,
  is_active     boolean     NOT NULL DEFAULT true
);

CREATE TABLE IF NOT EXISTS user_rent_reporting (
  id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         uuid        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  provider_id     uuid        REFERENCES rent_reporting_providers(id),
  status          text        NOT NULL DEFAULT 'pending', -- 'pending' | 'active' | 'verified' | 'cancelled'
  landlord_name   text,
  monthly_rent    numeric(10,2),
  verification_status text    NOT NULL DEFAULT 'unverified',
  started_at      timestamptz,
  created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS credit_fundability_scores (
  id                  uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id             uuid        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  score               integer     NOT NULL DEFAULT 0, -- 0-100
  personal_score_factor    integer,
  utilization_factor       integer,
  tradelines_factor        integer,
  inquiries_factor         integer,
  age_factor               integer,
  negative_items_factor    integer,
  notes               text,
  calculated_at       timestamptz NOT NULL DEFAULT now(),
  created_at          timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS credit_education_library (
  id          uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  title       text        NOT NULL,
  category    text        NOT NULL,
  content     text        NOT NULL,
  source_url  text,
  is_active   boolean     NOT NULL DEFAULT true,
  sort_order  integer     NOT NULL DEFAULT 0,
  created_at  timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE credit_boost_opportunities  ENABLE ROW LEVEL SECURITY;
ALTER TABLE credit_boost_actions        ENABLE ROW LEVEL SECURITY;
ALTER TABLE rent_reporting_providers    ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_rent_reporting         ENABLE ROW LEVEL SECURITY;
ALTER TABLE credit_fundability_scores   ENABLE ROW LEVEL SECURITY;
ALTER TABLE credit_education_library    ENABLE ROW LEVEL SECURITY;

CREATE POLICY IF NOT EXISTS "public_read_boost_opps"
  ON credit_boost_opportunities FOR SELECT USING (true);

CREATE POLICY IF NOT EXISTS "user_own_boost_actions"
  ON credit_boost_actions FOR ALL USING (user_id = auth.uid());

CREATE POLICY IF NOT EXISTS "public_read_rent_providers"
  ON rent_reporting_providers FOR SELECT USING (true);

CREATE POLICY IF NOT EXISTS "user_own_rent_reporting"
  ON user_rent_reporting FOR ALL USING (user_id = auth.uid());

CREATE POLICY IF NOT EXISTS "user_own_fundability"
  ON credit_fundability_scores FOR ALL USING (user_id = auth.uid());

CREATE POLICY IF NOT EXISTS "public_read_education"
  ON credit_education_library FOR SELECT USING (true);

-- ─── BUSINESS CREDIT + VENDOR TRADELINES ────────────────────────────────────

CREATE TABLE IF NOT EXISTS business_credit_profiles (
  id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         uuid        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  duns_number     text,
  paydex_score    integer,
  experian_score  integer,
  equifax_score   integer,
  credit_limit    numeric(12,2),
  payment_history text,       -- 'excellent' | 'good' | 'fair' | 'poor'
  updated_at      timestamptz NOT NULL DEFAULT now(),
  created_at      timestamptz NOT NULL DEFAULT now(),
  UNIQUE(user_id)
);

CREATE TABLE IF NOT EXISTS vendor_tradelines_catalog (
  id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  vendor_name     text        NOT NULL,
  tier            integer     NOT NULL DEFAULT 1, -- 1 | 2 | 3
  category        text        NOT NULL,
  description     text,
  requirements    text,
  credit_limit_range text,
  reports_to      text[],
  application_url text,
  is_active       boolean     NOT NULL DEFAULT true,
  sort_order      integer     NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS user_vendor_accounts (
  id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         uuid        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  vendor_id       uuid        REFERENCES vendor_tradelines_catalog(id),
  vendor_name     text        NOT NULL,
  tier            integer     NOT NULL DEFAULT 1,
  status          text        NOT NULL DEFAULT 'considering', -- 'considering' | 'applied' | 'approved' | 'active' | 'declined'
  credit_limit    numeric(10,2),
  applied_at      timestamptz,
  approved_at     timestamptz,
  created_at      timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE business_credit_profiles  ENABLE ROW LEVEL SECURITY;
ALTER TABLE vendor_tradelines_catalog ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_vendor_accounts      ENABLE ROW LEVEL SECURITY;

CREATE POLICY IF NOT EXISTS "user_own_biz_credit"
  ON business_credit_profiles FOR ALL USING (user_id = auth.uid());

CREATE POLICY IF NOT EXISTS "public_read_vendors"
  ON vendor_tradelines_catalog FOR SELECT USING (true);

CREATE POLICY IF NOT EXISTS "user_own_vendor_accounts"
  ON user_vendor_accounts FOR ALL USING (user_id = auth.uid());

-- ─── FUNDING READINESS ────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS funding_readiness_snapshots (
  id                  uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id             uuid        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  overall_score       integer     NOT NULL DEFAULT 0, -- 0-100
  personal_credit     integer,
  utilization         integer,
  tradelines          integer,
  business_foundation integer,
  business_credit     integer,
  bank_behavior       integer,
  risk_control        integer,
  calculated_at       timestamptz NOT NULL DEFAULT now(),
  created_at          timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS funding_roadmap_stages (
  id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         uuid        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  stage_key       text        NOT NULL, -- 'foundation' | 'credit_opt' | 'tier1' | 'tier2' | 'sba_grants'
  stage_name      text        NOT NULL,
  status          text        NOT NULL DEFAULT 'locked', -- 'locked' | 'active' | 'completed'
  score_required  integer     NOT NULL DEFAULT 0,
  blockers        jsonb,
  requirements    jsonb,
  next_action     text,
  completed_at    timestamptz,
  created_at      timestamptz NOT NULL DEFAULT now(),
  UNIQUE(user_id, stage_key)
);

CREATE TABLE IF NOT EXISTS funding_timeline_events (
  id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         uuid        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  event_type      text        NOT NULL,
  title           text        NOT NULL,
  description     text,
  event_date      timestamptz,
  status          text        NOT NULL DEFAULT 'upcoming',
  created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS next_best_actions (
  id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         uuid        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  category        text        NOT NULL, -- 'credit' | 'business' | 'funding' | 'grant' | 'trading'
  title           text        NOT NULL,
  description     text,
  impact_score    integer     NOT NULL DEFAULT 0,
  action_url      text,
  is_completed    boolean     NOT NULL DEFAULT false,
  priority        integer     NOT NULL DEFAULT 1,
  created_at      timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE funding_readiness_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE funding_roadmap_stages      ENABLE ROW LEVEL SECURITY;
ALTER TABLE funding_timeline_events     ENABLE ROW LEVEL SECURITY;
ALTER TABLE next_best_actions           ENABLE ROW LEVEL SECURITY;

CREATE POLICY IF NOT EXISTS "user_own_funding_readiness"
  ON funding_readiness_snapshots FOR ALL USING (user_id = auth.uid());

CREATE POLICY IF NOT EXISTS "user_own_roadmap_stages"
  ON funding_roadmap_stages FOR ALL USING (user_id = auth.uid());

CREATE POLICY IF NOT EXISTS "user_own_timeline_events"
  ON funding_timeline_events FOR ALL USING (user_id = auth.uid());

CREATE POLICY IF NOT EXISTS "user_own_nba"
  ON next_best_actions FOR ALL USING (user_id = auth.uid());

-- ─── FUNDING APPLICATIONS / 0% STRATEGY ─────────────────────────────────────

CREATE TABLE IF NOT EXISTS funding_recommendations (
  id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         uuid        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  lender_name     text        NOT NULL,
  product_type    text        NOT NULL,
  estimated_limit numeric(12,2),
  interest_rate   numeric(5,2),
  approval_odds   integer,    -- 0-100
  requirements    jsonb,
  recommended_at  timestamptz NOT NULL DEFAULT now(),
  is_active       boolean     NOT NULL DEFAULT true
);

CREATE TABLE IF NOT EXISTS funding_strategies (
  id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         uuid        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  strategy_name   text        NOT NULL, -- '0_percent_strategy' | 'business_credit_build' etc.
  status          text        NOT NULL DEFAULT 'pending',
  current_step    integer     NOT NULL DEFAULT 1,
  total_steps     integer     NOT NULL DEFAULT 1,
  notes           text,
  started_at      timestamptz,
  created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS funding_strategy_steps (
  id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  strategy_id     uuid        NOT NULL REFERENCES funding_strategies(id) ON DELETE CASCADE,
  user_id         uuid        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  step_number     integer     NOT NULL,
  title           text        NOT NULL,
  description     text,
  status          text        NOT NULL DEFAULT 'pending',
  completed_at    timestamptz,
  created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS funding_accounts (
  id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         uuid        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  lender_name     text        NOT NULL,
  product_type    text        NOT NULL,
  credit_limit    numeric(12,2),
  balance         numeric(12,2),
  interest_rate   numeric(5,2),
  status          text        NOT NULL DEFAULT 'active',
  opened_at       timestamptz,
  created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS client_funding_summary (
  id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         uuid        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  total_approved  numeric(12,2) NOT NULL DEFAULT 0,
  total_utilized  numeric(12,2) NOT NULL DEFAULT 0,
  round_count     integer     NOT NULL DEFAULT 0,
  last_round_at   timestamptz,
  next_round_at   timestamptz,
  updated_at      timestamptz NOT NULL DEFAULT now(),
  UNIQUE(user_id)
);

ALTER TABLE funding_recommendations ENABLE ROW LEVEL SECURITY;
ALTER TABLE funding_strategies      ENABLE ROW LEVEL SECURITY;
ALTER TABLE funding_strategy_steps  ENABLE ROW LEVEL SECURITY;
ALTER TABLE funding_accounts        ENABLE ROW LEVEL SECURITY;
ALTER TABLE client_funding_summary  ENABLE ROW LEVEL SECURITY;

CREATE POLICY IF NOT EXISTS "user_own_funding_recs"    ON funding_recommendations FOR ALL USING (user_id = auth.uid());
CREATE POLICY IF NOT EXISTS "user_own_strategies"      ON funding_strategies FOR ALL USING (user_id = auth.uid());
CREATE POLICY IF NOT EXISTS "user_own_strategy_steps"  ON funding_strategy_steps FOR ALL USING (user_id = auth.uid());
CREATE POLICY IF NOT EXISTS "user_own_funding_accounts" ON funding_accounts FOR ALL USING (user_id = auth.uid());
CREATE POLICY IF NOT EXISTS "user_own_funding_summary" ON client_funding_summary FOR ALL USING (user_id = auth.uid());

-- ─── APPROVAL SIMULATOR ──────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS lender_rules (
  id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  lender_name     text        NOT NULL,
  product_type    text        NOT NULL,
  min_score       integer,
  max_utilization integer,
  min_income      numeric(12,2),
  requirements    jsonb,
  estimated_limit_min numeric(10,2),
  estimated_limit_max numeric(10,2),
  is_active       boolean     NOT NULL DEFAULT true,
  created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS approval_simulations (
  id                  uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id             uuid        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  lender_rule_id      uuid        REFERENCES lender_rules(id),
  lender_name         text        NOT NULL,
  approval_odds       integer     NOT NULL DEFAULT 0,
  estimated_limit_min numeric(10,2),
  estimated_limit_max numeric(10,2),
  risk_factors        jsonb,
  improvements        jsonb,
  simulated_at        timestamptz NOT NULL DEFAULT now(),
  created_at          timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE lender_rules        ENABLE ROW LEVEL SECURITY;
ALTER TABLE approval_simulations ENABLE ROW LEVEL SECURITY;

CREATE POLICY IF NOT EXISTS "public_read_lender_rules" ON lender_rules FOR SELECT USING (true);
CREATE POLICY IF NOT EXISTS "user_own_simulations" ON approval_simulations FOR ALL USING (user_id = auth.uid());

-- ─── CONCIERGE ───────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS concierge_plans (
  id          uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  name        text        NOT NULL,
  price       numeric(8,2) NOT NULL,
  description text,
  features    jsonb,
  is_active   boolean     NOT NULL DEFAULT true
);

CREATE TABLE IF NOT EXISTS concierge_clients (
  id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         uuid        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  plan_id         uuid        REFERENCES concierge_plans(id),
  plan_name       text        NOT NULL,
  status          text        NOT NULL DEFAULT 'intake', -- 'intake' | 'review' | 'active' | 'completed'
  intake_data     jsonb,
  strategy_output text,
  admin_notes     text,
  enrolled_at     timestamptz NOT NULL DEFAULT now(),
  created_at      timestamptz NOT NULL DEFAULT now(),
  UNIQUE(user_id)
);

ALTER TABLE concierge_plans   ENABLE ROW LEVEL SECURITY;
ALTER TABLE concierge_clients ENABLE ROW LEVEL SECURITY;

CREATE POLICY IF NOT EXISTS "public_read_concierge_plans" ON concierge_plans FOR SELECT USING (true);
CREATE POLICY IF NOT EXISTS "user_own_concierge" ON concierge_clients FOR ALL USING (user_id = auth.uid());

-- ─── COMMISSION / REFERRAL ENGINE ────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS referrals (
  id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  referrer_id     uuid        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  referred_email  text        NOT NULL,
  referred_user_id uuid       REFERENCES auth.users(id),
  status          text        NOT NULL DEFAULT 'pending', -- 'pending' | 'signed_up' | 'converted'
  referral_code   text        NOT NULL,
  converted_at    timestamptz,
  created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS referral_earnings (
  id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  referrer_id     uuid        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  referral_id     uuid        REFERENCES referrals(id),
  amount          numeric(10,2) NOT NULL DEFAULT 0,
  percent_rate    numeric(5,2) NOT NULL DEFAULT 2.0,
  status          text        NOT NULL DEFAULT 'pending', -- 'pending' | 'verified' | 'paid'
  created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS funding_commissions (
  id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         uuid        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  funding_amount  numeric(12,2) NOT NULL,
  commission_rate numeric(5,2) NOT NULL DEFAULT 10.0,
  commission_amount numeric(10,2) NOT NULL,
  proof_url       text,
  status          text        NOT NULL DEFAULT 'pending', -- 'pending' | 'verified' | 'paid'
  notes           text,
  created_at      timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE referrals           ENABLE ROW LEVEL SECURITY;
ALTER TABLE referral_earnings   ENABLE ROW LEVEL SECURITY;
ALTER TABLE funding_commissions ENABLE ROW LEVEL SECURITY;

CREATE POLICY IF NOT EXISTS "user_own_referrals" ON referrals FOR ALL USING (referrer_id = auth.uid());
CREATE POLICY IF NOT EXISTS "user_own_referral_earnings" ON referral_earnings FOR ALL USING (referrer_id = auth.uid());
CREATE POLICY IF NOT EXISTS "user_own_commissions" ON funding_commissions FOR ALL USING (user_id = auth.uid());

-- ─── GRANTS ENGINE ───────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS grants_catalog (
  id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  title           text        NOT NULL,
  description     text,
  grantor         text,
  category        text        NOT NULL, -- 'federal' | 'state' | 'local' | 'nonprofit' | 'business'
  amount_min      numeric(12,2),
  amount_max      numeric(12,2),
  deadline        timestamptz,
  official_url    text,
  eligibility     text,
  required_docs   jsonb,
  naics_codes     text[],
  states          text[],
  is_active       boolean     NOT NULL DEFAULT true,
  is_verified     boolean     NOT NULL DEFAULT false,
  source          text,       -- URL of where grant was found
  scraped_at      timestamptz,
  created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS grant_matches (
  id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         uuid        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  grant_id        uuid        NOT NULL REFERENCES grants_catalog(id),
  match_score     integer     NOT NULL DEFAULT 0, -- 0-100
  blockers        jsonb,
  is_saved        boolean     NOT NULL DEFAULT false,
  matched_at      timestamptz NOT NULL DEFAULT now(),
  created_at      timestamptz NOT NULL DEFAULT now(),
  UNIQUE(user_id, grant_id)
);

CREATE TABLE IF NOT EXISTS grant_applications (
  id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         uuid        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  grant_id        uuid        NOT NULL REFERENCES grants_catalog(id),
  status          text        NOT NULL DEFAULT 'in_progress', -- 'in_progress' | 'submitted' | 'approved' | 'denied' | 'withdrawn'
  applied_at      timestamptz,
  decision_at     timestamptz,
  amount_requested numeric(12,2),
  amount_awarded  numeric(12,2),
  notes           text,
  created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS grant_review_requests (
  id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         uuid        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  keyword         text,
  business_type   text,
  city            text,
  state           text,
  grant_url       text,
  notes           text,
  status          text        NOT NULL DEFAULT 'pending', -- 'pending' | 'in_progress' | 'completed' | 'cancelled'
  response        text,
  completed_at    timestamptz,
  created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS grant_deadlines (
  id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         uuid        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  grant_id        uuid        REFERENCES grants_catalog(id),
  grant_title     text        NOT NULL,
  deadline        timestamptz NOT NULL,
  reminder_sent   boolean     NOT NULL DEFAULT false,
  created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS grant_scrape_logs (
  id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  source_url      text        NOT NULL,
  grants_found    integer     NOT NULL DEFAULT 0,
  grants_added    integer     NOT NULL DEFAULT 0,
  status          text        NOT NULL DEFAULT 'success',
  error_message   text,
  scraped_at      timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE grants_catalog        ENABLE ROW LEVEL SECURITY;
ALTER TABLE grant_matches          ENABLE ROW LEVEL SECURITY;
ALTER TABLE grant_applications    ENABLE ROW LEVEL SECURITY;
ALTER TABLE grant_review_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE grant_deadlines       ENABLE ROW LEVEL SECURITY;
ALTER TABLE grant_scrape_logs     ENABLE ROW LEVEL SECURITY;

CREATE POLICY IF NOT EXISTS "public_read_grants" ON grants_catalog FOR SELECT USING (is_active = true);
CREATE POLICY IF NOT EXISTS "user_own_grant_matches" ON grant_matches FOR ALL USING (user_id = auth.uid());
CREATE POLICY IF NOT EXISTS "user_own_grant_apps" ON grant_applications FOR ALL USING (user_id = auth.uid());
CREATE POLICY IF NOT EXISTS "user_own_grant_requests" ON grant_review_requests FOR ALL USING (user_id = auth.uid());
CREATE POLICY IF NOT EXISTS "user_own_grant_deadlines" ON grant_deadlines FOR ALL USING (user_id = auth.uid());
CREATE POLICY IF NOT EXISTS "admin_read_scrape_logs" ON grant_scrape_logs FOR SELECT USING (
  EXISTS (SELECT 1 FROM user_profiles WHERE id = auth.uid() AND role IN ('admin', 'super_admin'))
);

-- ─── TRADING LAB ──────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS trading_strategies (
  id                  uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  name                text        NOT NULL,
  description         text,
  market_type         text        NOT NULL DEFAULT 'stocks', -- 'stocks' | 'options' | 'forex' | 'crypto'
  risk_level          text        NOT NULL DEFAULT 'medium', -- 'low' | 'medium' | 'high'
  simulated_win_rate  numeric(5,2),
  max_drawdown        numeric(5,2),
  steps               jsonb,
  source_url          text,
  video_url           text,
  is_approved         boolean     NOT NULL DEFAULT false,
  admin_approved_by   uuid        REFERENCES auth.users(id),
  education_disclaimer text,
  created_at          timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS paper_trading_accounts (
  id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         uuid        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  balance         numeric(12,2) NOT NULL DEFAULT 100000, -- fake $100k starting balance
  initial_balance numeric(12,2) NOT NULL DEFAULT 100000,
  created_at      timestamptz NOT NULL DEFAULT now(),
  UNIQUE(user_id)
);

CREATE TABLE IF NOT EXISTS paper_trades (
  id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         uuid        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  account_id      uuid        NOT NULL REFERENCES paper_trading_accounts(id),
  strategy_id     uuid        REFERENCES trading_strategies(id),
  symbol          text        NOT NULL,
  direction       text        NOT NULL DEFAULT 'long', -- 'long' | 'short'
  entry_price     numeric(12,4) NOT NULL,
  exit_price      numeric(12,4),
  quantity        numeric(12,4) NOT NULL DEFAULT 1,
  status          text        NOT NULL DEFAULT 'open', -- 'open' | 'closed' | 'cancelled'
  pnl             numeric(12,2),
  opened_at       timestamptz NOT NULL DEFAULT now(),
  closed_at       timestamptz,
  notes           text,
  created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS paper_trading_metrics (
  id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         uuid        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  win_rate        numeric(5,2) NOT NULL DEFAULT 0,
  total_pnl       numeric(12,2) NOT NULL DEFAULT 0,
  max_drawdown    numeric(5,2) NOT NULL DEFAULT 0,
  total_trades    integer     NOT NULL DEFAULT 0,
  winning_trades  integer     NOT NULL DEFAULT 0,
  calculated_at   timestamptz NOT NULL DEFAULT now(),
  UNIQUE(user_id)
);

CREATE TABLE IF NOT EXISTS broker_connections (
  id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         uuid        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  broker_name     text        NOT NULL,
  status          text        NOT NULL DEFAULT 'pending', -- 'pending' | 'connected' | 'disconnected'
  notes           text,
  connected_at    timestamptz,
  created_at      timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE trading_strategies      ENABLE ROW LEVEL SECURITY;
ALTER TABLE paper_trading_accounts  ENABLE ROW LEVEL SECURITY;
ALTER TABLE paper_trades            ENABLE ROW LEVEL SECURITY;
ALTER TABLE paper_trading_metrics   ENABLE ROW LEVEL SECURITY;
ALTER TABLE broker_connections      ENABLE ROW LEVEL SECURITY;

CREATE POLICY IF NOT EXISTS "public_read_approved_strategies" ON trading_strategies FOR SELECT USING (is_approved = true);
CREATE POLICY IF NOT EXISTS "admin_manage_strategies" ON trading_strategies FOR ALL USING (
  EXISTS (SELECT 1 FROM user_profiles WHERE id = auth.uid() AND role IN ('admin', 'super_admin'))
);
CREATE POLICY IF NOT EXISTS "user_own_paper_account" ON paper_trading_accounts FOR ALL USING (user_id = auth.uid());
CREATE POLICY IF NOT EXISTS "user_own_paper_trades" ON paper_trades FOR ALL USING (user_id = auth.uid());
CREATE POLICY IF NOT EXISTS "user_own_trading_metrics" ON paper_trading_metrics FOR ALL USING (user_id = auth.uid());
CREATE POLICY IF NOT EXISTS "user_own_broker_connections" ON broker_connections FOR ALL USING (user_id = auth.uid());

-- ─── AI EMPLOYEE / RESEARCHER SYSTEM ─────────────────────────────────────────

CREATE TABLE IF NOT EXISTS ai_agent_events (
  id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         uuid        REFERENCES auth.users(id) ON DELETE CASCADE,
  agent_key       text        NOT NULL,
  event_type      text        NOT NULL,
  entity_id       text,
  entity_type     text,
  input_summary   text,
  output_summary  text,
  status          text        NOT NULL DEFAULT 'completed',
  duration_ms     integer,
  created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS ai_employee_runs (
  id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  agent_key       text        NOT NULL,
  trigger_type    text        NOT NULL DEFAULT 'scheduled', -- 'scheduled' | 'event' | 'manual'
  status          text        NOT NULL DEFAULT 'running',
  events_processed integer   NOT NULL DEFAULT 0,
  errors          integer     NOT NULL DEFAULT 0,
  started_at      timestamptz NOT NULL DEFAULT now(),
  completed_at    timestamptz,
  summary         text
);

CREATE TABLE IF NOT EXISTS research_sources (
  id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  source_type     text        NOT NULL DEFAULT 'youtube', -- 'youtube' | 'article' | 'podcast' | 'document'
  title           text        NOT NULL,
  url             text,
  transcript      text,
  topic_category  text,
  summary         text,
  score           integer     NOT NULL DEFAULT 0,
  status          text        NOT NULL DEFAULT 'pending', -- 'pending' | 'processed' | 'archived'
  processed_at    timestamptz,
  submitted_by    uuid        REFERENCES auth.users(id),
  created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS website_change_recommendations (
  id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  source_id       uuid        REFERENCES research_sources(id),
  title           text        NOT NULL,
  description     text,
  page_affected   text,
  change_type     text        NOT NULL DEFAULT 'content', -- 'content' | 'feature' | 'design' | 'data'
  status          text        NOT NULL DEFAULT 'pending_owner_review',
  reviewed_by     uuid        REFERENCES auth.users(id),
  reviewed_at     timestamptz,
  rejection_reason text,
  created_at      timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE ai_agent_events               ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_employee_runs              ENABLE ROW LEVEL SECURITY;
ALTER TABLE research_sources              ENABLE ROW LEVEL SECURITY;
ALTER TABLE website_change_recommendations ENABLE ROW LEVEL SECURITY;

CREATE POLICY IF NOT EXISTS "admin_manage_ai_events" ON ai_agent_events FOR ALL USING (
  EXISTS (SELECT 1 FROM user_profiles WHERE id = auth.uid() AND role IN ('admin', 'super_admin'))
);
CREATE POLICY IF NOT EXISTS "admin_manage_ai_runs" ON ai_employee_runs FOR ALL USING (
  EXISTS (SELECT 1 FROM user_profiles WHERE id = auth.uid() AND role IN ('admin', 'super_admin'))
);
CREATE POLICY IF NOT EXISTS "admin_manage_research" ON research_sources FOR ALL USING (
  EXISTS (SELECT 1 FROM user_profiles WHERE id = auth.uid() AND role IN ('admin', 'super_admin'))
);
CREATE POLICY IF NOT EXISTS "admin_manage_change_recs" ON website_change_recommendations FOR ALL USING (
  EXISTS (SELECT 1 FROM user_profiles WHERE id = auth.uid() AND role IN ('admin', 'super_admin'))
);

-- ─── BANK BEHAVIOR TRACKING ───────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS bank_behavior_snapshots (
  id                    uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id               uuid        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  bank_name             text,
  average_balance       numeric(12,2),
  monthly_deposits      numeric(12,2),
  monthly_withdrawals   numeric(12,2),
  overdraft_count       integer     NOT NULL DEFAULT 0,
  nsf_count             integer     NOT NULL DEFAULT 0,
  deposit_consistency   text,       -- 'excellent' | 'good' | 'fair' | 'poor'
  bank_readiness_score  integer     NOT NULL DEFAULT 0,
  snapshot_month        text,       -- 'YYYY-MM'
  notes                 text,
  created_at            timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE bank_behavior_snapshots ENABLE ROW LEVEL SECURITY;
CREATE POLICY IF NOT EXISTS "user_own_bank_behavior" ON bank_behavior_snapshots FOR ALL USING (user_id = auth.uid());

-- ─── PARTNER / WHITE LABEL SYSTEM ────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS partners (
  id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  name            text        NOT NULL,
  type            text        NOT NULL DEFAULT 'credit_repair', -- 'credit_repair' | 'funding_broker' | 'business_coach' | 'accountant' | 'nonprofit' | 'grant_writer'
  contact_email   text,
  contact_phone   text,
  status          text        NOT NULL DEFAULT 'active',
  commission_rate numeric(5,2) NOT NULL DEFAULT 0,
  created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS partner_branding (
  id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  partner_id      uuid        NOT NULL REFERENCES partners(id) ON DELETE CASCADE,
  logo_url        text,
  primary_color   text,
  secondary_color text,
  custom_domain   text,
  created_at      timestamptz NOT NULL DEFAULT now(),
  UNIQUE(partner_id)
);

CREATE TABLE IF NOT EXISTS partner_clients (
  id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  partner_id      uuid        NOT NULL REFERENCES partners(id),
  user_id         uuid        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  status          text        NOT NULL DEFAULT 'active',
  created_at      timestamptz NOT NULL DEFAULT now(),
  UNIQUE(partner_id, user_id)
);

ALTER TABLE partners          ENABLE ROW LEVEL SECURITY;
ALTER TABLE partner_branding  ENABLE ROW LEVEL SECURITY;
ALTER TABLE partner_clients   ENABLE ROW LEVEL SECURITY;

CREATE POLICY IF NOT EXISTS "admin_manage_partners" ON partners FOR ALL USING (
  EXISTS (SELECT 1 FROM user_profiles WHERE id = auth.uid() AND role IN ('admin', 'super_admin'))
);
CREATE POLICY IF NOT EXISTS "admin_manage_partner_branding" ON partner_branding FOR ALL USING (
  EXISTS (SELECT 1 FROM user_profiles WHERE id = auth.uid() AND role IN ('admin', 'super_admin'))
);
CREATE POLICY IF NOT EXISTS "admin_manage_partner_clients" ON partner_clients FOR ALL USING (
  EXISTS (SELECT 1 FROM user_profiles WHERE id = auth.uid() AND role IN ('admin', 'super_admin'))
);

-- ─── SEED: Vendor Tradelines Catalog ─────────────────────────────────────────

INSERT INTO vendor_tradelines_catalog (vendor_name, tier, category, description, requirements, credit_limit_range, reports_to, application_url, sort_order)
VALUES
  ('Uline', 1, 'Office/Shipping Supplies', 'Net-30 account, no personal guarantee needed after initial order', 'Business address, EIN, 3+ orders', '$500-$5,000', ARRAY['D&B'], 'https://www.uline.com', 1),
  ('Quill', 1, 'Office Supplies', 'Net-30 trade account for office supplies', 'Business name, phone, address', '$500-$3,000', ARRAY['D&B','Experian'], 'https://www.quill.com', 2),
  ('Grainger', 1, 'Industrial/Safety', 'Net-30 industrial supplier, reports to business bureaus', 'Business license, EIN', '$1,000-$10,000', ARRAY['D&B'], 'https://www.grainger.com', 3),
  ('Summa Office Supplies', 1, 'Office Supplies', 'Starter vendor for new businesses, easy approval', 'Business name only', '$100-$1,000', ARRAY['D&B','Experian'], 'https://www.summaofficesupplies.com', 4),
  ('Amazon Business', 2, 'E-commerce', 'Net-30 business account with Amazon', '1+ year in business, good payment history', '$2,000-$10,000', ARRAY['Experian'], 'https://business.amazon.com', 5),
  ('Staples Business', 2, 'Office Supplies', 'Net-30 account at Staples for established businesses', '6+ months in business, EIN', '$1,000-$5,000', ARRAY['D&B','Experian'], 'https://www.staples.com', 6),
  ('Shell Small Business Card', 3, 'Fuel/Fleet', 'Fleet fuel card for small businesses', 'Good business credit score, 1+ year', '$2,000-$15,000', ARRAY['Experian','Equifax'], 'https://www.shell.us/business', 7),
  ('Home Depot Commercial Account', 3, 'Hardware/Construction', 'Commercial credit account at Home Depot', 'Established business credit, 2+ years', '$5,000-$25,000', ARRAY['D&B','Experian'], 'https://www.homedepot.com/c/pro', 8)
ON CONFLICT DO NOTHING;

-- ─── SEED: Rent Reporting Providers ─────────────────────────────────────────

INSERT INTO rent_reporting_providers (name, description, monthly_cost, bureaus, website_url, how_it_works)
VALUES
  ('Rental Kharma', 'Reports rent payments to credit bureaus to build credit history', 6.95, ARRAY['TransUnion','Equifax'], 'https://rentalkharma.com', 'Sign up, verify with landlord, get 24+ months of rent history reported'),
  ('Rent Reporters', 'Reports rent to Equifax and TransUnion for credit building', 9.95, ARRAY['TransUnion','Equifax'], 'https://www.rentreporters.com', 'Landlord verification required, reports 2 years of history'),
  ('LevelCredit', 'Reports rent and utilities to major bureaus', 6.95, ARRAY['TransUnion'], 'https://levelcredit.com', 'Connect bank account or manually verify rent payments'),
  ('Experian RentBureau', 'Experian''s rent reporting service for tenants', 0, ARRAY['Experian'], 'https://www.experian.com/rentbureau', 'Landlord must enroll, tenant reporting free')
ON CONFLICT DO NOTHING;

-- ─── SEED: Credit Boost Opportunities ────────────────────────────────────────

INSERT INTO credit_boost_opportunities (name, category, description, impact_score_min, impact_score_max, impact_fundability, estimated_timeline, cost_estimate, sort_order)
VALUES
  ('Rent Reporting', 'rent_reporting', 'Report monthly rent payments to credit bureaus to add positive payment history', 10, 40, 15, '1-3 months', '$7-$10/mo', 1),
  ('Utilization Optimization', 'utilization', 'Lower credit utilization below 10% for maximum score improvement', 20, 60, 25, '1-2 months', 'Free', 2),
  ('Authorized User', 'authorized_user', 'Get added as authorized user on a seasoned tradeline', 15, 50, 20, '30-60 days', '$0-$200', 3),
  ('Credit Builder Loan', 'credit_builder', 'Secured loan that builds payment history and savings', 10, 35, 10, '12-24 months', '$10-$50/mo', 4),
  ('Personal Tradelines', 'tradeline', 'Purchase seasoned tradelines to boost age and history', 20, 80, 30, '30-45 days', '$200-$1,500', 5),
  ('Negative Item Dispute', 'dispute', 'Dispute inaccurate negative items on credit report', 20, 100, 40, '30-90 days', 'Free', 6)
ON CONFLICT DO NOTHING;

-- ─── SEED: Concierge Plans ────────────────────────────────────────────────────

INSERT INTO concierge_plans (name, price, description, features)
VALUES
  ('Basic', 500, 'Foundational credit and business setup strategy', '["Credit report review", "Business entity guidance", "Action plan"]'),
  ('Pro', 1000, 'Full credit repair and funding strategy', '["Everything in Basic", "Dispute letter generation", "Funding roadmap", "30-day check-in"]'),
  ('Elite', 2000, 'Done-with-you full service', '["Everything in Pro", "Weekly check-ins", "Grant research", "0% funding strategy", "Business credit build"]')
ON CONFLICT DO NOTHING;

-- ─── SEED: Sample Lender Rules ────────────────────────────────────────────────

INSERT INTO lender_rules (lender_name, product_type, min_score, max_utilization, estimated_limit_min, estimated_limit_max, requirements)
VALUES
  ('Chase', '0% Business Card', 680, 30, 5000, 25000, '{"years_in_business": 0, "personal_guarantee": true}'),
  ('Amex', '0% Business Card', 700, 25, 10000, 50000, '{"years_in_business": 0, "personal_guarantee": true}'),
  ('Capital One', 'Business Card', 660, 40, 3000, 15000, '{"years_in_business": 0, "personal_guarantee": true}'),
  ('SBA', '7(a) Loan', 650, 50, 50000, 500000, '{"years_in_business": 2, "annual_revenue": 100000}')
ON CONFLICT DO NOTHING;
