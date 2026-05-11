-- Phase 4: funding_card_results table
-- Stores AI-researched business funding card recommendations per customer

CREATE TABLE IF NOT EXISTS funding_card_results (
  id                      uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id               text        NOT NULL,
  customer_id             text        NOT NULL,
  job_id                  uuid,

  -- Input snapshot
  credit_score_input      integer,
  monthly_revenue_input   numeric,
  months_in_business      integer,
  industry                text,
  funding_goal            text,                         -- working_capital|equipment|expansion|cash_back

  -- Research results
  eligibility_tier        text,                         -- strong|good|fair|limited
  recommended_cards       jsonb       DEFAULT '[]',     -- array of card objects
  best_match_card         text,
  estimated_credit_limit  integer,
  total_available_credit  integer,
  approval_likelihood     text,                         -- high|medium|low
  funding_strategy        text,
  raw_research            text,

  -- Phase 1 standard fields
  schema_version          integer     NOT NULL DEFAULT 1,
  review_status           text        NOT NULL DEFAULT 'unreviewed', -- unreviewed|approved|rejected
  reviewed_at             timestamptz,
  review_notes            text,
  expires_at              timestamptz,

  created_at              timestamptz NOT NULL DEFAULT now()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_funding_card_results_tenant    ON funding_card_results (tenant_id);
CREATE INDEX IF NOT EXISTS idx_funding_card_results_customer  ON funding_card_results (customer_id);
CREATE INDEX IF NOT EXISTS idx_funding_card_results_review    ON funding_card_results (review_status) WHERE review_status = 'unreviewed';
CREATE INDEX IF NOT EXISTS idx_funding_card_results_expires   ON funding_card_results (expires_at);

-- RLS: tenants can only see their own rows
ALTER TABLE funding_card_results ENABLE ROW LEVEL SECURITY;

CREATE POLICY "tenant_isolation" ON funding_card_results
  USING (tenant_id = current_setting('app.tenant_id', true));
