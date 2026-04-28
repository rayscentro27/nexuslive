-- research_recommendations.sql
-- Unified recommendation packets for research-derived business and trading ideas.
-- Safe to run multiple times (CREATE IF NOT EXISTS + ADD COLUMN IF NOT EXISTS).

CREATE TABLE IF NOT EXISTS public.research_recommendations (
  id                 uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  source_table       text        NOT NULL,
  source_id          uuid,
  domain             text        NOT NULL CHECK (domain IN ('business', 'trading')),
  category           text,
  title              text        NOT NULL,
  score              numeric,
  confidence         numeric,
  recommendation     text        NOT NULL DEFAULT 'review'
                               CHECK (recommendation IN ('approve', 'review', 'reject')),
  summary            text,
  thesis             text,
  execution_plan     jsonb       NOT NULL DEFAULT '[]'::jsonb,
  profitability_path text,
  backend_handoff    jsonb       NOT NULL DEFAULT '[]'::jsonb,
  approval_status    text        NOT NULL DEFAULT 'pending'
                               CHECK (approval_status IN ('pending', 'approved', 'rejected', 'executing', 'completed')),
  metadata           jsonb       NOT NULL DEFAULT '{}'::jsonb,
  trace_id           text,
  created_at         timestamptz NOT NULL DEFAULT now(),
  updated_at         timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE public.research_recommendations ADD COLUMN IF NOT EXISTS source_table       text;
ALTER TABLE public.research_recommendations ADD COLUMN IF NOT EXISTS source_id          uuid;
ALTER TABLE public.research_recommendations ADD COLUMN IF NOT EXISTS domain             text;
ALTER TABLE public.research_recommendations ADD COLUMN IF NOT EXISTS category           text;
ALTER TABLE public.research_recommendations ADD COLUMN IF NOT EXISTS title              text;
ALTER TABLE public.research_recommendations ADD COLUMN IF NOT EXISTS score              numeric;
ALTER TABLE public.research_recommendations ADD COLUMN IF NOT EXISTS confidence         numeric;
ALTER TABLE public.research_recommendations ADD COLUMN IF NOT EXISTS recommendation     text;
ALTER TABLE public.research_recommendations ADD COLUMN IF NOT EXISTS summary            text;
ALTER TABLE public.research_recommendations ADD COLUMN IF NOT EXISTS thesis             text;
ALTER TABLE public.research_recommendations ADD COLUMN IF NOT EXISTS execution_plan     jsonb NOT NULL DEFAULT '[]'::jsonb;
ALTER TABLE public.research_recommendations ADD COLUMN IF NOT EXISTS profitability_path text;
ALTER TABLE public.research_recommendations ADD COLUMN IF NOT EXISTS backend_handoff    jsonb NOT NULL DEFAULT '[]'::jsonb;
ALTER TABLE public.research_recommendations ADD COLUMN IF NOT EXISTS approval_status    text;
ALTER TABLE public.research_recommendations ADD COLUMN IF NOT EXISTS metadata           jsonb NOT NULL DEFAULT '{}'::jsonb;
ALTER TABLE public.research_recommendations ADD COLUMN IF NOT EXISTS trace_id           text;
ALTER TABLE public.research_recommendations ADD COLUMN IF NOT EXISTS created_at         timestamptz NOT NULL DEFAULT now();
ALTER TABLE public.research_recommendations ADD COLUMN IF NOT EXISTS updated_at         timestamptz NOT NULL DEFAULT now();

CREATE INDEX IF NOT EXISTS idx_research_recommendations_domain
  ON public.research_recommendations (domain);

CREATE INDEX IF NOT EXISTS idx_research_recommendations_source
  ON public.research_recommendations (source_table, source_id);

CREATE INDEX IF NOT EXISTS idx_research_recommendations_recommendation
  ON public.research_recommendations (recommendation);

CREATE INDEX IF NOT EXISTS idx_research_recommendations_approval_status
  ON public.research_recommendations (approval_status);

CREATE INDEX IF NOT EXISTS idx_research_recommendations_created_at
  ON public.research_recommendations (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_research_recommendations_metadata
  ON public.research_recommendations USING GIN (metadata);

CREATE INDEX IF NOT EXISTS idx_research_recommendations_execution_plan
  ON public.research_recommendations USING GIN (execution_plan);

CREATE INDEX IF NOT EXISTS idx_research_recommendations_backend_handoff
  ON public.research_recommendations USING GIN (backend_handoff);

COMMENT ON TABLE public.research_recommendations IS
  'Unified Hermes-ready recommendation packets generated from research-derived business and trading candidates. Approved records can be consumed by backend execution workers.';

COMMENT ON COLUMN public.research_recommendations.domain IS
  'High-level domain for the recommendation packet: business or trading.';

COMMENT ON COLUMN public.research_recommendations.execution_plan IS
  'Ordered plan steps generated from the research context. For business ideas this should include launch steps; for trading ideas, risk and validation steps.';

COMMENT ON COLUMN public.research_recommendations.backend_handoff IS
  'Structured task list for downstream implementation workers once the operator approves the recommendation.';

COMMENT ON COLUMN public.research_recommendations.approval_status IS
  'Operator decision lifecycle: pending, approved, rejected, executing, completed.';
