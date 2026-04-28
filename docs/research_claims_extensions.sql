-- ── research_claims extensions ────────────────────────────────────────────────
-- Phase 7: Nexus Brain Research Ingestion Lab
-- Run this in Supabase Dashboard SQL editor if research_claims already exists
-- with fewer columns. Safe to re-run — ALTER TABLE ADD COLUMN IF NOT EXISTS.
-- ─────────────────────────────────────────────────────────────────────────────

-- If the table doesn't exist yet, create it fully:
CREATE TABLE IF NOT EXISTS research_claims (
  id          UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
  source      TEXT          NOT NULL,
  topic       TEXT          NOT NULL,
  subtheme    TEXT,
  claim_text  TEXT          NOT NULL,
  claim_type  TEXT          NOT NULL DEFAULT 'strategy',
  confidence  DECIMAL(4,3)  NOT NULL DEFAULT 0.5,
  trace_id    UUID,
  created_at  TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

-- If the table already exists, add any missing columns:
ALTER TABLE research_claims ADD COLUMN IF NOT EXISTS topic      TEXT;
ALTER TABLE research_claims ADD COLUMN IF NOT EXISTS subtheme   TEXT;
ALTER TABLE research_claims ADD COLUMN IF NOT EXISTS claim_type TEXT    DEFAULT 'strategy';
ALTER TABLE research_claims ADD COLUMN IF NOT EXISTS confidence DECIMAL(4,3) DEFAULT 0.5;
ALTER TABLE research_claims ADD COLUMN IF NOT EXISTS trace_id   UUID;

-- Indexes (safe to re-run)
CREATE INDEX IF NOT EXISTS research_claims_topic_idx      ON research_claims (topic);
CREATE INDEX IF NOT EXISTS research_claims_claim_type_idx ON research_claims (claim_type);
CREATE INDEX IF NOT EXISTS research_claims_confidence_idx ON research_claims (confidence DESC);
CREATE INDEX IF NOT EXISTS research_claims_trace_id_idx   ON research_claims (trace_id);
CREATE INDEX IF NOT EXISTS research_claims_created_at_idx ON research_claims (created_at DESC);

-- Also create research_relationships table (Phase 7 graph enrichment):
CREATE TABLE IF NOT EXISTS research_relationships (
  id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  from_node   TEXT        NOT NULL,
  from_type   TEXT        NOT NULL,
  to_node     TEXT        NOT NULL,
  to_type     TEXT        NOT NULL,
  relation    TEXT        NOT NULL,
  source      TEXT,
  trace_id    UUID,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS research_relationships_from_idx      ON research_relationships (from_node, from_type);
CREATE INDEX IF NOT EXISTS research_relationships_to_idx        ON research_relationships (to_node, to_type);
CREATE INDEX IF NOT EXISTS research_relationships_relation_idx  ON research_relationships (relation);
CREATE INDEX IF NOT EXISTS research_relationships_created_at_idx ON research_relationships (created_at DESC);

-- Validation:
-- SELECT column_name, data_type FROM information_schema.columns
--   WHERE table_name = 'research_claims' ORDER BY ordinal_position;
-- SELECT topic, claim_type, COUNT(*), ROUND(AVG(confidence),3) AS avg_conf
--   FROM research_claims GROUP BY topic, claim_type ORDER BY COUNT(*) DESC;
