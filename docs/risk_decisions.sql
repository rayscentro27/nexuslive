-- =============================================================================
-- Nexus Trading Lab — Risk Decisions Table
-- Apply via: Supabase Dashboard → SQL Editor → Run
-- Safe to run multiple times (IF NOT EXISTS + ADD COLUMN IF NOT EXISTS).
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.risk_decisions (
    id                   UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    proposal_id          UUID,                         -- FK to reviewed_signal_proposals
    signal_id            UUID,                         -- FK to tv_normalized_signals
    symbol               TEXT,
    side                 TEXT,
    asset_type           TEXT        NOT NULL DEFAULT 'forex'
                                     CHECK (asset_type IN ('forex', 'options')),

    -- Decision (100-penalty scoring system)
    decision             TEXT        NOT NULL
                                     CHECK (decision IN ('approved', 'manual_review', 'blocked')),
    risk_score           NUMERIC,                      -- 0–100; higher = safer (less penalized)
    risk_flags           JSONB       NOT NULL DEFAULT '[]'::jsonb,  -- array of flag strings

    -- Computed metrics
    rr_ratio             NUMERIC,
    daily_pnl_used       NUMERIC,
    open_positions_count INTEGER,

    -- Legacy binary checks (kept for compatibility)
    rr_ok                BOOLEAN,
    prices_ok            BOOLEAN,
    daily_pnl_ok         BOOLEAN,
    positions_ok         BOOLEAN,
    no_duplicate         BOOLEAN,

    rejection_reason     TEXT,                         -- human-readable summary if blocked
    trace_id             TEXT,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Upgrade: add new columns if table already exists from earlier schema
ALTER TABLE public.risk_decisions ADD COLUMN IF NOT EXISTS asset_type TEXT NOT NULL DEFAULT 'forex';
ALTER TABLE public.risk_decisions ADD COLUMN IF NOT EXISTS decision   TEXT;
ALTER TABLE public.risk_decisions ADD COLUMN IF NOT EXISTS risk_flags JSONB NOT NULL DEFAULT '[]'::jsonb;

-- Back-fill decision from legacy status column if upgrading
UPDATE public.risk_decisions
   SET decision = CASE
       WHEN decision IS NULL AND (SELECT column_name FROM information_schema.columns
            WHERE table_name='risk_decisions' AND column_name='status' LIMIT 1) IS NOT NULL
       THEN status
       ELSE decision
   END
 WHERE decision IS NULL;

CREATE INDEX IF NOT EXISTS idx_rd_proposal_id  ON public.risk_decisions (proposal_id);
CREATE INDEX IF NOT EXISTS idx_rd_signal_id    ON public.risk_decisions (signal_id);
CREATE INDEX IF NOT EXISTS idx_rd_decision     ON public.risk_decisions (decision);
CREATE INDEX IF NOT EXISTS idx_rd_symbol       ON public.risk_decisions (symbol);
CREATE INDEX IF NOT EXISTS idx_rd_asset_type   ON public.risk_decisions (asset_type);
CREATE INDEX IF NOT EXISTS idx_rd_created_at   ON public.risk_decisions (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_rd_trace_id     ON public.risk_decisions (trace_id);
CREATE INDEX IF NOT EXISTS idx_rd_risk_flags   ON public.risk_decisions USING GIN (risk_flags);

COMMENT ON TABLE  public.risk_decisions IS '100-penalty risk scoring results. Approved ≥70, manual_review 40–69, blocked <40. No execution — analysis only.';
COMMENT ON COLUMN public.risk_decisions.decision    IS 'approved | manual_review | blocked';
COMMENT ON COLUMN public.risk_decisions.risk_score  IS '0–100. Starts at 100, penalties subtracted per flag.';
COMMENT ON COLUMN public.risk_decisions.risk_flags  IS 'Array of penalty flag strings: poor_rr, low_confidence, high_spread, unknown_strategy, duplicate_signal, conflict, missing_sl, low_rr_options.';
COMMENT ON COLUMN public.risk_decisions.rr_ratio    IS 'Reward:Risk ratio (e.g. 2.5 = 1:2.5).';

-- =============================================================================
-- Verify:
-- SELECT symbol, side, asset_type, decision, risk_score, risk_flags, created_at
-- FROM risk_decisions ORDER BY created_at DESC LIMIT 10;
-- =============================================================================
