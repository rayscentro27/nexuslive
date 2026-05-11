-- ============================================================
-- Agent Run Summaries + CEO Agent + Admin Commands + Source Registry
-- Run in Supabase SQL editor
-- ============================================================

-- 1. Agent Run Summaries
CREATE TABLE IF NOT EXISTS agent_run_summaries (
  id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  agent_name          text        NOT NULL,
  job_id              text,
  client_id           text,
  tenant_id           text,
  summary_type        text        NOT NULL,
  summary_text        text        NOT NULL,
  structured_payload  jsonb       DEFAULT '{}'::jsonb,
  status              text        DEFAULT 'completed',
  priority            text        DEFAULT 'medium',
  trigger_event_type  text,
  created_at          timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_run_summaries_agent    ON agent_run_summaries(agent_name);
CREATE INDEX IF NOT EXISTS idx_run_summaries_client   ON agent_run_summaries(client_id);
CREATE INDEX IF NOT EXISTS idx_run_summaries_type     ON agent_run_summaries(summary_type);
CREATE INDEX IF NOT EXISTS idx_run_summaries_priority ON agent_run_summaries(priority);
CREATE INDEX IF NOT EXISTS idx_run_summaries_created  ON agent_run_summaries(created_at DESC);

-- 2. Executive Briefings (CEO agent output)
CREATE TABLE IF NOT EXISTS executive_briefings (
  id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  brief_type          text        NOT NULL DEFAULT 'periodic',
  headline            text        NOT NULL,
  summary             text        NOT NULL,
  top_updates         jsonb       DEFAULT '[]'::jsonb,
  blockers            jsonb       DEFAULT '[]'::jsonb,
  recommended_actions jsonb       DEFAULT '[]'::jsonb,
  created_at          timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_briefings_type    ON executive_briefings(brief_type);
CREATE INDEX IF NOT EXISTS idx_briefings_created ON executive_briefings(created_at DESC);

-- 3. Admin Commands
CREATE TABLE IF NOT EXISTS admin_commands (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  raw_input         text        NOT NULL,
  parsed_intent     text,
  command_type      text,
  target_agent      text,
  payload           jsonb       DEFAULT '{}'::jsonb,
  validation_status text        DEFAULT 'pending',
  queue_status      text        DEFAULT 'queued',
  created_by        text        DEFAULT 'admin',
  created_at        timestamptz DEFAULT now(),
  processed_at      timestamptz
);

CREATE INDEX IF NOT EXISTS idx_admin_commands_type     ON admin_commands(command_type);
CREATE INDEX IF NOT EXISTS idx_admin_commands_vstatus  ON admin_commands(validation_status);
CREATE INDEX IF NOT EXISTS idx_admin_commands_qstatus  ON admin_commands(queue_status);
CREATE INDEX IF NOT EXISTS idx_admin_commands_created  ON admin_commands(created_at DESC);

-- 4. Research Sources
CREATE TABLE IF NOT EXISTS research_sources (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  source_type text        NOT NULL,
  source_url  text        NOT NULL UNIQUE,
  label       text,
  domain      text,
  status      text        DEFAULT 'active',
  priority    text        DEFAULT 'medium',
  added_by    text        DEFAULT 'admin',
  created_at  timestamptz DEFAULT now(),
  updated_at  timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_research_sources_type    ON research_sources(source_type);
CREATE INDEX IF NOT EXISTS idx_research_sources_status  ON research_sources(status);
CREATE INDEX IF NOT EXISTS idx_research_sources_domain  ON research_sources(domain);
CREATE INDEX IF NOT EXISTS idx_research_sources_created ON research_sources(created_at DESC);
