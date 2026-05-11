-- proposal_outcomes.sql
-- Stores final outcome records for reviewed signal proposals.
-- Safe to run multiple times (CREATE IF NOT EXISTS).

CREATE TABLE IF NOT EXISTS public.proposal_outcomes (
  id            uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  proposal_id   uuid,
  signal_id     uuid,
  asset_type    text        NOT NULL DEFAULT 'forex'
                            CHECK (asset_type IN ('forex', 'options')),
  symbol        text,
  strategy_id   text,
  strategy_type text,
  outcome_status text       NOT NULL
                            CHECK (outcome_status IN ('win', 'loss', 'breakeven', 'expired')),
  outcome_label text,
  pnl_r         numeric,
  pnl_pct       numeric,
  mfe           numeric,    -- Maximum Favorable Excursion
  mae           numeric,    -- Maximum Adverse Excursion
  notes         text,
  trace_id      text,
  created_at    timestamptz NOT NULL DEFAULT now()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_proposal_outcomes_proposal_id
  ON public.proposal_outcomes (proposal_id);

CREATE INDEX IF NOT EXISTS idx_proposal_outcomes_signal_id
  ON public.proposal_outcomes (signal_id);

CREATE INDEX IF NOT EXISTS idx_proposal_outcomes_strategy_id
  ON public.proposal_outcomes (strategy_id);

CREATE INDEX IF NOT EXISTS idx_proposal_outcomes_strategy_type
  ON public.proposal_outcomes (strategy_type);

CREATE INDEX IF NOT EXISTS idx_proposal_outcomes_asset_type
  ON public.proposal_outcomes (asset_type);

CREATE INDEX IF NOT EXISTS idx_proposal_outcomes_outcome_status
  ON public.proposal_outcomes (outcome_status);

CREATE INDEX IF NOT EXISTS idx_proposal_outcomes_created_at
  ON public.proposal_outcomes (created_at DESC);

-- Comments
COMMENT ON TABLE public.proposal_outcomes IS
  'Final outcome records for reviewed signal proposals — win/loss/breakeven/expired with P&L metrics.';

COMMENT ON COLUMN public.proposal_outcomes.proposal_id IS
  'Foreign key to reviewed_signal_proposals.id';

COMMENT ON COLUMN public.proposal_outcomes.signal_id IS
  'Foreign key to the originating signal record';

COMMENT ON COLUMN public.proposal_outcomes.asset_type IS
  'Asset class: forex or options';

COMMENT ON COLUMN public.proposal_outcomes.outcome_status IS
  'Final outcome: win, loss, breakeven, or expired (reached DTE without resolution)';

COMMENT ON COLUMN public.proposal_outcomes.pnl_r IS
  'Profit/loss expressed in R multiples (e.g. 2.0 = 2x risk, -1.0 = full loss)';

COMMENT ON COLUMN public.proposal_outcomes.pnl_pct IS
  'Profit/loss as percentage of position size';

COMMENT ON COLUMN public.proposal_outcomes.mfe IS
  'Maximum Favorable Excursion — best unrealized gain during the trade';

COMMENT ON COLUMN public.proposal_outcomes.mae IS
  'Maximum Adverse Excursion — worst unrealized drawdown during the trade';

COMMENT ON COLUMN public.proposal_outcomes.trace_id IS
  'Correlation ID for tracing through the pipeline';

-- Verify:
-- SELECT id, proposal_id, asset_type, symbol, strategy_id, outcome_status, pnl_r, pnl_pct, created_at
-- FROM public.proposal_outcomes
-- ORDER BY created_at DESC
-- LIMIT 20;
