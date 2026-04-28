-- ── research_artifacts extensions ────────────────────────────────────────────
-- Phase 7: Nexus Brain Research Ingestion Lab
-- Run this in Supabase Dashboard SQL editor if research_artifacts already exists
-- with fewer columns. Safe to re-run — ALTER TABLE ADD COLUMN IF NOT EXISTS.
-- ─────────────────────────────────────────────────────────────────────────────

-- If the table doesn't exist yet, create it fully:
CREATE TABLE IF NOT EXISTS research_artifacts (
  id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  source        TEXT        NOT NULL,
  source_type   TEXT        NOT NULL DEFAULT 'youtube_channel',
  source_url    TEXT,
  topic         TEXT        NOT NULL,
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

-- If the table already exists, add any missing columns:
ALTER TABLE research_artifacts ADD COLUMN IF NOT EXISTS source_type      TEXT    DEFAULT 'youtube_channel';
ALTER TABLE research_artifacts ADD COLUMN IF NOT EXISTS source_url       TEXT;
ALTER TABLE research_artifacts ADD COLUMN IF NOT EXISTS topic            TEXT;
ALTER TABLE research_artifacts ADD COLUMN IF NOT EXISTS subtheme         TEXT;
ALTER TABLE research_artifacts ADD COLUMN IF NOT EXISTS subthemes        JSONB   DEFAULT '[]';
ALTER TABLE research_artifacts ADD COLUMN IF NOT EXISTS summary          TEXT;
ALTER TABLE research_artifacts ADD COLUMN IF NOT EXISTS content          TEXT;
ALTER TABLE research_artifacts ADD COLUMN IF NOT EXISTS key_points       JSONB   DEFAULT '[]';
ALTER TABLE research_artifacts ADD COLUMN IF NOT EXISTS action_items     JSONB   DEFAULT '[]';
ALTER TABLE research_artifacts ADD COLUMN IF NOT EXISTS risk_warnings    JSONB   DEFAULT '[]';
ALTER TABLE research_artifacts ADD COLUMN IF NOT EXISTS opportunity_notes JSONB  DEFAULT '[]';
ALTER TABLE research_artifacts ADD COLUMN IF NOT EXISTS published_at     DATE;
ALTER TABLE research_artifacts ADD COLUMN IF NOT EXISTS trace_id         UUID;

-- Indexes (safe to re-run)
CREATE INDEX IF NOT EXISTS research_artifacts_topic_idx      ON research_artifacts (topic);
CREATE INDEX IF NOT EXISTS research_artifacts_subtheme_idx   ON research_artifacts (subtheme);
CREATE INDEX IF NOT EXISTS research_artifacts_source_idx     ON research_artifacts (source);
CREATE INDEX IF NOT EXISTS research_artifacts_trace_id_idx   ON research_artifacts (trace_id);
CREATE INDEX IF NOT EXISTS research_artifacts_created_at_idx ON research_artifacts (created_at DESC);

-- Validation:
-- SELECT column_name, data_type FROM information_schema.columns
--   WHERE table_name = 'research_artifacts' ORDER BY ordinal_position;
-- SELECT topic, COUNT(*) FROM research_artifacts GROUP BY topic ORDER BY COUNT(*) DESC;
