-- coverage_gaps.sql
-- Tracks identified research coverage gaps from Phase 6 Research Desk.
CREATE TABLE IF NOT EXISTS public.coverage_gaps (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  gap_type    text NOT NULL,
  asset_type  text DEFAULT 'all',
  description text,
  severity    text DEFAULT 'medium'
                CHECK (severity IN ('low','medium','high')),
  notes       text,
  created_at  timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_coverage_gaps_gap_type ON public.coverage_gaps (gap_type);
CREATE INDEX IF NOT EXISTS idx_coverage_gaps_severity ON public.coverage_gaps (severity);
CREATE INDEX IF NOT EXISTS idx_coverage_gaps_created_at ON public.coverage_gaps (created_at DESC);

COMMENT ON TABLE public.coverage_gaps IS 'Research coverage gaps detected by Phase 6 — areas lacking sufficient research, strategy coverage, or calibration data.';
