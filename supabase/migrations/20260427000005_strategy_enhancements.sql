-- ── Strategy enhancement columns ─────────────────────────────────────────────
ALTER TABLE public.ranked_strategies
  ADD COLUMN IF NOT EXISTS enhancement    jsonb         DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS enhanced_score numeric(4,1)  DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS enhanced_at    timestamptz   DEFAULT NULL;

-- index for polling unenhanced mid-range strategies
CREATE INDEX IF NOT EXISTS ranked_strategies_enhance_idx
  ON public.ranked_strategies (rank_score DESC, enhanced_at NULLS FIRST)
  WHERE rank_score >= 4.0;
