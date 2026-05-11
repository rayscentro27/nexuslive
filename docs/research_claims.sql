-- ── research_claims ───────────────────────────────────────────────────────────
-- Phase 7: Nexus Brain Research Ingestion Lab
-- Structured claim extraction from research artifacts.
-- Each row is a single atomic claim, insight, tactic, or warning extracted
-- from a transcript by the OpenClaw claim extractor (or keyword fallback).
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS research_claims (
  id          UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
  source      TEXT          NOT NULL,
  topic       TEXT          NOT NULL CHECK (topic IN (
    'trading',
    'credit_repair',
    'grant_research',
    'business_opportunities',
    'crm_automation',
    'general_business_intelligence'
  )),
  subtheme    TEXT,
  claim_text  TEXT          NOT NULL,
  claim_type  TEXT          NOT NULL DEFAULT 'strategy' CHECK (claim_type IN (
    'strategy',
    'workflow',
    'warning',
    'opportunity',
    'framework'
  )),
  confidence  DECIMAL(4,3)  NOT NULL DEFAULT 0.5
                            CHECK (confidence >= 0 AND confidence <= 1),
  trace_id    UUID,
  created_at  TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS research_claims_topic_idx
  ON research_claims (topic);

CREATE INDEX IF NOT EXISTS research_claims_claim_type_idx
  ON research_claims (claim_type);

CREATE INDEX IF NOT EXISTS research_claims_confidence_idx
  ON research_claims (confidence DESC);

CREATE INDEX IF NOT EXISTS research_claims_trace_id_idx
  ON research_claims (trace_id);

CREATE INDEX IF NOT EXISTS research_claims_created_at_idx
  ON research_claims (created_at DESC);

-- Validation:
-- SELECT topic, claim_type, COUNT(*) FROM research_claims
--   GROUP BY topic, claim_type ORDER BY COUNT(*) DESC;
-- SELECT source, claim_text, confidence FROM research_claims
--   ORDER BY confidence DESC LIMIT 20;
