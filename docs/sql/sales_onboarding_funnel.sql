-- ============================================================
-- Sales Agent + Onboarding Agent + Support Agent
-- Funnel Automation + Multi-Business + Decision Engine
-- Run in Supabase SQL editor
-- ============================================================

-- 1. Lead Profiles
CREATE TABLE IF NOT EXISTS lead_profiles (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  external_id  text,
  channel      text        DEFAULT 'telegram',
  name         text,
  contact_info text,
  interest     text,
  status       text        DEFAULT 'new',
  notes        text,
  created_at   timestamptz DEFAULT now(),
  updated_at   timestamptz DEFAULT now(),
  UNIQUE(external_id, channel)
);

CREATE INDEX IF NOT EXISTS idx_leads_status  ON lead_profiles(status);
CREATE INDEX IF NOT EXISTS idx_leads_channel ON lead_profiles(channel);
CREATE INDEX IF NOT EXISTS idx_leads_updated ON lead_profiles(updated_at DESC);

-- 2. Sales Conversations
CREATE TABLE IF NOT EXISTS sales_conversations (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  lead_id         uuid,
  client_id       uuid,
  channel         text        DEFAULT 'telegram',
  status          text        DEFAULT 'active',
  intent          text,
  message_count   integer     DEFAULT 0,
  last_message_at timestamptz,
  converted_at    timestamptz,
  created_at      timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_sales_conv_lead    ON sales_conversations(lead_id);
CREATE INDEX IF NOT EXISTS idx_sales_conv_client  ON sales_conversations(client_id);
CREATE INDEX IF NOT EXISTS idx_sales_conv_status  ON sales_conversations(status);
CREATE INDEX IF NOT EXISTS idx_sales_conv_created ON sales_conversations(created_at DESC);

-- 3. Conversion Events
CREATE TABLE IF NOT EXISTS conversion_events (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  lead_id      uuid,
  client_id    uuid,
  event_type   text        NOT NULL,
  metadata     jsonb       DEFAULT '{}'::jsonb,
  created_at   timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_conv_events_lead    ON conversion_events(lead_id);
CREATE INDEX IF NOT EXISTS idx_conv_events_client  ON conversion_events(client_id);
CREATE INDEX IF NOT EXISTS idx_conv_events_type    ON conversion_events(event_type);
CREATE INDEX IF NOT EXISTS idx_conv_events_created ON conversion_events(created_at DESC);

-- 4. Onboarding Sessions
CREATE TABLE IF NOT EXISTS onboarding_sessions (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id    uuid        NOT NULL,
  current_step text        DEFAULT 'welcome',
  status       text        DEFAULT 'active',
  started_at   timestamptz DEFAULT now(),
  completed_at timestamptz,
  created_at   timestamptz DEFAULT now(),
  UNIQUE(client_id)
);

CREATE INDEX IF NOT EXISTS idx_onboard_sessions_client  ON onboarding_sessions(client_id);
CREATE INDEX IF NOT EXISTS idx_onboard_sessions_status  ON onboarding_sessions(status);
CREATE INDEX IF NOT EXISTS idx_onboard_sessions_step    ON onboarding_sessions(current_step);

-- 5. Onboarding Steps
CREATE TABLE IF NOT EXISTS onboarding_steps (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id   uuid        NOT NULL REFERENCES onboarding_sessions(id) ON DELETE CASCADE,
  step_name    text        NOT NULL,
  step_order   integer     NOT NULL,
  status       text        DEFAULT 'pending',
  completed_at timestamptz,
  notes        text,
  created_at   timestamptz DEFAULT now(),
  UNIQUE(session_id, step_name)
);

CREATE INDEX IF NOT EXISTS idx_onboard_steps_session ON onboarding_steps(session_id);
CREATE INDEX IF NOT EXISTS idx_onboard_steps_status  ON onboarding_steps(status);

-- 6. Support Threads
CREATE TABLE IF NOT EXISTS support_threads (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id   uuid,
  lead_id     uuid,
  subject     text,
  status      text        DEFAULT 'open',
  category    text,
  priority    text        DEFAULT 'normal',
  resolved_at timestamptz,
  created_at  timestamptz DEFAULT now(),
  updated_at  timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_support_threads_client   ON support_threads(client_id);
CREATE INDEX IF NOT EXISTS idx_support_threads_status   ON support_threads(status);
CREATE INDEX IF NOT EXISTS idx_support_threads_priority ON support_threads(priority);
CREATE INDEX IF NOT EXISTS idx_support_threads_updated  ON support_threads(updated_at DESC);

-- 7. Support Messages
CREATE TABLE IF NOT EXISTS support_messages (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  thread_id   uuid        NOT NULL REFERENCES support_threads(id) ON DELETE CASCADE,
  sender_role text        NOT NULL,
  content     text        NOT NULL,
  created_at  timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_support_messages_thread  ON support_messages(thread_id);
CREATE INDEX IF NOT EXISTS idx_support_messages_created ON support_messages(created_at DESC);

-- 8. Support Resolutions
CREATE TABLE IF NOT EXISTS support_resolutions (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  thread_id   uuid        NOT NULL REFERENCES support_threads(id) ON DELETE CASCADE,
  resolution  text        NOT NULL,
  resolved_by text        DEFAULT 'ai_agent',
  created_at  timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_support_resolutions_thread ON support_resolutions(thread_id);

-- 9. Funnel Events
CREATE TABLE IF NOT EXISTS funnel_events (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id    uuid,
  lead_id      uuid,
  stage        text        NOT NULL,
  event_source text,
  metadata     jsonb       DEFAULT '{}'::jsonb,
  created_at   timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_funnel_events_client  ON funnel_events(client_id);
CREATE INDEX IF NOT EXISTS idx_funnel_events_stage   ON funnel_events(stage);
CREATE INDEX IF NOT EXISTS idx_funnel_events_created ON funnel_events(created_at DESC);

-- 10. Funnel Stage Tracking (current stage per client)
CREATE TABLE IF NOT EXISTS funnel_stage_tracking (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id        uuid        NOT NULL,
  current_stage    text        NOT NULL DEFAULT 'lead_captured',
  previous_stage   text,
  days_in_stage    integer     DEFAULT 0,
  stage_entered_at timestamptz DEFAULT now(),
  last_activity_at timestamptz DEFAULT now(),
  created_at       timestamptz DEFAULT now(),
  UNIQUE(client_id)
);

CREATE INDEX IF NOT EXISTS idx_funnel_tracking_client ON funnel_stage_tracking(client_id);
CREATE INDEX IF NOT EXISTS idx_funnel_tracking_stage  ON funnel_stage_tracking(current_stage);
CREATE INDEX IF NOT EXISTS idx_funnel_tracking_active ON funnel_stage_tracking(last_activity_at DESC);

-- 11. Business Units
CREATE TABLE IF NOT EXISTS business_units (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  unit_name   text        NOT NULL UNIQUE,
  unit_type   text        NOT NULL,
  status      text        DEFAULT 'active',
  description text,
  created_at  timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_biz_units_type   ON business_units(unit_type);
CREATE INDEX IF NOT EXISTS idx_biz_units_status ON business_units(status);

-- Seed default business units
INSERT INTO business_units (unit_name, unit_type, description) VALUES
  ('nexus_funding',   'funding',           'Business funding consulting — 10% commission on funded amount'),
  ('nexus_trading',   'trading_education', 'Trading education and signal service'),
  ('nexus_grants',    'grants',            'Government grant research and application assistance'),
  ('nexus_saas',      'saas',              'SaaS tools and AI automation products')
ON CONFLICT (unit_name) DO NOTHING;

-- 12. Business Configs
CREATE TABLE IF NOT EXISTS business_configs (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  unit_id      uuid        NOT NULL REFERENCES business_units(id) ON DELETE CASCADE,
  config_key   text        NOT NULL,
  config_value text,
  created_at   timestamptz DEFAULT now(),
  UNIQUE(unit_id, config_key)
);

CREATE INDEX IF NOT EXISTS idx_biz_configs_unit ON business_configs(unit_id);
CREATE INDEX IF NOT EXISTS idx_biz_configs_key  ON business_configs(config_key);

-- 13. Decisions
CREATE TABLE IF NOT EXISTS decisions (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  decision_type text        NOT NULL,
  context       jsonb       DEFAULT '{}'::jsonb,
  action        text        NOT NULL,
  rationale     text,
  confidence    numeric     DEFAULT 0.5,
  status        text        DEFAULT 'pending',
  safety_level  text        DEFAULT 'low',
  executed_at   timestamptz,
  created_at    timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_decisions_type    ON decisions(decision_type);
CREATE INDEX IF NOT EXISTS idx_decisions_status  ON decisions(status);
CREATE INDEX IF NOT EXISTS idx_decisions_safety  ON decisions(safety_level);
CREATE INDEX IF NOT EXISTS idx_decisions_created ON decisions(created_at DESC);

-- 14. Decision Context
CREATE TABLE IF NOT EXISTS decision_context (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  decision_id  uuid        NOT NULL REFERENCES decisions(id) ON DELETE CASCADE,
  context_type text        NOT NULL,
  data         jsonb       DEFAULT '{}'::jsonb,
  created_at   timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_decision_ctx_decision ON decision_context(decision_id);
CREATE INDEX IF NOT EXISTS idx_decision_ctx_type     ON decision_context(context_type);
