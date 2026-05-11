-- options_strategy_performance.sql
-- Aggregate win/loss metrics per options strategy type (covered_call, iron_condor, etc.)
-- Safe to run multiple times (CREATE IF NOT EXISTS).

CREATE TABLE IF NOT EXISTS public.options_strategy_performance (
  id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  strategy_type   text        NOT NULL,
  trades_count    integer     NOT NULL DEFAULT 0,
  wins            integer     NOT NULL DEFAULT 0,
  losses          integer     NOT NULL DEFAULT 0,
  avg_pnl_pct     numeric,    -- average P&L as percentage of position
  score           numeric,    -- composite performance score 0-100
  ranking_label   text,       -- e.g. 'top_performer', 'average', 'underperformer'
  updated_at      timestamptz NOT NULL DEFAULT now()
);

-- Unique constraint: one record per options strategy type
CREATE UNIQUE INDEX IF NOT EXISTS idx_options_strategy_performance_unique
  ON public.options_strategy_performance (strategy_type);

-- Additional indexes
CREATE INDEX IF NOT EXISTS idx_options_strategy_performance_score
  ON public.options_strategy_performance (score DESC);

CREATE INDEX IF NOT EXISTS idx_options_strategy_performance_updated_at
  ON public.options_strategy_performance (updated_at DESC);

-- Comments
COMMENT ON TABLE public.options_strategy_performance IS
  'Aggregate performance metrics per options strategy type. Strategy types include: covered_call, cash_secured_put, iron_condor, credit_spread, zebra_strategy, wheel_strategy.';

COMMENT ON COLUMN public.options_strategy_performance.strategy_type IS
  'Options strategy type: covered_call, cash_secured_put, iron_condor, credit_spread, zebra_strategy, wheel_strategy';

COMMENT ON COLUMN public.options_strategy_performance.trades_count IS
  'Total number of completed options trades for this strategy type';

COMMENT ON COLUMN public.options_strategy_performance.wins IS
  'Number of trades that hit take-profit target or were closed profitably';

COMMENT ON COLUMN public.options_strategy_performance.losses IS
  'Number of trades that hit stop-loss or were closed at a net loss';

COMMENT ON COLUMN public.options_strategy_performance.avg_pnl_pct IS
  'Average P&L as a percentage of position size (positive = profitable on average)';

COMMENT ON COLUMN public.options_strategy_performance.score IS
  'Composite performance score 0-100 combining win rate, avg P&L, and sample size';

COMMENT ON COLUMN public.options_strategy_performance.ranking_label IS
  'Human-readable tier label: top_performer, average, underperformer, insufficient_data';

COMMENT ON COLUMN public.options_strategy_performance.updated_at IS
  'Timestamp of last upsert — records are updated in place, not appended';

-- Verify:
-- SELECT strategy_type, trades_count, wins, losses,
--        ROUND(wins::numeric / NULLIF(trades_count, 0) * 100, 1) AS win_rate_pct,
--        avg_pnl_pct, score, ranking_label, updated_at
-- FROM public.options_strategy_performance
-- ORDER BY score DESC NULLS LAST;
