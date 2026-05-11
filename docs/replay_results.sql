-- replay_results.sql
-- Stores outcome data for each completed paper/replay trade simulation.
-- Safe to run multiple times (CREATE IF NOT EXISTS).

CREATE TABLE IF NOT EXISTS public.replay_results (
  id                   uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id               uuid,       -- FK to paper_trade_runs.id
  proposal_id          uuid,       -- FK to reviewed_signal_proposals.id
  signal_id            uuid,
  asset_type           text        NOT NULL DEFAULT 'forex',
  symbol               text,
  strategy_id          text,
  strategy_type        text,
  replay_outcome       text        NOT NULL
                                   CHECK (replay_outcome IN (
                                     'tp_hit', 'sl_hit', 'breakeven', 'expired',
                                     'win', 'loss'
                                   )),
  pnl_r                numeric,    -- P&L in R multiples
  pnl_pct              numeric,    -- P&L as percentage
  mfe                  numeric,    -- Maximum Favorable Excursion
  mae                  numeric,    -- Maximum Adverse Excursion
  bars_to_resolution   integer,    -- How many bars until TP/SL hit or expiry
  hit_take_profit      boolean,
  hit_stop_loss        boolean,
  expired              boolean,    -- True if position expired without TP/SL hit
  trace_id             text,
  created_at           timestamptz NOT NULL DEFAULT now()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_replay_results_run_id
  ON public.replay_results (run_id);

CREATE INDEX IF NOT EXISTS idx_replay_results_proposal_id
  ON public.replay_results (proposal_id);

CREATE INDEX IF NOT EXISTS idx_replay_results_signal_id
  ON public.replay_results (signal_id);

CREATE INDEX IF NOT EXISTS idx_replay_results_strategy_id
  ON public.replay_results (strategy_id);

CREATE INDEX IF NOT EXISTS idx_replay_results_strategy_type
  ON public.replay_results (strategy_type);

CREATE INDEX IF NOT EXISTS idx_replay_results_asset_type
  ON public.replay_results (asset_type);

CREATE INDEX IF NOT EXISTS idx_replay_results_replay_outcome
  ON public.replay_results (replay_outcome);

CREATE INDEX IF NOT EXISTS idx_replay_results_created_at
  ON public.replay_results (created_at DESC);

-- Composite index for win-rate queries per strategy
CREATE INDEX IF NOT EXISTS idx_replay_results_strategy_outcome
  ON public.replay_results (strategy_id, replay_outcome);

-- Comments
COMMENT ON TABLE public.replay_results IS
  'Outcome records for completed paper/replay trade simulations. One row per run. Cross-referenced by optimizers to compute win rates and calibration metrics.';

COMMENT ON COLUMN public.replay_results.run_id IS
  'Foreign key to paper_trade_runs.id — the simulation session that produced this result';

COMMENT ON COLUMN public.replay_results.proposal_id IS
  'Foreign key to reviewed_signal_proposals.id — enables cross-referencing confidence with outcomes';

COMMENT ON COLUMN public.replay_results.replay_outcome IS
  'Simulation outcome: tp_hit or win = favorable, sl_hit or loss = unfavorable, breakeven = no net gain/loss, expired = reached max holding period';

COMMENT ON COLUMN public.replay_results.pnl_r IS
  'P&L in R multiples. 1.0 = gained 1x initial risk. -1.0 = lost full risk amount.';

COMMENT ON COLUMN public.replay_results.pnl_pct IS
  'P&L as a percentage of position size';

COMMENT ON COLUMN public.replay_results.mfe IS
  'Maximum Favorable Excursion — furthest the trade moved in the profitable direction';

COMMENT ON COLUMN public.replay_results.mae IS
  'Maximum Adverse Excursion — furthest the trade moved against the position';

COMMENT ON COLUMN public.replay_results.bars_to_resolution IS
  'Number of price bars elapsed from entry until TP hit, SL hit, or expiry';

COMMENT ON COLUMN public.replay_results.hit_take_profit IS
  'True if take-profit target was reached during the simulation';

COMMENT ON COLUMN public.replay_results.hit_stop_loss IS
  'True if stop-loss level was breached during the simulation';

COMMENT ON COLUMN public.replay_results.expired IS
  'True if the simulation ran to the maximum holding period without hitting TP or SL';

-- Verify:
-- SELECT id, proposal_id, asset_type, symbol, strategy_id, replay_outcome,
--        pnl_r, pnl_pct, bars_to_resolution, created_at
-- FROM public.replay_results
-- ORDER BY created_at DESC
-- LIMIT 20;
