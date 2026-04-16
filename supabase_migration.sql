-- =============================================================================
-- NEXUS — Full Schema Migration
-- New Supabase project: ygqglfbhxiumqdisauar
-- 24 tables: Client Portal + Admin Portal + AI Workforce + Owner Self-Use
-- Run this in: Supabase Dashboard → SQL Editor → New Query → Run
-- =============================================================================

-- =============================================================================
-- CLEANUP: Drop ALL tables from any previous or partial migrations
-- Safe to run — cascades handle foreign key dependencies
-- =============================================================================

-- Previous partial migration tables
DROP TABLE IF EXISTS admin_notes            CASCADE;
DROP TABLE IF EXISTS business_opportunities CASCADE;
DROP TABLE IF EXISTS activity_log           CASCADE;
DROP TABLE IF EXISTS trading_performance    CASCADE;
DROP TABLE IF EXISTS trading_journal        CASCADE;
DROP TABLE IF EXISTS trading_strategies     CASCADE;
DROP TABLE IF EXISTS chat_messages          CASCADE;
DROP TABLE IF EXISTS chat_conversations     CASCADE;
DROP TABLE IF EXISTS documents              CASCADE;
DROP TABLE IF EXISTS tasks                  CASCADE;
DROP TABLE IF EXISTS funding_applications   CASCADE;
DROP TABLE IF EXISTS funding_actions        CASCADE;
DROP TABLE IF EXISTS funding_stages         CASCADE;
DROP TABLE IF EXISTS credit_disputes        CASCADE;
DROP TABLE IF EXISTS credit_reports         CASCADE;
DROP TABLE IF EXISTS business_details       CASCADE;
DROP TABLE IF EXISTS business_entities      CASCADE;
DROP TABLE IF EXISTS payment_methods        CASCADE;
DROP TABLE IF EXISTS subscriptions          CASCADE;
DROP TABLE IF EXISTS user_settings          CASCADE;
DROP TABLE IF EXISTS user_profiles          CASCADE;
DROP TABLE IF EXISTS bot_profiles           CASCADE;
DROP TABLE IF EXISTS task_templates         CASCADE;
DROP TABLE IF EXISTS funding_stage_templates CASCADE;

-- Google AI Studio tables
DROP TABLE IF EXISTS business_profiles CASCADE;
DROP TABLE IF EXISTS referrals         CASCADE;
DROP TABLE IF EXISTS profiles          CASCADE;

-- =============================================================================
-- EXTENSIONS
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- =============================================================================
-- 1. USER IDENTITY & ACCESS
-- =============================================================================

