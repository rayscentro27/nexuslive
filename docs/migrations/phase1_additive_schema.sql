-- Phase 1: Additive Schema Fields
-- Freshness, versioning, approval layer
-- SAFE: additive only, no breaking changes, all columns have defaults
-- Apply in Supabase SQL editor: https://supabase.com/dashboard/project/ftxbphwlqskimdnqcfxh/sql

-- ============================================================
-- messages table — enrichment versioning + approval
-- ============================================================

ALTER TABLE messages
  ADD COLUMN IF NOT EXISTS ai_enrich_version   INT          DEFAULT 1,
  ADD COLUMN IF NOT EXISTS ai_enriched_at      TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS ai_review_status    VARCHAR(20)  DEFAULT 'unreviewed',
  ADD COLUMN IF NOT EXISTS ai_reviewed_at      TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS ai_review_notes     TEXT,
  ADD COLUMN IF NOT EXISTS ai_expires_at       TIMESTAMPTZ;

-- Auto-populate ai_enriched_at for existing enriched rows
UPDATE messages
SET ai_enriched_at = created_at
WHERE ai_enrich_status = 'complete'
  AND ai_enriched_at IS NULL;

-- ============================================================
-- research table — freshness, versioning, approval
-- ============================================================

ALTER TABLE research
  ADD COLUMN IF NOT EXISTS schema_version  INT          DEFAULT 1,
  ADD COLUMN IF NOT EXISTS review_status   VARCHAR(20)  DEFAULT 'unreviewed',
  ADD COLUMN IF NOT EXISTS reviewed_at     TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS review_notes    TEXT,
  ADD COLUMN IF NOT EXISTS expires_at      TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS updated_at      TIMESTAMPTZ  DEFAULT now();

-- Set expiration to 7 days for trading research (market conditions change fast)
UPDATE research
SET expires_at = created_at + INTERVAL '7 days'
WHERE expires_at IS NULL;

-- ============================================================
-- job_results table — schema version for output evolution
-- ============================================================

ALTER TABLE job_results
  ADD COLUMN IF NOT EXISTS schema_version  INT  DEFAULT 1;

-- ============================================================
-- Performance index for approval workflow queries
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_messages_ai_review_status
  ON messages(ai_review_status)
  WHERE ai_review_status = 'unreviewed';

CREATE INDEX IF NOT EXISTS idx_research_review_status
  ON research(review_status)
  WHERE review_status = 'unreviewed';

CREATE INDEX IF NOT EXISTS idx_research_expires_at
  ON research(expires_at)
  WHERE expires_at IS NOT NULL;

-- ============================================================
-- Verify
-- ============================================================

SELECT
  column_name,
  data_type,
  column_default
FROM information_schema.columns
WHERE table_name IN ('messages', 'research', 'job_results')
  AND column_name IN (
    'ai_enrich_version', 'ai_enriched_at', 'ai_review_status',
    'ai_expires_at', 'schema_version', 'review_status', 'expires_at'
  )
ORDER BY table_name, column_name;
