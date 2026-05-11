-- ─────────────────────────────────────────────────────────────────────────────
-- Phase 3 Patch 2: Add all missing scoring columns across all 4 tables
-- Safe: ADD COLUMN IF NOT EXISTS + ALTER COLUMN — idempotent, safe to re-run.
-- Run via: Supabase Dashboard → SQL Editor → Run
-- ─────────────────────────────────────────────────────────────────────────────

-- ─── signal_candidates ────────────────────────────────────────────────────────
-- tenant_id has NOT NULL — relax it (Mac Mini worker has no tenant context)
ALTER TABLE public.signal_candidates
    ALTER COLUMN tenant_id DROP NOT NULL;

-- ─── signal_scores ────────────────────────────────────────────────────────────
ALTER TABLE public.signal_scores
    ALTER COLUMN tenant_id DROP NOT NULL;

ALTER TABLE public.signal_scores
    ADD COLUMN IF NOT EXISTS signal_candidate_id  UUID;

ALTER TABLE public.signal_scores
    ADD COLUMN IF NOT EXISTS score_setup_quality  NUMERIC(5,2) NOT NULL DEFAULT 0;

ALTER TABLE public.signal_scores
    ADD COLUMN IF NOT EXISTS score_risk_quality   NUMERIC(5,2) NOT NULL DEFAULT 0;

ALTER TABLE public.signal_scores
    ADD COLUMN IF NOT EXISTS score_confirmation   NUMERIC(5,2) NOT NULL DEFAULT 0;

ALTER TABLE public.signal_scores
    ADD COLUMN IF NOT EXISTS score_clarity        NUMERIC(5,2) NOT NULL DEFAULT 0;

ALTER TABLE public.signal_scores
    ADD COLUMN IF NOT EXISTS notes                TEXT;

CREATE INDEX IF NOT EXISTS idx_signal_scores_candidate
    ON public.signal_scores (signal_candidate_id);

-- ─── signal_reviews ───────────────────────────────────────────────────────────
ALTER TABLE public.signal_reviews
    ALTER COLUMN tenant_id DROP NOT NULL;

ALTER TABLE public.signal_reviews
    ADD COLUMN IF NOT EXISTS signal_candidate_id  UUID;

ALTER TABLE public.signal_reviews
    ADD COLUMN IF NOT EXISTS review_action        TEXT
        CHECK (review_action IN ('approve','reject','hold','expire'));

ALTER TABLE public.signal_reviews
    ADD COLUMN IF NOT EXISTS reviewer_type        TEXT DEFAULT 'system'
        CHECK (reviewer_type IN ('system','ai','human'));

ALTER TABLE public.signal_reviews
    ADD COLUMN IF NOT EXISTS score_total          NUMERIC(5,2);

ALTER TABLE public.signal_reviews
    ADD COLUMN IF NOT EXISTS confidence_label     TEXT;

ALTER TABLE public.signal_reviews
    ADD COLUMN IF NOT EXISTS risk_label           TEXT;

ALTER TABLE public.signal_reviews
    ADD COLUMN IF NOT EXISTS notes                TEXT;

CREATE INDEX IF NOT EXISTS idx_signal_reviews_candidate
    ON public.signal_reviews (signal_candidate_id);

-- ─── approved_signals ─────────────────────────────────────────────────────────
ALTER TABLE public.approved_signals
    ALTER COLUMN tenant_id DROP NOT NULL;

ALTER TABLE public.approved_signals
    ADD COLUMN IF NOT EXISTS source_signal_id     UUID;

ALTER TABLE public.approved_signals
    ADD COLUMN IF NOT EXISTS published            BOOLEAN NOT NULL DEFAULT false;

-- ─────────────────────────────────────────────────────────────────────────────
-- Verify (run after applying):
-- SELECT column_name FROM information_schema.columns
--   WHERE table_name IN ('signal_candidates','signal_scores','signal_reviews','approved_signals')
--   ORDER BY table_name, ordinal_position;
-- ─────────────────────────────────────────────────────────────────────────────