-- Extended profile for every auth user (client or admin)
CREATE TABLE IF NOT EXISTS user_profiles (
  id                    uuid        PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  full_name             text,
  avatar_url            text,
  role                  text        NOT NULL DEFAULT 'client', -- 'client' | 'admin' | 'super_admin'
  readiness_score       integer     NOT NULL DEFAULT 0,        -- 0-100
  business_potential    text,
  current_funding_level integer     NOT NULL DEFAULT 1,        -- 1-4
  next_milestone        text,
  subscription_plan     text        NOT NULL DEFAULT 'free',   -- 'free' | 'starter' | 'pro'
  onboarding_complete   boolean     NOT NULL DEFAULT false,
  created_at            timestamptz NOT NULL DEFAULT now(),
  updated_at            timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS user_settings (
  user_id                  uuid        PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  notification_email       boolean     NOT NULL DEFAULT true,
  notification_sms         boolean     NOT NULL DEFAULT false,
  notification_push        boolean     NOT NULL DEFAULT true,
  two_factor_enabled       boolean     NOT NULL DEFAULT false,
  profile_visibility       text        NOT NULL DEFAULT 'private',
  ai_communication_style   text        NOT NULL DEFAULT 'professional',
  language                 text        NOT NULL DEFAULT 'en',
  timezone                 text        NOT NULL DEFAULT 'America/Los_Angeles',
  updated_at               timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS subscriptions (
  id               uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id          uuid        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  plan_name        text        NOT NULL DEFAULT 'free',
  price_per_month  numeric(8,2),
  status           text        NOT NULL DEFAULT 'active', -- 'active' | 'cancelled' | 'past_due'
  started_at       timestamptz NOT NULL DEFAULT now(),
  next_billing_at  timestamptz,
  cancelled_at     timestamptz,
  created_at       timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS payment_methods (
  id            uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id       uuid        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  type          text        NOT NULL,  -- 'visa' | 'mastercard' | 'ach'
  last_four     text,
  expiry_month  integer,
  expiry_year   integer,
  is_default    boolean     NOT NULL DEFAULT false,
  verified      boolean     NOT NULL DEFAULT false,
  created_at    timestamptz NOT NULL DEFAULT now()
);

-- =============================================================================
-- 2. BUSINESS SETUP
-- =============================================================================

CREATE TABLE IF NOT EXISTS business_entities (
  id                          uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id                     uuid        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  business_name               text,
  entity_type                 text,       -- 'LLC' | 'S-Corp' | 'C-Corp' | 'Sole Prop'
  ein                         text,
  duns_number                 text,
  formation_state             text,
  formation_date              date,
  naics_code                  text,
  secretary_of_state_status   text        NOT NULL DEFAULT 'pending',
  duns_report_status          text        NOT NULL DEFAULT 'pending',
  tradelines_status           text        NOT NULL DEFAULT 'pending',
  status                      text        NOT NULL DEFAULT 'incomplete',
  created_at                  timestamptz NOT NULL DEFAULT now(),
  updated_at                  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS business_details (
  user_id           uuid        PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  address_line1     text,
  address_line2     text,
  city              text,
  state             text,
  zip               text,
  phone             text,
  website_url       text,
  contact_email     text,
  logo_url          text,
  google_indexed    boolean     NOT NULL DEFAULT false,
  domain_email_set  boolean     NOT NULL DEFAULT false,
  updated_at        timestamptz NOT NULL DEFAULT now()
);

-- =============================================================================
-- 3. CREDIT
-- =============================================================================

CREATE TABLE IF NOT EXISTS credit_reports (
  id                  uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id             uuid        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  score               integer,
  score_band          text,       -- 'poor' | 'fair' | 'good' | 'excellent'
  funding_range_min   integer,
  funding_range_max   integer,
  utilization_percent numeric(5,2),
  total_debt          numeric(12,2),
  report_file_url     text,
  report_date         date,
  is_current          boolean     NOT NULL DEFAULT true,
  created_at          timestamptz NOT NULL DEFAULT now(),
  updated_at          timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS credit_disputes (
  id            uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id       uuid        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  creditor      text        NOT NULL,
  account_number text,
  amount        numeric(12,2),
  reason        text        NOT NULL,
  status        text        NOT NULL DEFAULT 'pending', -- 'pending' | 'submitted' | 'resolved' | 'rejected'
  letter_url    text,
  notes         text,
  submitted_at  timestamptz,
  resolved_at   timestamptz,
  created_at    timestamptz NOT NULL DEFAULT now(),
  updated_at    timestamptz NOT NULL DEFAULT now()
);

-- =============================================================================
-- 4. FUNDING JOURNEY
-- =============================================================================

-- Funding roadmap stages per user (4 levels: Foundation → 0% Cards → Credit Lines → SBA)
CREATE TABLE IF NOT EXISTS funding_stages (
  id                  uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id             uuid        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  stage_number        integer     NOT NULL,   -- 1, 2, 3, 4
  title               text        NOT NULL,
  description         text,
  status              text        NOT NULL DEFAULT 'locked', -- 'completed' | 'current' | 'locked'
  funding_range_min   integer,
  funding_range_max   integer,
  readiness_required  integer     NOT NULL DEFAULT 0,
  projected_approvals integer,
  timeline_weeks      integer,
  created_at          timestamptz NOT NULL DEFAULT now(),
  updated_at          timestamptz NOT NULL DEFAULT now(),
  UNIQUE (user_id, stage_number)
);

-- Action steps within each funding stage
CREATE TABLE IF NOT EXISTS funding_actions (
  id                    uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  stage_id              uuid        NOT NULL REFERENCES funding_stages(id) ON DELETE CASCADE,
  user_id               uuid        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  title                 text        NOT NULL,
  description           text,
  status                text        NOT NULL DEFAULT 'pending', -- 'pending' | 'in_progress' | 'complete'
  readiness_impact      integer     NOT NULL DEFAULT 0,         -- % readiness boost on completion
  sort_order            integer     NOT NULL DEFAULT 0,
  due_date              date,
  completed_at          timestamptz,
  created_at            timestamptz NOT NULL DEFAULT now()
);

-- Actual funding applications
CREATE TABLE IF NOT EXISTS funding_applications (
  id                  uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id             uuid        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  lender_name         text,
  product_type        text,       -- '0_percent_card' | 'credit_line' | 'sba_loan' | 'term_loan'
  requested_amount    numeric(12,2),
  approved_amount     numeric(12,2),
  interest_rate       numeric(5,2),
  approval_odds       integer,    -- percentage
  status              text        NOT NULL DEFAULT 'draft', -- 'draft' | 'submitted' | 'approved' | 'denied' | 'pending'
  notes               text,
  applied_at          timestamptz,
  decided_at          timestamptz,
  created_at          timestamptz NOT NULL DEFAULT now(),
  updated_at          timestamptz NOT NULL DEFAULT now()
);

-- =============================================================================
-- 5. ACTION CENTER TASKS
-- =============================================================================

CREATE TABLE IF NOT EXISTS tasks (
  id                uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id           uuid        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  title             text        NOT NULL,
  description       text,
  category          text        NOT NULL DEFAULT 'general', -- 'business_setup' | 'credit' | 'funding' | 'general'
  status            text        NOT NULL DEFAULT 'pending', -- 'pending' | 'in_progress' | 'complete'
  priority          integer     NOT NULL DEFAULT 5,          -- 1 (highest) to 10
  readiness_impact  integer     NOT NULL DEFAULT 0,
  is_primary        boolean     NOT NULL DEFAULT false,
  duration_minutes  integer,
  due_date          date,
  completed_at      timestamptz,
  created_at        timestamptz NOT NULL DEFAULT now(),
  updated_at        timestamptz NOT NULL DEFAULT now()
);

-- =============================================================================
-- 6. DOCUMENTS
-- =============================================================================

CREATE TABLE IF NOT EXISTS documents (
  id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         uuid        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  filename        text        NOT NULL,
  file_url        text        NOT NULL,
  file_size       bigint,
  mime_type       text,
  category        text        NOT NULL DEFAULT 'general', -- 'business' | 'credit' | 'funding' | 'identity' | 'legal' | 'general'
  document_type   text,
  status          text        NOT NULL DEFAULT 'pending', -- 'pending' | 'verified' | 'attention'
  uploaded_by     text        NOT NULL DEFAULT 'client',  -- 'client' | 'admin'
  notes           text,
  verified_at     timestamptz,
  verified_by     uuid,
  created_at      timestamptz NOT NULL DEFAULT now(),
  updated_at      timestamptz NOT NULL DEFAULT now()
);

-- =============================================================================
-- 7. MESSAGING
-- =============================================================================

CREATE TABLE IF NOT EXISTS chat_conversations (
  id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         uuid        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  contact_id      text        NOT NULL,  -- agent id or 'system'
  contact_name    text        NOT NULL,
  contact_role    text,
  contact_type    text        NOT NULL DEFAULT 'ai', -- 'ai' | 'human' | 'system'
  last_message_at timestamptz NOT NULL DEFAULT now(),
  unread_count    integer     NOT NULL DEFAULT 0,
  created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS chat_messages (
  id               uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  conversation_id  uuid        NOT NULL REFERENCES chat_conversations(id) ON DELETE CASCADE,
  sender_id        text        NOT NULL,
  sender_name      text        NOT NULL,
  content          text        NOT NULL,
  is_user_message  boolean     NOT NULL DEFAULT false,
  read_at          timestamptz,
  created_at       timestamptz NOT NULL DEFAULT now()
);

-- =============================================================================
-- 8. TRADING (FRONTEND-FACING)
-- =============================================================================

CREATE TABLE IF NOT EXISTS trading_strategies (
  id               uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id          uuid        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  strategy_name    text        NOT NULL,
  description      text,
  asset_class      text,
  timeframe        text,
  win_percent      numeric(5,2),
  trades_count     integer     NOT NULL DEFAULT 0,
  net_pnl          numeric(12,2),
  stability_rating text,       -- 'high' | 'medium' | 'low'
  status           text        NOT NULL DEFAULT 'active', -- 'active' | 'paused' | 'archived'
  is_paper         boolean     NOT NULL DEFAULT true,
  created_at       timestamptz NOT NULL DEFAULT now(),
  updated_at       timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS trading_journal (
  id             uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id        uuid        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  strategy_id    uuid        REFERENCES trading_strategies(id),
  symbol         text,
  side           text,        -- 'long' | 'short'
  entry_price    numeric(12,4),
  exit_price     numeric(12,4),
  quantity       numeric(12,4),
  pnl            numeric(12,2),
  outcome        text,        -- 'win' | 'loss' | 'breakeven'
  notes          text,
  traded_at      timestamptz NOT NULL DEFAULT now(),
  created_at     timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS trading_performance (
  id            uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id       uuid        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  period_days   integer     NOT NULL DEFAULT 30,
  win_rate      numeric(5,2),
  net_pnl       numeric(12,2),
  trade_count   integer     NOT NULL DEFAULT 0,
  calculated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (user_id, period_days)
);

-- =============================================================================
-- 9. BOT PROFILES (AI Employees — display configs, seeded below)
-- =============================================================================

CREATE TABLE IF NOT EXISTS bot_profiles (
  id           uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  agent_key    text        UNIQUE NOT NULL,  -- 'credit-ai' | 'funding-ai' | 'setup-ai' | 'trading-ai'
  name         text        NOT NULL,
  role         text        NOT NULL,
  division     text,
  description  text,
  status       text        NOT NULL DEFAULT 'active', -- 'active' | 'idle' | 'offline'
  efficiency   numeric(5,1),
  avatar_style text        NOT NULL DEFAULT 'default',
  sort_order   integer     NOT NULL DEFAULT 0,
  created_at   timestamptz NOT NULL DEFAULT now()
);

-- =============================================================================
-- 10. BUSINESS OPPORTUNITIES (Admin)
-- =============================================================================

CREATE TABLE IF NOT EXISTS business_opportunities (
  id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  created_by      uuid        REFERENCES auth.users(id),
  title           text        NOT NULL,
  description     text,
  type            text        NOT NULL, -- 'funding' | 'grant' | 'partnership' | 'affiliate' | 'vendor' | 'growth' | 'ai_detected'
  source          text,
  value_min       numeric(12,2),
  value_max       numeric(12,2),
  deadline        date,
  eligibility     text,
  status          text        NOT NULL DEFAULT 'active', -- 'active' | 'archived' | 'applied'
  is_client_facing boolean   NOT NULL DEFAULT false,
  linked_user_id  uuid        REFERENCES auth.users(id),
  metadata        jsonb,
  created_at      timestamptz NOT NULL DEFAULT now(),
  updated_at      timestamptz NOT NULL DEFAULT now()
);

-- =============================================================================
-- 11. ACTIVITY LOG (Dashboard feed)
-- =============================================================================

CREATE TABLE IF NOT EXISTS activity_log (
  id            uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id       uuid        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  actor         text        NOT NULL,  -- agent name or 'system' or 'user'
  action        text        NOT NULL,
  entity_type   text,
  entity_id     text,
  metadata      jsonb,
  created_at    timestamptz NOT NULL DEFAULT now()
);

-- =============================================================================
-- 12. ADMIN NOTES (per-client)
-- =============================================================================

CREATE TABLE IF NOT EXISTS admin_notes (
  id          uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  admin_id    uuid        NOT NULL REFERENCES auth.users(id),
  client_id   uuid        NOT NULL REFERENCES auth.users(id),
  content     text        NOT NULL,
  is_pinned   boolean     NOT NULL DEFAULT false,
  created_at  timestamptz NOT NULL DEFAULT now(),
  updated_at  timestamptz NOT NULL DEFAULT now()
);

-- =============================================================================
-- INDEXES
-- =============================================================================

CREATE INDEX IF NOT EXISTS idx_user_profiles_role          ON user_profiles (role);
CREATE INDEX IF NOT EXISTS idx_user_profiles_readiness     ON user_profiles (readiness_score DESC);
CREATE INDEX IF NOT EXISTS idx_business_entities_user      ON business_entities (user_id);
CREATE INDEX IF NOT EXISTS idx_credit_reports_user         ON credit_reports (user_id, is_current);
CREATE INDEX IF NOT EXISTS idx_credit_disputes_user_status ON credit_disputes (user_id, status);
CREATE INDEX IF NOT EXISTS idx_funding_stages_user         ON funding_stages (user_id, stage_number);
CREATE INDEX IF NOT EXISTS idx_funding_actions_stage       ON funding_actions (stage_id, status);
CREATE INDEX IF NOT EXISTS idx_tasks_user_status           ON tasks (user_id, status);
CREATE INDEX IF NOT EXISTS idx_documents_user_category     ON documents (user_id, category);
CREATE INDEX IF NOT EXISTS idx_chat_conversations_user     ON chat_conversations (user_id, last_message_at DESC);
CREATE INDEX IF NOT EXISTS idx_chat_messages_conversation  ON chat_messages (conversation_id, created_at);
CREATE INDEX IF NOT EXISTS idx_trading_journal_user        ON trading_journal (user_id, traded_at DESC);
CREATE INDEX IF NOT EXISTS idx_activity_log_user           ON activity_log (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_opportunities_type_status   ON business_opportunities (type, status);
CREATE INDEX IF NOT EXISTS idx_admin_notes_client          ON admin_notes (client_id, created_at DESC);

-- =============================================================================
-- ROW LEVEL SECURITY
-- =============================================================================

ALTER TABLE user_profiles          ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_settings          ENABLE ROW LEVEL SECURITY;
ALTER TABLE subscriptions          ENABLE ROW LEVEL SECURITY;
ALTER TABLE payment_methods        ENABLE ROW LEVEL SECURITY;
ALTER TABLE business_entities      ENABLE ROW LEVEL SECURITY;
ALTER TABLE business_details       ENABLE ROW LEVEL SECURITY;
ALTER TABLE credit_reports         ENABLE ROW LEVEL SECURITY;
ALTER TABLE credit_disputes        ENABLE ROW LEVEL SECURITY;
ALTER TABLE funding_stages         ENABLE ROW LEVEL SECURITY;
ALTER TABLE funding_actions        ENABLE ROW LEVEL SECURITY;
ALTER TABLE funding_applications   ENABLE ROW LEVEL SECURITY;
ALTER TABLE tasks                  ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents              ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_conversations     ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_messages          ENABLE ROW LEVEL SECURITY;
ALTER TABLE trading_strategies     ENABLE ROW LEVEL SECURITY;
ALTER TABLE trading_journal        ENABLE ROW LEVEL SECURITY;
ALTER TABLE trading_performance    ENABLE ROW LEVEL SECURITY;
ALTER TABLE activity_log           ENABLE ROW LEVEL SECURITY;
ALTER TABLE admin_notes            ENABLE ROW LEVEL SECURITY;
ALTER TABLE business_opportunities ENABLE ROW LEVEL SECURITY;

-- Helper: check if current user is admin or super_admin
CREATE OR REPLACE FUNCTION is_admin()
RETURNS boolean LANGUAGE sql SECURITY DEFINER AS $$
  SELECT EXISTS (
    SELECT 1 FROM user_profiles
    WHERE id = auth.uid()
    AND role IN ('admin', 'super_admin')
  );
$$;

-- user_profiles: users see own, admins see all
CREATE POLICY "users_own_profile"    ON user_profiles FOR ALL USING (id = auth.uid());
CREATE POLICY "admin_all_profiles"   ON user_profiles FOR SELECT USING (is_admin());

-- user_settings
CREATE POLICY "users_own_settings"   ON user_settings FOR ALL USING (user_id = auth.uid());

-- subscriptions
CREATE POLICY "users_own_sub"        ON subscriptions FOR ALL USING (user_id = auth.uid());
CREATE POLICY "admin_all_subs"       ON subscriptions FOR SELECT USING (is_admin());

-- payment_methods
CREATE POLICY "users_own_payments"   ON payment_methods FOR ALL USING (user_id = auth.uid());

-- business_entities
CREATE POLICY "users_own_business"   ON business_entities FOR ALL USING (user_id = auth.uid());
CREATE POLICY "admin_all_business"   ON business_entities FOR SELECT USING (is_admin());

-- business_details
CREATE POLICY "users_own_details"    ON business_details FOR ALL USING (user_id = auth.uid());
CREATE POLICY "admin_all_details"    ON business_details FOR SELECT USING (is_admin());

-- credit_reports
CREATE POLICY "users_own_credit"     ON credit_reports FOR ALL USING (user_id = auth.uid());
CREATE POLICY "admin_all_credit"     ON credit_reports FOR SELECT USING (is_admin());

-- credit_disputes
CREATE POLICY "users_own_disputes"   ON credit_disputes FOR ALL USING (user_id = auth.uid());
CREATE POLICY "admin_all_disputes"   ON credit_disputes FOR SELECT USING (is_admin());

-- funding_stages
CREATE POLICY "users_own_stages"     ON funding_stages FOR ALL USING (user_id = auth.uid());
CREATE POLICY "admin_all_stages"     ON funding_stages FOR SELECT USING (is_admin());

-- funding_actions
CREATE POLICY "users_own_actions"    ON funding_actions FOR ALL USING (user_id = auth.uid());
CREATE POLICY "admin_all_actions"    ON funding_actions FOR SELECT USING (is_admin());

-- funding_applications
CREATE POLICY "users_own_apps"       ON funding_applications FOR ALL USING (user_id = auth.uid());
CREATE POLICY "admin_all_apps"       ON funding_applications FOR SELECT USING (is_admin());

-- tasks
CREATE POLICY "users_own_tasks"      ON tasks FOR ALL USING (user_id = auth.uid());
CREATE POLICY "admin_all_tasks"      ON tasks FOR SELECT USING (is_admin());

-- documents
CREATE POLICY "users_own_docs"       ON documents FOR ALL USING (user_id = auth.uid());
CREATE POLICY "admin_all_docs"       ON documents FOR SELECT USING (is_admin());

-- chat
CREATE POLICY "users_own_convos"     ON chat_conversations FOR ALL USING (user_id = auth.uid());
CREATE POLICY "users_own_messages"   ON chat_messages FOR ALL
  USING (conversation_id IN (SELECT id FROM chat_conversations WHERE user_id = auth.uid()));
CREATE POLICY "admin_all_convos"     ON chat_conversations FOR SELECT USING (is_admin());

-- trading
CREATE POLICY "users_own_strategies" ON trading_strategies FOR ALL USING (user_id = auth.uid());
CREATE POLICY "users_own_journal"    ON trading_journal FOR ALL USING (user_id = auth.uid());
CREATE POLICY "users_own_perf"       ON trading_performance FOR ALL USING (user_id = auth.uid());
CREATE POLICY "admin_all_trading"    ON trading_strategies FOR SELECT USING (is_admin());

-- activity_log
CREATE POLICY "users_own_activity"   ON activity_log FOR SELECT USING (user_id = auth.uid());
CREATE POLICY "admin_all_activity"   ON activity_log FOR SELECT USING (is_admin());
CREATE POLICY "system_insert_activity" ON activity_log FOR INSERT WITH CHECK (true);

-- admin_notes
CREATE POLICY "admin_own_notes"      ON admin_notes FOR ALL USING (admin_id = auth.uid() AND is_admin());
CREATE POLICY "admin_read_notes"     ON admin_notes FOR SELECT USING (client_id = auth.uid() OR is_admin());

-- business_opportunities (admin manages, optionally visible to clients)
CREATE POLICY "admin_manage_opps"    ON business_opportunities FOR ALL USING (is_admin());
CREATE POLICY "clients_view_opps"    ON business_opportunities FOR SELECT
  USING (is_client_facing = true AND (linked_user_id = auth.uid() OR linked_user_id IS NULL));

-- bot_profiles: everyone can read, only service role writes
ALTER TABLE bot_profiles ENABLE ROW LEVEL SECURITY;
CREATE POLICY "anyone_read_bots"     ON bot_profiles FOR SELECT USING (true);

-- =============================================================================
-- TRIGGER: auto-create user_profile on signup
-- =============================================================================

CREATE OR REPLACE FUNCTION handle_new_user()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER AS $$
BEGIN
  INSERT INTO user_profiles (id, full_name, role)
  VALUES (
    NEW.id,
    COALESCE(NEW.raw_user_meta_data->>'full_name', split_part(NEW.email, '@', 1)),
    COALESCE(NEW.raw_user_meta_data->>'role', 'client')
  );
  INSERT INTO user_settings (user_id) VALUES (NEW.id);
  RETURN NEW;
END;
$$;

CREATE OR REPLACE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION handle_new_user();

-- =============================================================================
-- TRIGGER: recalculate readiness score when tasks/stages complete
-- =============================================================================

CREATE OR REPLACE FUNCTION recalculate_readiness()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER AS $$
DECLARE
  v_user_id uuid;
  v_score   integer;
BEGIN
  v_user_id := COALESCE(NEW.user_id, OLD.user_id);
  SELECT LEAST(100, COALESCE(SUM(readiness_impact), 0))
  INTO v_score
  FROM tasks
  WHERE user_id = v_user_id AND status = 'complete';

  UPDATE user_profiles SET readiness_score = v_score, updated_at = now()
  WHERE id = v_user_id;
  RETURN NEW;
END;
$$;

CREATE OR REPLACE TRIGGER tasks_readiness_update
  AFTER INSERT OR UPDATE OF status ON tasks
  FOR EACH ROW EXECUTE FUNCTION recalculate_readiness();

-- =============================================================================
-- SEED: BOT PROFILES (AI Employees shown in frontend)
-- =============================================================================

INSERT INTO bot_profiles (agent_key, name, role, division, description, status, efficiency, sort_order) VALUES
  ('credit-ai',   'Credit AI',   'Credit Optimization', 'Underwriting & Risk',  'Analyzes credit reports, generates dispute letters, and tracks resolution automatically.',          'active', 98.2, 1),
  ('funding-ai',  'Funding AI',  'Capital Strategy',    'Acquisition & Sales',  'Matches clients with funding products based on readiness score and business profile.',              'active', 94.5, 2),
  ('setup-ai',    'Setup AI',    'Business Formation',  'Strategy & Analysis',  'Handles LLC filings, EIN applications, compliance checks, and bank setup workflows.',               'active', 99.1, 3),
  ('trading-ai',  'Trading AI',  'Market Analysis',     'Strategy & Analysis',  'Monitors market signals and executes trades based on approved strategies from the strategy lab.',   'idle',   92.8, 4)
ON CONFLICT (agent_key) DO UPDATE SET
  name = EXCLUDED.name,
  role = EXCLUDED.role,
  status = EXCLUDED.status,
  efficiency = EXCLUDED.efficiency;

-- =============================================================================
-- SEED: DEFAULT FUNDING STAGE TEMPLATES
-- (Applied per-user when they sign up via edge function or trigger)
-- =============================================================================

CREATE TABLE IF NOT EXISTS funding_stage_templates (
  stage_number        integer     PRIMARY KEY,
  title               text        NOT NULL,
  description         text,
  funding_range_min   integer,
  funding_range_max   integer,
  readiness_required  integer     NOT NULL DEFAULT 0,
  projected_approvals integer,
  timeline_weeks      integer
);

INSERT INTO funding_stage_templates VALUES
  (1, 'Business Foundation',  'Establish your legal entity, EIN, business address, and basic credit profile.',              0,      19000,  20, 3,  4),
  (2, '0% Interest Cards',    'Qualify for 0% business credit cards based on personal credit and business credibility.',     19000,  53000,  65, 5,  8),
  (3, 'Business Credit Lines','Build dedicated business credit lines with net terms and bank credit products.',              50000,  150000, 80, 4,  16),
  (4, 'SBA & Term Loans',     'Access SBA 7(a) loans, term loans, and institutional capital with proven revenue history.',  100000, 500000, 90, 2,  26)
ON CONFLICT (stage_number) DO NOTHING;

-- =============================================================================
-- SEED: DEFAULT TASK TEMPLATES (used to initialize tasks per new user)
-- =============================================================================

CREATE TABLE IF NOT EXISTS task_templates (
  id               uuid    PRIMARY KEY DEFAULT gen_random_uuid(),
  stage_number     integer,
  title            text    NOT NULL,
  description      text,
  category         text    NOT NULL DEFAULT 'business_setup',
  priority         integer NOT NULL DEFAULT 5,
  readiness_impact integer NOT NULL DEFAULT 0,
  is_primary       boolean NOT NULL DEFAULT false,
  duration_minutes integer
);

INSERT INTO task_templates (stage_number, title, description, category, priority, readiness_impact, is_primary, duration_minutes) VALUES
  (1, 'Form Your LLC or Corporation',       'Register your business entity with the state. Recommended: LLC for flexibility.',               'business_setup', 1, 15, true,  60),
  (1, 'Obtain Your EIN',                    'Apply for an Employer Identification Number through the IRS website (free, instant).',          'business_setup', 1, 10, false, 15),
  (1, 'Open a Business Bank Account',       'Separate personal and business finances. Required for funding applications.',                   'business_setup', 2, 8,  false, 30),
  (1, 'Set Up Business Address',            'Use a registered agent or virtual office — not your home address.',                            'business_setup', 2, 5,  false, 20),
  (1, 'Get a DUNS Number',                  'Register with Dun & Bradstreet to start building business credit history.',                     'credit',         2, 5,  false, 15),
  (2, 'Pull All 3 Credit Reports',          'Request reports from Experian, Equifax, and TransUnion. Review for errors.',                   'credit',         1, 8,  true,  20),
  (2, 'Dispute Negative Items',             'Submit dispute letters for inaccurate or unverifiable negative items on your reports.',         'credit',         1, 12, true,  45),
  (2, 'Reduce Credit Utilization Below 10%','Pay down balances to under 10% of limits. This is the single biggest score booster.',          'credit',         1, 10, false, 10),
  (2, 'Add Authorized User Tradelines',     'Ask a trusted person to add you as an authorized user on an aged, low-utilization account.',   'credit',         2, 8,  false, 15),
  (3, 'Apply for Net-30 Vendor Accounts',   'Open accounts with Uline, Quill, and Grainger. They report to business bureaus.',              'funding',        2, 6,  false, 30),
  (3, 'Establish Business Credit Score',    'After 3–6 months of vendor payments, check Dun & Bradstreet and Experian Business scores.',   'credit',         2, 6,  false, 10),
  (3, 'Prepare Business Financial Package', '2 years of business bank statements, P&L, and balance sheet ready for lenders.',              'funding',        2, 8,  false, 120)
ON CONFLICT DO NOTHING;

-- =============================================================================
-- STORAGE BUCKET: documents
-- Creates the public bucket for client document uploads
-- =============================================================================

INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
  'documents',
  'documents',
  true,
  52428800,  -- 50 MB per file
  ARRAY['application/pdf','image/jpeg','image/png','image/webp','application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document']
) ON CONFLICT (id) DO NOTHING;

-- RLS on storage objects: users can upload to their own folder, read their own files
DROP POLICY IF EXISTS "users_upload_own_docs" ON storage.objects;
DROP POLICY IF EXISTS "users_read_own_docs"   ON storage.objects;
DROP POLICY IF EXISTS "admin_read_all_docs"   ON storage.objects;
DROP POLICY IF EXISTS "users_delete_own_docs" ON storage.objects;

CREATE POLICY "users_upload_own_docs"
  ON storage.objects FOR INSERT
  WITH CHECK (bucket_id = 'documents' AND (storage.foldername(name))[1] = auth.uid()::text);

CREATE POLICY "users_read_own_docs"
  ON storage.objects FOR SELECT
  USING (bucket_id = 'documents' AND (storage.foldername(name))[1] = auth.uid()::text);

CREATE POLICY "admin_read_all_docs"
  ON storage.objects FOR SELECT
  USING (bucket_id = 'documents' AND is_admin());

CREATE POLICY "users_delete_own_docs"
  ON storage.objects FOR DELETE
  USING (bucket_id = 'documents' AND (storage.foldername(name))[1] = auth.uid()::text);

-- =============================================================================
-- ADMIN ACCOUNT SCAFFOLD
-- Note: Create the auth user for rayscentro@yahoo.com via Supabase Dashboard
-- (Authentication → Users → Invite User), then run this to set super_admin role:
--
-- UPDATE user_profiles SET role = 'super_admin' WHERE id = '<paste-user-uuid-here>';
--
-- =============================================================================
