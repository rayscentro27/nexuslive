-- strategy_performance.sql
-- Aggregate win/loss/expectancy metrics per strategy_id.
-- Safe to run multiple times (CREATE IF NOT EXISTS).

CREATE TABLE IF NOT EXISTS public.strategy_performance (
  id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  strategy_id     text        NOT NULL,
  asset_type      text        NOT NULL DEFAULT 'forex',
  trades_count    integer     NOT NULL DEFAULT 0,
  wins            integer     NOT NULL DEFAULT 0,
  losses          integer     NOT NULL DEFAULT 0,
  breakevens      integer     NOT NULL DEFAULT 0,
  win_rate        numeric,    -- wins / trades_count
  avg_pnl_r       numeric,    -- average P&L in R multiples
  avg_pnl_pct     numeric,    -- average P&L as percentage
  expectancy      numeric,    -- (win_rate * avg_win_r) - ((1 - win_rate) * avg_loss_r)
  score           numeric,    -- composite performance score 0-100
  ranking_label   text,       -- e.g. 'top_performer', 'average', 'underperformer'
  updated_at      timestamptz NOT NULL DEFAULT now()
);

-- Unique constraint: one performance record per strategy per asset type
CREATE UNIQUE INDEX IF NOT EXISTS idx_strategy_performance_unique
  ON public.strategy_performance (strategy_id, asset_type);

-- Additional indexes
CREATE INDEX IF NOT EXISTS idx_strategy_performance_strategy_id
  ON public.strategy_performance (strategy_id);

CREATE INDEX IF NOT EXISTS idx_strategy_performance_asset_type
  ON public.strategy_performance (asset_type);

CREATE INDEX IF NOT EXISTS idx_strategy_performance_score
  ON public.strategy_performance (score DESC);

CREATE INDEX IF NOT EXISTS idx_strategy_performance_win_rate
  ON public.strategy_performance (win_rate DESC);

CREATE INDEX IF NOT EXISTS idx_strategy_performance_updated_at
  ON public.strategy_performance (updated_at DESC);

-- Comments
COMMENT ON TABLE public.strategy_performance IS
  'Aggregate performance metrics per strategy_id — win rate, expectancy, and composite score. Upserted by the performance tracker.';

COMMENT ON COLUMN public.strategy_performance.strategy_id IS
  'Strategy identifier matching reviewed_signal_proposals.strategy_id';

COMMENT ON COLUMN public.strategy_performance.asset_type IS
  'Asset class this performance record applies to (forex, options)';

COMMENT ON COLUMN public.strategy_performance.trades_count IS
  'Total number of completed trades included in this record';

COMMENT ON COLUMN public.strategy_performance.win_rate IS
  'Win rate: wins / trades_count (0.0 to 1.0)';

COMMENT ON COLUMN public.strategy_performance.expectancy IS
  'Statistical expectancy per trade in R multiples — positive = edge exists';

COMMENT ON COLUMN public.strategy_performance.score IS
  'Composite performance score 0-100 combining win rate, expectancy, and sample size';

COMMENT ON COLUMN public.strategy_performance.ranking_label IS
  'Human-readable tier label: top_performer, average, underperformer, insufficient_data';

COMMENT ON COLUMN public.strategy_performance.updated_at IS
  'Timestamp of last update — performance records are upserted, not appended';

-- Verify:
-- SELECT strategy_id, asset_type, trades_count, wins, losses, win_rate, expectancy, score, ranking_label, updated_at
-- FROM public.strategy_performance
-- ORDER BY score DESC NULLS LAST
-- LIMIT 20;
