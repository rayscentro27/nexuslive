-- ─────────────────────────────────────────────────────────────────────────────
-- Phase 3: Signal Scoring Layer
-- Purpose : Canonical signal pipeline for AFinalChapter educational portal.
--           Raw normalized signals → scored candidates → approved educational records.
-- Tables  : signal_candidates, signal_scores, signal_reviews, approved_signals
-- Run via : Supabase SQL Editor (Settings → SQL Editor)
-- ─────────────────────────────────────────────────────────────────────────────

BEGIN;

-- ─── signal_candidates ────────────────────────────────────────────────────────
-- Normalized incoming signals staged for scoring and approval.
-- Source: tv_normalized_signals (after risk gate passes).
-- Raw signal data never reaches the portal — only approved_signals does.

CREATE TABLE IF NOT EXISTS signal_candidates (
    id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id        UUID,
    source           TEXT        NOT NULL DEFAULT 'tradingview',
    source_signal_id UUID,                           -- FK to tv_normalized_signals.id
    symbol           TEXT        NOT NULL,
    market_type      TEXT,                           -- forex | crypto | equity | futures | options | commodities | indices
    setup_type       TEXT,                           -- breakout | reversal | trend_continuation | range | pullback | momentum | ...
    direction        TEXT,                           -- long | short
    timeframe        TEXT,                           -- 1m | 5m | 15m | 1h | 4h | 1D | 1W
    entry_zone       JSONB,                          -- { "price": 1.2345 }
    stop_zone        JSONB,                          -- { "price": 1.2300 }
    target_zone      JSONB,                          -- { "price": 1.2400 }
    raw_payload      JSONB,                          -- full source signal row for audit
    review_status    TEXT        NOT NULL DEFAULT 'new'
                     CHECK (review_status IN ('new','scoring','scored','approved','rejected','expired')),
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_signal_candidates_review_status
    ON signal_candidates (review_status);
CREATE INDEX IF NOT EXISTS idx_signal_candidates_symbol
    ON signal_candidates (symbol);
CREATE INDEX IF NOT EXISTS idx_signal_candidates_source_signal_id
    ON signal_candidates (source_signal_id);
CREATE INDEX IF NOT EXISTS idx_signal_candidates_created_at
    ON signal_candidates (created_at DESC);


-- ─── signal_scores ────────────────────────────────────────────────────────────
-- Deterministic scoring output from signal_scoring worker.
-- One row per scoring run (allows re-scoring with a new version).
-- score_breakdown JSONB stores the per-dimension sub-scores for full auditability.

CREATE TABLE IF NOT EXISTS signal_scores (
    id                   UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id            UUID,
    signal_candidate_id  UUID        NOT NULL REFERENCES signal_candidates(id) ON DELETE CASCADE,
    score_total          NUMERIC(5,2) NOT NULL DEFAULT 0,
    score_setup_quality  NUMERIC(5,2) NOT NULL DEFAULT 0,   -- technical merit   (max 25)
    score_risk_quality   NUMERIC(5,2) NOT NULL DEFAULT 0,   -- stop/target/R:R   (max 25)
    score_confirmation   NUMERIC(5,2) NOT NULL DEFAULT 0,   -- AI review quality (max 25)
    score_clarity        NUMERIC(5,2) NOT NULL DEFAULT 0,   -- completeness      (max 25)
    confidence_label     TEXT        CHECK (confidence_label IN ('low','medium','high')),
    risk_label           TEXT        CHECK (risk_label IN ('low','medium','high')),
    rr_ratio             NUMERIC(6,3),                      -- reward:risk at scoring time
    scoring_version      TEXT        NOT NULL DEFAULT '1.0',
    score_breakdown      JSONB,                             -- per-dimension sub-score audit
    notes                TEXT,                              -- pipe-separated scoring notes
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_signal_scores_candidate
    ON signal_scores (signal_candidate_id);


-- ─── signal_reviews ───────────────────────────────────────────────────────────
-- Immutable audit trail of every review action taken on a candidate.
-- Every approve/reject/hold/expire writes one row.

CREATE TABLE IF NOT EXISTS signal_reviews (
    id                   UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id            UUID,
    signal_candidate_id  UUID        NOT NULL REFERENCES signal_candidates(id) ON DELETE CASCADE,
    review_action        TEXT        NOT NULL
                         CHECK (review_action IN ('approve','reject','hold','expire')),
    reviewer_type        TEXT        NOT NULL DEFAULT 'system'
                         CHECK (reviewer_type IN ('system','ai','human')),
    score_total          NUMERIC(5,2),   -- snapshot at review time
    confidence_label     TEXT,
    risk_label           TEXT,
    notes                TEXT,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_signal_reviews_candidate
    ON signal_reviews (signal_candidate_id);
CREATE INDEX IF NOT EXISTS idx_signal_reviews_action
    ON signal_reviews (review_action, created_at DESC);


-- ─── approved_signals ─────────────────────────────────────────────────────────
-- Client-safe educational signal records.
-- These are the ONLY records the AFinalChapter portal may read.
-- Raw price/execution data from signal_candidates is never exposed here.
-- Content is AI-generated (headline, client_summary, etc.) or template-generated.

CREATE TABLE IF NOT EXISTS approved_signals (
    id                UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id         UUID,
    source_signal_id  UUID,                   -- FK to signal_candidates.id
    symbol            TEXT        NOT NULL,
    market_type       TEXT,                   -- forex | crypto | equity | futures | ...
    setup_type        TEXT,                   -- breakout | reversal | trend_continuation | ...
    direction         TEXT,                   -- long | short
    timeframe         TEXT,                   -- 1m | 5m | 1h | 4h | 1D ...
    -- Educational content (AI-generated or template-generated)
    headline          TEXT        NOT NULL,   -- one-line title, max 80 chars
    client_summary    TEXT        NOT NULL,   -- 2-3 sentences: setup, meaning, key levels
    why_it_matters    TEXT,                   -- 1-2 sentences: why this pattern is notable
    invalidation_note TEXT,                   -- when/how signal becomes invalid
    -- Quality labels derived from scoring
    confidence_label  TEXT        CHECK (confidence_label IN ('low','medium','high')),
    risk_label        TEXT        CHECK (risk_label IN ('low','medium','high')),
    score_total       NUMERIC(5,2),
    -- Publish lifecycle
    published         BOOLEAN     NOT NULL DEFAULT false,
    published_at      TIMESTAMPTZ,
    expires_at        TIMESTAMPTZ,
    review_status     TEXT        NOT NULL DEFAULT 'new'
                      CHECK (review_status IN ('new','reviewed','approved','rejected','expired')),
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Portal read path: published=true AND not expired AND status='approved'
CREATE INDEX IF NOT EXISTS idx_approved_signals_portal
    ON approved_signals (published, review_status, expires_at)
    WHERE published = true AND review_status = 'approved';

CREATE INDEX IF NOT EXISTS idx_approved_signals_symbol
    ON approved_signals (symbol);
CREATE INDEX IF NOT EXISTS idx_approved_signals_market_type
    ON approved_signals (market_type);
CREATE INDEX IF NOT EXISTS idx_approved_signals_published_at
    ON approved_signals (published_at DESC);


-- ─── expire stale approved_signals ────────────────────────────────────────────
-- Optional: a cron or worker can run this periodically.
-- Not auto-applied — document it for ops to schedule.
-- UPDATE approved_signals
--   SET review_status = 'expired', updated_at = NOW()
--   WHERE published = true
--     AND review_status = 'approved'
--     AND expires_at < NOW();

COMMIT;
