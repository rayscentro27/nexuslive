-- ============================================================
-- Enterprise Multi-Tenant + White-Label + Voice + Ads
-- API Gateway + Compliance + Audit
-- Run in Supabase SQL editor
-- ============================================================

-- 1. Organizations
CREATE TABLE IF NOT EXISTS organizations (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_name    text        NOT NULL UNIQUE,
  org_type    text        DEFAULT 'client',
  status      text        DEFAULT 'active',
  owner_email text,
  created_at  timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_orgs_type   ON organizations(org_type);
CREATE INDEX IF NOT EXISTS idx_orgs_status ON organizations(status);

-- Seed default internal org
INSERT INTO organizations (org_name, org_type, owner_email) VALUES
  ('nexus_internal', 'internal', 'admin@nexus.ai')
ON CONFLICT (org_name) DO NOTHING;

-- 2. Organization Users
CREATE TABLE IF NOT EXISTS organization_users (
  id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id     uuid        NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  user_id    uuid        NOT NULL,
  role       text        NOT NULL DEFAULT 'client',
  status     text        DEFAULT 'active',
  created_at timestamptz DEFAULT now(),
  UNIQUE(org_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_org_users_org  ON organization_users(org_id);
CREATE INDEX IF NOT EXISTS idx_org_users_user ON organization_users(user_id);
CREATE INDEX IF NOT EXISTS idx_org_users_role ON organization_users(role);

-- 3. Branding Configs
CREATE TABLE IF NOT EXISTS branding_configs (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id          uuid        NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  brand_name      text,
  logo_url        text,
  primary_color   text        DEFAULT '#1a1a2e',
  secondary_color text        DEFAULT '#16213e',
  domain          text,
  support_email   text,
  telegram_handle text,
  created_at      timestamptz DEFAULT now(),
  updated_at      timestamptz DEFAULT now(),
  UNIQUE(org_id)
);

CREATE INDEX IF NOT EXISTS idx_branding_org ON branding_configs(org_id);

-- 4. Org Module Configs (enable/disable per org)
CREATE TABLE IF NOT EXISTS org_module_configs (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id      uuid        NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  module_name text        NOT NULL,
  enabled     boolean     DEFAULT true,
  config      jsonb       DEFAULT '{}'::jsonb,
  updated_at  timestamptz DEFAULT now(),
  UNIQUE(org_id, module_name)
);

CREATE INDEX IF NOT EXISTS idx_module_configs_org    ON org_module_configs(org_id);
CREATE INDEX IF NOT EXISTS idx_module_configs_module ON org_module_configs(module_name);

-- 5. Call Sessions
CREATE TABLE IF NOT EXISTS call_sessions (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id    uuid,
  lead_id      uuid,
  org_id       uuid,
  call_type    text        DEFAULT 'inbound',
  channel      text        DEFAULT 'telegram',
  status       text        DEFAULT 'open',
  outcome      text,
  duration_sec integer     DEFAULT 0,
  started_at   timestamptz DEFAULT now(),
  ended_at     timestamptz,
  created_at   timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_call_sessions_client  ON call_sessions(client_id);
CREATE INDEX IF NOT EXISTS idx_call_sessions_lead    ON call_sessions(lead_id);
CREATE INDEX IF NOT EXISTS idx_call_sessions_status  ON call_sessions(status);
CREATE INDEX IF NOT EXISTS idx_call_sessions_outcome ON call_sessions(outcome);
CREATE INDEX IF NOT EXISTS idx_call_sessions_created ON call_sessions(created_at DESC);

-- 6. Call Transcripts
CREATE TABLE IF NOT EXISTS call_transcripts (
  id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id uuid        NOT NULL REFERENCES call_sessions(id) ON DELETE CASCADE,
  speaker    text        NOT NULL,
  content    text        NOT NULL,
  turn_order integer     NOT NULL,
  created_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_call_transcripts_session ON call_transcripts(session_id);

-- 7. Call Outcomes
CREATE TABLE IF NOT EXISTS call_outcomes (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id   uuid        NOT NULL REFERENCES call_sessions(id) ON DELETE CASCADE,
  outcome_type text        NOT NULL,
  notes        text,
  next_action  text,
  follow_up_at timestamptz,
  created_at   timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_call_outcomes_session ON call_outcomes(session_id);
CREATE INDEX IF NOT EXISTS idx_call_outcomes_type    ON call_outcomes(outcome_type);

-- 8. Ad Campaigns
CREATE TABLE IF NOT EXISTS ad_campaigns (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id           uuid,
  campaign_name    text        NOT NULL,
  platform         text        NOT NULL,
  objective        text,
  status           text        DEFAULT 'draft',
  budget           numeric,
  target_audience  text,
  created_at       timestamptz DEFAULT now(),
  updated_at       timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_ad_campaigns_org      ON ad_campaigns(org_id);
CREATE INDEX IF NOT EXISTS idx_ad_campaigns_platform ON ad_campaigns(platform);
CREATE INDEX IF NOT EXISTS idx_ad_campaigns_status   ON ad_campaigns(status);

-- 9. Ad Creatives
CREATE TABLE IF NOT EXISTS ad_creatives (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  campaign_id       uuid        REFERENCES ad_campaigns(id) ON DELETE CASCADE,
  creative_type     text        NOT NULL,
  platform          text,
  content           text        NOT NULL,
  status            text        DEFAULT 'draft',
  performance_score numeric     DEFAULT 0,
  created_at        timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_ad_creatives_campaign ON ad_creatives(campaign_id);
CREATE INDEX IF NOT EXISTS idx_ad_creatives_type     ON ad_creatives(creative_type);
CREATE INDEX IF NOT EXISTS idx_ad_creatives_status   ON ad_creatives(status);

-- 10. API Keys
CREATE TABLE IF NOT EXISTS api_keys (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id       uuid,
  key_hash     text        NOT NULL UNIQUE,
  key_prefix   text        NOT NULL,
  label        text,
  scopes       jsonb       DEFAULT '[]'::jsonb,
  status       text        DEFAULT 'active',
  last_used_at timestamptz,
  expires_at   timestamptz,
  created_at   timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_api_keys_org    ON api_keys(org_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_hash   ON api_keys(key_hash);
CREATE INDEX IF NOT EXISTS idx_api_keys_status ON api_keys(status);

-- 11. API Usage Logs
CREATE TABLE IF NOT EXISTS api_usage_logs (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  api_key_id  uuid        REFERENCES api_keys(id),
  org_id      uuid,
  endpoint    text        NOT NULL,
  method      text        DEFAULT 'POST',
  status_code integer,
  response_ms integer,
  created_at  timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_api_usage_key     ON api_usage_logs(api_key_id);
CREATE INDEX IF NOT EXISTS idx_api_usage_org     ON api_usage_logs(org_id);
CREATE INDEX IF NOT EXISTS idx_api_usage_created ON api_usage_logs(created_at DESC);

-- 12. Audit Logs
CREATE TABLE IF NOT EXISTS audit_logs (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  actor_id    text,
  actor_type  text        DEFAULT 'system',
  action      text        NOT NULL,
  entity_type text,
  entity_id   text,
  org_id      uuid,
  details     jsonb       DEFAULT '{}'::jsonb,
  ip_address  text,
  created_at  timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_audit_actor      ON audit_logs(actor_id);
CREATE INDEX IF NOT EXISTS idx_audit_action     ON audit_logs(action);
CREATE INDEX IF NOT EXISTS idx_audit_entity     ON audit_logs(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_audit_org        ON audit_logs(org_id);
CREATE INDEX IF NOT EXISTS idx_audit_created    ON audit_logs(created_at DESC);

-- 13. Compliance Records
CREATE TABLE IF NOT EXISTS compliance_records (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  record_type      text        NOT NULL,
  client_id        uuid,
  org_id           uuid,
  content          text        NOT NULL,
  actor_id         text,
  acknowledged     boolean     DEFAULT false,
  acknowledged_at  timestamptz,
  created_at       timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_compliance_type    ON compliance_records(record_type);
CREATE INDEX IF NOT EXISTS idx_compliance_client  ON compliance_records(client_id);
CREATE INDEX IF NOT EXISTS idx_compliance_org     ON compliance_records(org_id);
CREATE INDEX IF NOT EXISTS idx_compliance_created ON compliance_records(created_at DESC);
