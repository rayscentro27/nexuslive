-- =============================================================================
-- Intelligence Source Registry + Extractions
-- Migration: 20260526000002_intelligence_sources
-- =============================================================================

-- ── intelligence_sources ──────────────────────────────────────────────────────
-- Registered intelligence sources (YouTube channels + videos)

CREATE TABLE IF NOT EXISTS intelligence_sources (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id       TEXT NOT NULL UNIQUE,
    name            TEXT NOT NULL,
    url             TEXT NOT NULL,
    source_type     TEXT NOT NULL DEFAULT 'video',  -- video | channel
    division        TEXT NOT NULL,
    scout_id        TEXT NOT NULL,
    tier            TEXT NOT NULL DEFAULT 'B',
    frequency_hours INT  NOT NULL DEFAULT 168,
    extraction_goals JSONB,
    tags            JSONB,
    enabled         BOOLEAN NOT NULL DEFAULT true,
    last_processed_at TIMESTAMPTZ,
    total_extractions INT NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_is_division ON intelligence_sources(division);
CREATE INDEX IF NOT EXISTS idx_is_scout    ON intelligence_sources(scout_id);
CREATE INDEX IF NOT EXISTS idx_is_tier     ON intelligence_sources(tier);

ALTER TABLE intelligence_sources ENABLE ROW LEVEL SECURITY;
CREATE POLICY "service_role_all_is"
    ON intelligence_sources FOR ALL
    USING (auth.role() = 'service_role');

-- ── source_extractions ────────────────────────────────────────────────────────
-- Intelligence extracted from each video/transcript

CREATE TABLE IF NOT EXISTS source_extractions (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id           TEXT NOT NULL,
    division            TEXT NOT NULL,
    scout_id            TEXT NOT NULL,
    video_id            TEXT NOT NULL,
    video_title         TEXT NOT NULL DEFAULT '',
    source_url          TEXT,
    publish_date        DATE,
    tier                TEXT NOT NULL DEFAULT 'B',
    extraction_data     JSONB,          -- full LLM extraction
    summary             TEXT,
    confidence_score    NUMERIC(5,2),   -- weighted: base × tier × recency
    raw_content_chars   INT,
    tags                JSONB,
    fed_to_consensus    BOOLEAN NOT NULL DEFAULT false,
    fed_to_briefing     BOOLEAN NOT NULL DEFAULT false,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (source_id, video_id)        -- don't re-extract same video from same source
);

CREATE INDEX IF NOT EXISTS idx_se_source    ON source_extractions(source_id);
CREATE INDEX IF NOT EXISTS idx_se_division  ON source_extractions(division);
CREATE INDEX IF NOT EXISTS idx_se_scout     ON source_extractions(scout_id);
CREATE INDEX IF NOT EXISTS idx_se_conf      ON source_extractions(confidence_score DESC);
CREATE INDEX IF NOT EXISTS idx_se_date      ON source_extractions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_se_unfed     ON source_extractions(fed_to_consensus) WHERE fed_to_consensus = false;

ALTER TABLE source_extractions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "service_role_all_se"
    ON source_extractions FOR ALL
    USING (auth.role() = 'service_role');

-- ── intelligence_daily_summaries ──────────────────────────────────────────────
-- Daily rollup of intelligence across all sources

CREATE TABLE IF NOT EXISTS intelligence_daily_summaries (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    summary_date        DATE NOT NULL DEFAULT CURRENT_DATE,
    division            TEXT NOT NULL,
    sources_processed   INT  NOT NULL DEFAULT 0,
    videos_processed    INT  NOT NULL DEFAULT 0,
    findings_count      INT  NOT NULL DEFAULT 0,
    top_insights        JSONB,           -- top 5 insights of the day
    top_opportunities   JSONB,           -- top 3 opportunities identified
    consensus_run       BOOLEAN NOT NULL DEFAULT false,
    body_markdown       TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (summary_date, division)
);

CREATE INDEX IF NOT EXISTS idx_ids_date     ON intelligence_daily_summaries(summary_date DESC);
CREATE INDEX IF NOT EXISTS idx_ids_division ON intelligence_daily_summaries(division);

ALTER TABLE intelligence_daily_summaries ENABLE ROW LEVEL SECURITY;
CREATE POLICY "service_role_all_ids"
    ON intelligence_daily_summaries FOR ALL
    USING (auth.role() = 'service_role');

-- Auto-update updated_at on intelligence_sources
CREATE OR REPLACE TRIGGER trg_is_updated_at
    BEFORE UPDATE ON intelligence_sources
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
