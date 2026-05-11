-- trading_lab_strategy_bridge.sql
-- Generated from existing docs SQL files for remote apply.

-- BEGIN reviewed_signal_proposals.sql
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
    strategy_type        TEXT,                         -- normalized strategy family for replay/profile mapping
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

ALTER TABLE public.reviewed_signal_proposals
    ADD COLUMN IF NOT EXISTS asset_type TEXT NOT NULL DEFAULT 'forex';
ALTER TABLE public.reviewed_signal_proposals
    ADD COLUMN IF NOT EXISTS strategy_type TEXT;

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
CREATE INDEX IF NOT EXISTS idx_rsp_strategy_type ON public.reviewed_signal_proposals (strategy_type);
CREATE INDEX IF NOT EXISTS idx_rsp_asset_type  ON public.reviewed_signal_proposals (asset_type);
CREATE INDEX IF NOT EXISTS idx_rsp_created_at  ON public.reviewed_signal_proposals (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_rsp_trace_id    ON public.reviewed_signal_proposals (trace_id);

COMMENT ON TABLE  public.reviewed_signal_proposals IS 'AI analyst proposals. Covers forex (entry/SL/TP) and options (expiry/strike/premium). No execution — analysis only.';
COMMENT ON COLUMN public.reviewed_signal_proposals.asset_type    IS 'forex | options';
COMMENT ON COLUMN public.reviewed_signal_proposals.strategy_type IS 'Normalized strategy family used by replay/profile logic, e.g. covered_call, cash_secured_put, credit_spread.';
COMMENT ON COLUMN public.reviewed_signal_proposals.status        IS 'proposed | blocked | needs_review';
COMMENT ON COLUMN public.reviewed_signal_proposals.ai_confidence IS '0.0–1.0 AI confidence score.';
-- END reviewed_signal_proposals.sql

-- BEGIN risk_decisions.sql
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

ALTER TABLE public.risk_decisions ADD COLUMN IF NOT EXISTS asset_type TEXT NOT NULL DEFAULT 'forex';
ALTER TABLE public.risk_decisions ADD COLUMN IF NOT EXISTS decision   TEXT;
ALTER TABLE public.risk_decisions ADD COLUMN IF NOT EXISTS risk_flags JSONB NOT NULL DEFAULT '[]'::jsonb;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'risk_decisions'
          AND column_name = 'status'
    ) THEN
        EXECUTE '
            UPDATE public.risk_decisions
               SET decision = COALESCE(decision, status)
             WHERE decision IS NULL
        ';
    END IF;
END
$$;

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
-- END risk_decisions.sql

-- BEGIN paper_trade_runs.sql
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
-- END paper_trade_runs.sql

-- BEGIN replay_results.sql
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

CREATE INDEX IF NOT EXISTS idx_replay_results_strategy_outcome
  ON public.replay_results (strategy_id, replay_outcome);

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
-- END replay_results.sql

-- BEGIN strategy_variants.sql
-- strategy_variants.sql
-- Stores alternative parameter configurations for strategies, with backtest/replay scores.
-- Enables A/B comparison of parameter sets before committing to changes.
-- Safe to run multiple times (CREATE IF NOT EXISTS).

CREATE TABLE IF NOT EXISTS public.strategy_variants (
  id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  strategy_id     text,       -- Parent strategy this variant belongs to
  variant_name    text,       -- Descriptive name, e.g. 'conservative_rr_2.0', 'aggressive_rr_3.5'
  parameter_set   jsonb       NOT NULL DEFAULT '{}'::jsonb,
  backtest_score  numeric,    -- Performance score from historical backtest (0-100)
  replay_score    numeric,    -- Performance score from replay simulation (0-100)
  created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_strategy_variants_strategy_id
  ON public.strategy_variants (strategy_id);

CREATE INDEX IF NOT EXISTS idx_strategy_variants_variant_name
  ON public.strategy_variants (variant_name);

CREATE INDEX IF NOT EXISTS idx_strategy_variants_replay_score
  ON public.strategy_variants (replay_score DESC NULLS LAST);

CREATE INDEX IF NOT EXISTS idx_strategy_variants_backtest_score
  ON public.strategy_variants (backtest_score DESC NULLS LAST);

CREATE INDEX IF NOT EXISTS idx_strategy_variants_created_at
  ON public.strategy_variants (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_strategy_variants_parameter_set
  ON public.strategy_variants USING gin (parameter_set);

COMMENT ON TABLE public.strategy_variants IS
  'Alternative parameter configurations for strategies. Used to compare variant performance before deciding to update live strategy parameters. All variants are for research/comparison only.';

COMMENT ON COLUMN public.strategy_variants.strategy_id IS
  'Parent strategy this variant is derived from. Matches strategy_id in reviewed_signal_proposals and strategy_performance.';

COMMENT ON COLUMN public.strategy_variants.variant_name IS
  'Descriptive name for this parameter configuration. Examples: conservative_rr_2.0, aggressive_rr_3.5, tight_sl_0.5pct, wide_tp_3.0pct';

COMMENT ON COLUMN public.strategy_variants.parameter_set IS
  'JSONB object containing the full parameter configuration for this variant. Example: {"rr_ratio": 2.0, "sl_pct": 0.005, "tp_pct": 0.010, "min_confidence": 0.70}';

COMMENT ON COLUMN public.strategy_variants.backtest_score IS
  'Composite score 0-100 from historical backtesting with this parameter set. Higher = better historical performance.';

COMMENT ON COLUMN public.strategy_variants.replay_score IS
  'Composite score 0-100 from replay simulation with this parameter set. Higher = better simulated performance. Primary ranking metric.';
-- END strategy_variants.sql
