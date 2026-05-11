-- agent_scorecards.sql
-- Per-agent performance metric storage for AI workforce evaluation.
-- Safe to run multiple times (CREATE IF NOT EXISTS).

CREATE TABLE IF NOT EXISTS public.agent_scorecards (
  id            uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  agent_name    text        NOT NULL,
  metric_type   text        NOT NULL,
  metric_value  numeric,
  notes         text,
  updated_at    timestamptz NOT NULL DEFAULT now()
);

-- Unique constraint: one metric record per (agent, metric_type) pair
CREATE UNIQUE INDEX IF NOT EXISTS idx_agent_scorecards_unique
  ON public.agent_scorecards (agent_name, metric_type);

-- Additional indexes
CREATE INDEX IF NOT EXISTS idx_agent_scorecards_agent_name
  ON public.agent_scorecards (agent_name);

CREATE INDEX IF NOT EXISTS idx_agent_scorecards_metric_type
  ON public.agent_scorecards (metric_type);

CREATE INDEX IF NOT EXISTS idx_agent_scorecards_metric_value
  ON public.agent_scorecards (metric_value DESC);

CREATE INDEX IF NOT EXISTS idx_agent_scorecards_updated_at
  ON public.agent_scorecards (updated_at DESC);

-- Comments
COMMENT ON TABLE public.agent_scorecards IS
  'Performance scorecard metrics per AI agent. Each row is one metric for one agent. Upserted by the performance tracker.';

COMMENT ON COLUMN public.agent_scorecards.agent_name IS
  'Name of the AI agent being scored (e.g. signal_reviewer, risk_manager, strategy_agent)';

COMMENT ON COLUMN public.agent_scorecards.metric_type IS
  'Type of metric being stored. Examples: approval_accuracy, confidence_calibration_score, avg_review_latency_ms, win_rate_of_approved_signals, false_positive_rate';

COMMENT ON COLUMN public.agent_scorecards.metric_value IS
  'Numeric value of the metric. Units depend on metric_type (e.g. 0-1 for rates, ms for latency)';

COMMENT ON COLUMN public.agent_scorecards.notes IS
  'Human-readable context for this metric value (e.g. sample count, date range, methodology)';

COMMENT ON COLUMN public.agent_scorecards.updated_at IS
  'Timestamp of last update — records are upserted on (agent_name, metric_type)';

-- Verify:
-- SELECT agent_name, metric_type, metric_value, notes, updated_at
-- FROM public.agent_scorecards
-- ORDER BY agent_name, metric_type;
