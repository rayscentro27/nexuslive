-- ── Ranked strategies: research pipeline output ──────────────────────────────
CREATE TABLE IF NOT EXISTS public.ranked_strategies (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  source_file     text NOT NULL,
  source_channel  text,
  strategy_text   text NOT NULL,
  rank_score      numeric(4,1) DEFAULT 0,   -- 0-10
  rank_reasons    jsonb DEFAULT '{}',
  instruments     text[],                   -- ['EURUSD', 'GBPUSD']
  timeframes      text[],                   -- ['H1', 'H4']
  has_entry       boolean DEFAULT false,
  has_stoploss    boolean DEFAULT false,
  has_tp          boolean DEFAULT false,
  paper_tested    boolean DEFAULT false,
  paper_result    jsonb DEFAULT '{}',
  event_emitted   boolean DEFAULT false,
  created_at      timestamptz DEFAULT now(),
  updated_at      timestamptz DEFAULT now()
);

ALTER TABLE public.ranked_strategies ENABLE ROW LEVEL SECURITY;

CREATE POLICY "service_full_access" ON public.ranked_strategies
  USING (true) WITH CHECK (true);

-- index for polling high-ranked untested strategies
CREATE INDEX IF NOT EXISTS ranked_strategies_score_idx
  ON public.ranked_strategies (rank_score DESC, paper_tested, event_emitted);
