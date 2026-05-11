-- ─────────────────────────────────────────────────────────────────────────────
-- Phase 3 Patch: signal_candidates missing columns
-- Purpose : signal_candidates already existed with basic columns. This patch
--           adds all columns that the scoring pipeline expects.
-- Safe    : All ADD COLUMN IF NOT EXISTS — idempotent, safe to re-run.
-- Run via : Supabase Dashboard → SQL Editor → Run
-- ─────────────────────────────────────────────────────────────────────────────

ALTER TABLE public.signal_candidates
    ADD COLUMN IF NOT EXISTS source           TEXT        NOT NULL DEFAULT 'tradingview';

ALTER TABLE public.signal_candidates
    ADD COLUMN IF NOT EXISTS source_signal_id UUID;

ALTER TABLE public.signal_candidates
    ADD COLUMN IF NOT EXISTS entry_zone       JSONB;

ALTER TABLE public.signal_candidates
    ADD COLUMN IF NOT EXISTS stop_zone        JSONB;

ALTER TABLE public.signal_candidates
    ADD COLUMN IF NOT EXISTS target_zone      JSONB;

ALTER TABLE public.signal_candidates
    ADD COLUMN IF NOT EXISTS raw_payload      JSONB;

ALTER TABLE public.signal_candidates
    ADD COLUMN IF NOT EXISTS review_status    TEXT NOT NULL DEFAULT 'new'
        CHECK (review_status IN ('new','scoring','scored','approved','rejected','expired'));

ALTER TABLE public.signal_candidates
    ADD COLUMN IF NOT EXISTS updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW();

-- Indexes for the new columns
CREATE INDEX IF NOT EXISTS idx_signal_candidates_review_status
    ON public.signal_candidates (review_status);

CREATE INDEX IF NOT EXISTS idx_signal_candidates_source_signal_id
    ON public.signal_candidates (source_signal_id);

-- ─────────────────────────────────────────────────────────────────────────────
-- Verify all columns exist:
-- SELECT column_name FROM information_schema.columns
--   WHERE table_name = 'signal_candidates' ORDER BY ordinal_position;
-- ─────────────────────────────────────────────────────────────────────────────
