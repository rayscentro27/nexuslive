-- =============================================================================
-- Nexus Trading Lab — Approval Queue Table
-- Apply via: Supabase Dashboard → SQL Editor → Run
-- Safe to run multiple times (IF NOT EXISTS).
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.approval_queue (
    id                   UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    proposal_id          UUID,                         -- FK to reviewed_signal_proposals
    signal_id            UUID,                         -- FK to tv_normalized_signals
    symbol               TEXT,
    side                 TEXT,
    asset_type           TEXT        NOT NULL DEFAULT 'forex'
                                     CHECK (asset_type IN ('forex', 'options')),
    strategy_id          TEXT,
    risk_score           NUMERIC,                      -- 0–100 from risk_decisions
    decision             TEXT        NOT NULL
                                     CHECK (decision IN ('approved', 'manual_review')),
    approval_status      TEXT        NOT NULL DEFAULT 'pending'
                                     CHECK (approval_status IN ('pending', 'approved', 'rejected')),
    approved_by          TEXT,                         -- optional: human identifier
    approved_at          TIMESTAMPTZ,
    rejection_note       TEXT,                         -- optional: reason if rejected
    trace_id             TEXT,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_aq_proposal_id      ON public.approval_queue (proposal_id);
CREATE INDEX IF NOT EXISTS idx_aq_signal_id        ON public.approval_queue (signal_id);
CREATE INDEX IF NOT EXISTS idx_aq_approval_status  ON public.approval_queue (approval_status);
CREATE INDEX IF NOT EXISTS idx_aq_decision         ON public.approval_queue (decision);
CREATE INDEX IF NOT EXISTS idx_aq_symbol           ON public.approval_queue (symbol);
CREATE INDEX IF NOT EXISTS idx_aq_asset_type       ON public.approval_queue (asset_type);
CREATE INDEX IF NOT EXISTS idx_aq_created_at       ON public.approval_queue (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_aq_trace_id         ON public.approval_queue (trace_id);

COMMENT ON TABLE  public.approval_queue IS 'Human approval queue. Signals with risk decision approved or manual_review land here. Human reviews in Webull/OANDA and executes manually. No auto execution.';
COMMENT ON COLUMN public.approval_queue.decision         IS 'Risk engine decision: approved | manual_review';
COMMENT ON COLUMN public.approval_queue.approval_status  IS 'Human response: pending | approved | rejected';
COMMENT ON COLUMN public.approval_queue.risk_score       IS '0–100 penalty score from risk engine.';
COMMENT ON COLUMN public.approval_queue.approved_by      IS 'Optional identifier of human reviewer.';

-- =============================================================================
-- Verify:
-- SELECT symbol, side, asset_type, decision, approval_status, risk_score, created_at
-- FROM approval_queue ORDER BY created_at DESC LIMIT 10;
--
-- Count pending approvals:
-- SELECT COUNT(*) FROM approval_queue WHERE approval_status = 'pending';
-- =============================================================================
