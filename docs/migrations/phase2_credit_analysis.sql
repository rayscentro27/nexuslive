-- Phase 2: credit_analysis_results table
-- Stores structured output from credit_report_analysis worker
-- SAFE: new table only, no changes to existing tables

CREATE TABLE IF NOT EXISTS public.credit_analysis_results (
  id                    UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id             UUID        NOT NULL,
  customer_id           UUID        NOT NULL,
  job_id                UUID,

  -- Scored output
  credit_score_estimate INT,
  score_tier            TEXT,       -- poor|fair|good|very_good|exceptional
  risk_level            TEXT,       -- low|medium|high

  -- Account detail (JSONB arrays)
  negative_items        JSONB       DEFAULT '[]',
  positive_items        JSONB       DEFAULT '[]',
  recommendations       JSONB       DEFAULT '[]',

  -- Metrics
  utilization_pct       NUMERIC,
  total_accounts        INT,
  delinquent_accounts   INT,
  inquiries_90d         INT,

  -- Raw LLM output for audit trail
  raw_analysis          TEXT,

  -- Phase 1 standard fields
  schema_version        INT         DEFAULT 1,
  review_status         TEXT        DEFAULT 'unreviewed',
  expires_at            TIMESTAMPTZ,
  created_at            TIMESTAMPTZ DEFAULT now()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_credit_analysis_tenant    ON credit_analysis_results(tenant_id);
CREATE INDEX IF NOT EXISTS idx_credit_analysis_customer  ON credit_analysis_results(customer_id);
CREATE INDEX IF NOT EXISTS idx_credit_analysis_review    ON credit_analysis_results(review_status) WHERE review_status = 'unreviewed';
CREATE INDEX IF NOT EXISTS idx_credit_analysis_expires   ON credit_analysis_results(expires_at) WHERE expires_at IS NOT NULL;

-- Verify
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'credit_analysis_results'
ORDER BY ordinal_position;
