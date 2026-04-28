-- confidence_calibration.sql
-- Tracks AI confidence accuracy by agent and confidence band.
-- Populated by the performance tracker from replay_results cross-referenced with proposals.
-- Safe to run multiple times (CREATE IF NOT EXISTS).

CREATE TABLE IF NOT EXISTS public.confidence_calibration (
  id                 uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  agent_name         text        NOT NULL,
  confidence_band    text        NOT NULL,  -- e.g. '0.60-0.65', '0.80-0.85'
  samples            integer     NOT NULL DEFAULT 0,
  wins               integer     NOT NULL DEFAULT 0,
  losses             integer     NOT NULL DEFAULT 0,
  actual_win_rate    numeric,    -- wins / samples (observed outcome)
  expected_win_rate  numeric,    -- midpoint of confidence_band (what AI predicted)
  calibration_gap    numeric,    -- expected_win_rate - actual_win_rate
                                 --   positive = AI overconfident
                                 --   negative = AI underconfident
  updated_at         timestamptz NOT NULL DEFAULT now()
);

-- Unique constraint: one record per (agent, confidence_band)
CREATE UNIQUE INDEX IF NOT EXISTS idx_confidence_calibration_unique
  ON public.confidence_calibration (agent_name, confidence_band);

-- Additional indexes
CREATE INDEX IF NOT EXISTS idx_confidence_calibration_agent_name
  ON public.confidence_calibration (agent_name);

CREATE INDEX IF NOT EXISTS idx_confidence_calibration_confidence_band
  ON public.confidence_calibration (confidence_band);

CREATE INDEX IF NOT EXISTS idx_confidence_calibration_calibration_gap
  ON public.confidence_calibration (calibration_gap DESC);

CREATE INDEX IF NOT EXISTS idx_confidence_calibration_updated_at
  ON public.confidence_calibration (updated_at DESC);

-- Comments
COMMENT ON TABLE public.confidence_calibration IS
  'AI confidence calibration tracking per agent per confidence band. Measures whether stated confidence matches actual win rates. Used by confidence_optimizer.js to detect systematic over/under-confidence.';

COMMENT ON COLUMN public.confidence_calibration.agent_name IS
  'Name of the AI agent whose confidence is being calibrated (e.g. signal_reviewer, strategy_agent)';

COMMENT ON COLUMN public.confidence_calibration.confidence_band IS
  'Confidence range bucket, e.g. "0.60-0.65" meaning the agent assigned confidence between 60% and 65%';

COMMENT ON COLUMN public.confidence_calibration.samples IS
  'Total number of proposals in this confidence band with known replay outcomes';

COMMENT ON COLUMN public.confidence_calibration.wins IS
  'Number of proposals in this band that resulted in a win (tp_hit or win outcome)';

COMMENT ON COLUMN public.confidence_calibration.losses IS
  'Number of proposals in this band that resulted in a loss (sl_hit or loss outcome)';

COMMENT ON COLUMN public.confidence_calibration.actual_win_rate IS
  'Observed win rate for this band: wins / samples. Compare to expected_win_rate for calibration.';

COMMENT ON COLUMN public.confidence_calibration.expected_win_rate IS
  'The midpoint of confidence_band — what the AI expected the win rate to be';

COMMENT ON COLUMN public.confidence_calibration.calibration_gap IS
  'expected_win_rate minus actual_win_rate. Positive = AI overestimated (overconfident). Negative = AI underestimated (underconfident). Ideal = 0.';

COMMENT ON COLUMN public.confidence_calibration.updated_at IS
  'Timestamp of last upsert — records are updated in place on (agent_name, confidence_band)';

-- Verify:
-- SELECT agent_name, confidence_band, samples, wins, losses,
--        ROUND(actual_win_rate * 100, 1)   AS actual_win_pct,
--        ROUND(expected_win_rate * 100, 1) AS expected_win_pct,
--        ROUND(calibration_gap * 100, 1)   AS gap_pct,
--        updated_at
-- FROM public.confidence_calibration
-- ORDER BY ABS(calibration_gap) DESC NULLS LAST;
