-- paper_trade_runs.sql
-- Tracks paper/replay trade run sessions initiated by the replay lab.
-- Safe to run multiple times (CREATE IF NOT EXISTS).

CREATE TABLE IF NOT EXISTS public.paper_trade_runs (
  id            uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  proposal_id   uuid,
  signal_id     uuid,
  asset_type    text        NOT NULL DEFAULT 'forex',
  symbol        text,
  strategy_id   text,
  strategy_type text,
  replay_mode   text,       -- e.g. 'historical_bars', 'tick_replay', 'simple_tp_sl'
  status        text        NOT NULL DEFAULT 'running'
                            CHECK (status IN ('running', 'finished', 'error')),
  started_at    timestamptz NOT NULL DEFAULT now(),
  finished_at   timestamptz,
  trace_id      text
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_paper_trade_runs_proposal_id
  ON public.paper_trade_runs (proposal_id);

CREATE INDEX IF NOT EXISTS idx_paper_trade_runs_signal_id
  ON public.paper_trade_runs (signal_id);

CREATE INDEX IF NOT EXISTS idx_paper_trade_runs_strategy_id
  ON public.paper_trade_runs (strategy_id);

CREATE INDEX IF NOT EXISTS idx_paper_trade_runs_strategy_type
  ON public.paper_trade_runs (strategy_type);

CREATE INDEX IF NOT EXISTS idx_paper_trade_runs_asset_type
  ON public.paper_trade_runs (asset_type);

CREATE INDEX IF NOT EXISTS idx_paper_trade_runs_status
  ON public.paper_trade_runs (status);

CREATE INDEX IF NOT EXISTS idx_paper_trade_runs_started_at
  ON public.paper_trade_runs (started_at DESC);

-- Comments
COMMENT ON TABLE public.paper_trade_runs IS
  'Run sessions for paper/replay trading simulations. Each row represents one simulation run for one proposal. Results are stored in replay_results.';

COMMENT ON COLUMN public.paper_trade_runs.proposal_id IS
  'Foreign key to reviewed_signal_proposals.id — the proposal being simulated';

COMMENT ON COLUMN public.paper_trade_runs.signal_id IS
  'Foreign key to the originating signal';

COMMENT ON COLUMN public.paper_trade_runs.asset_type IS
  'Asset class being simulated: forex or options';

COMMENT ON COLUMN public.paper_trade_runs.replay_mode IS
  'Simulation method used: historical_bars (bar-by-bar), tick_replay, or simple_tp_sl (immediate TP/SL check)';

COMMENT ON COLUMN public.paper_trade_runs.status IS
  'Run status: running (in progress), finished (completed successfully), error (failed)';

COMMENT ON COLUMN public.paper_trade_runs.started_at IS
  'Timestamp when the simulation run was initiated';

COMMENT ON COLUMN public.paper_trade_runs.finished_at IS
  'Timestamp when the simulation run completed (null if still running or errored before completion)';

COMMENT ON COLUMN public.paper_trade_runs.trace_id IS
  'Correlation ID for tracing this run through the pipeline';

-- Verify:
-- SELECT id, proposal_id, asset_type, symbol, strategy_id, replay_mode, status, started_at, finished_at
-- FROM public.paper_trade_runs
-- ORDER BY started_at DESC
-- LIMIT 20;
