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

-- Indexes
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

-- GIN index for JSONB parameter_set queries
CREATE INDEX IF NOT EXISTS idx_strategy_variants_parameter_set
  ON public.strategy_variants USING gin (parameter_set);

-- Comments
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

-- Verify:
-- SELECT strategy_id, variant_name,
--        parameter_set,
--        backtest_score, replay_score,
--        created_at
-- FROM public.strategy_variants
-- ORDER BY replay_score DESC NULLS LAST;
