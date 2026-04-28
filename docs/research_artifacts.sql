-- ── research_artifacts ────────────────────────────────────────────────────────
-- Phase 7: Nexus Brain Research Ingestion Lab
-- Multi-domain research artifact storage (extends the existing research table
-- with domain classification, subtheme tagging, and structured output fields).
-- Domains: trading, credit_repair, grant_research, business_opportunities,
--          crm_automation, general_business_intelligence
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS research_artifacts (
  id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  source        TEXT        NOT NULL,
  source_type   TEXT        NOT NULL DEFAULT 'youtube_channel',
  source_url    TEXT,
  topic         TEXT        NOT NULL CHECK (topic IN (
    'trading',
    'credit_repair',
    'grant_research',
    'business_opportunities',
    'crm_automation',
    'general_business_intelligence'
  )),
  subtheme      TEXT,
  subthemes     JSONB       NOT NULL DEFAULT '[]',
  title         TEXT        NOT NULL,
  summary       TEXT,
  content       TEXT,
  key_points    JSONB       NOT NULL DEFAULT '[]',
  action_items  JSONB       NOT NULL DEFAULT '[]',
  risk_warnings JSONB       NOT NULL DEFAULT '[]',
  opportunity_notes JSONB   NOT NULL DEFAULT '[]',
  published_at  DATE,
  trace_id      UUID,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS research_artifacts_topic_idx
  ON research_artifacts (topic);

CREATE INDEX IF NOT EXISTS research_artifacts_subtheme_idx
  ON research_artifacts (subtheme);

CREATE INDEX IF NOT EXISTS research_artifacts_source_idx
  ON research_artifacts (source);

CREATE INDEX IF NOT EXISTS research_artifacts_trace_id_idx
  ON research_artifacts (trace_id);

CREATE INDEX IF NOT EXISTS research_artifacts_created_at_idx
  ON research_artifacts (created_at DESC);

-- Validation:
-- SELECT topic, COUNT(*) FROM research_artifacts GROUP BY topic ORDER BY COUNT(*) DESC;
-- SELECT title, topic, subtheme, created_at FROM research_artifacts ORDER BY created_at DESC LIMIT 20;
