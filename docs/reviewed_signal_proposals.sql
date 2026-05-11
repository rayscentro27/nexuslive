-- =============================================================================
-- Nexus Trading Lab — Reviewed Signal Proposals Table
-- Apply via: Supabase Dashboard → SQL Editor → Run
-- Safe to run multiple times (IF NOT EXISTS + ADD COLUMN IF NOT EXISTS).
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.reviewed_signal_proposals (
    id                   UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    signal_id            UUID,                         -- FK to tv_normalized_signals
    symbol               TEXT,
    side                 TEXT,
    timeframe            TEXT,
    strategy_id          TEXT,
    asset_type           TEXT        NOT NULL DEFAULT 'forex'
                                     CHECK (asset_type IN ('forex', 'options')),

    -- Price levels (forex; NULL for options)
    entry_price          NUMERIC,
    stop_loss            NUMERIC,
    take_profit          NUMERIC,

    -- Options fields (NULL for forex)
    underlying           TEXT,
    expiration_note      TEXT,
    strike_note          TEXT,
    premium_estimate     TEXT,
    delta_guidance       TEXT,
    theta_note           TEXT,
    vega_note            TEXT,
    iv_context           TEXT,
    webull_note          TEXT,

    -- AI analyst output
    ai_confidence        NUMERIC     CHECK (ai_confidence >= 0 AND ai_confidence <= 1),
    market_context       TEXT,
    research_context     TEXT,
    risk_notes           TEXT,
    recommendation       TEXT,

    -- Lifecycle
    status               TEXT        NOT NULL DEFAULT 'needs_review'
                                     CHECK (status IN ('proposed', 'blocked', 'needs_review')),
    trace_id             TEXT,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Add asset_type column if upgrading from an earlier schema
ALTER TABLE public.reviewed_signal_proposals
    ADD COLUMN IF NOT EXISTS asset_type TEXT NOT NULL DEFAULT 'forex';

-- Add options columns if upgrading
ALTER TABLE public.reviewed_signal_proposals ADD COLUMN IF NOT EXISTS underlying        TEXT;
ALTER TABLE public.reviewed_signal_proposals ADD COLUMN IF NOT EXISTS expiration_note   TEXT;
ALTER TABLE public.reviewed_signal_proposals ADD COLUMN IF NOT EXISTS strike_note       TEXT;
ALTER TABLE public.reviewed_signal_proposals ADD COLUMN IF NOT EXISTS premium_estimate  TEXT;
ALTER TABLE public.reviewed_signal_proposals ADD COLUMN IF NOT EXISTS delta_guidance    TEXT;
ALTER TABLE public.reviewed_signal_proposals ADD COLUMN IF NOT EXISTS theta_note        TEXT;
ALTER TABLE public.reviewed_signal_proposals ADD COLUMN IF NOT EXISTS vega_note         TEXT;
ALTER TABLE public.reviewed_signal_proposals ADD COLUMN IF NOT EXISTS iv_context        TEXT;
ALTER TABLE public.reviewed_signal_proposals ADD COLUMN IF NOT EXISTS webull_note       TEXT;

CREATE INDEX IF NOT EXISTS idx_rsp_signal_id   ON public.reviewed_signal_proposals (signal_id);
CREATE INDEX IF NOT EXISTS idx_rsp_status      ON public.reviewed_signal_proposals (status);
CREATE INDEX IF NOT EXISTS idx_rsp_symbol      ON public.reviewed_signal_proposals (symbol);
CREATE INDEX IF NOT EXISTS idx_rsp_asset_type  ON public.reviewed_signal_proposals (asset_type);
CREATE INDEX IF NOT EXISTS idx_rsp_created_at  ON public.reviewed_signal_proposals (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_rsp_trace_id    ON public.reviewed_signal_proposals (trace_id);

COMMENT ON TABLE  public.reviewed_signal_proposals IS 'AI analyst proposals. Covers forex (entry/SL/TP) and options (expiry/strike/premium). No execution — analysis only.';
COMMENT ON COLUMN public.reviewed_signal_proposals.asset_type    IS 'forex | options';
COMMENT ON COLUMN public.reviewed_signal_proposals.status        IS 'proposed | blocked | needs_review';
COMMENT ON COLUMN public.reviewed_signal_proposals.ai_confidence IS '0.0–1.0 AI confidence score.';

-- =============================================================================
-- Verify:
-- SELECT symbol, side, asset_type, status, ai_confidence, created_at
-- FROM reviewed_signal_proposals ORDER BY created_at DESC LIMIT 10;
-- =============================================================================
