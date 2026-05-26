-- =============================================================================
-- Hermes Executive Memory Layer
-- Migration: 20260525000003_hermes_executive_memory
-- =============================================================================

CREATE TABLE IF NOT EXISTS hermes_executive_memory (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category        TEXT NOT NULL UNIQUE,   -- one of 9 CATEGORIES
    items           JSONB NOT NULL DEFAULT '[]'::jsonb,
    updated_by      TEXT NOT NULL DEFAULT 'system',
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_hem_category ON hermes_executive_memory(category);
CREATE INDEX IF NOT EXISTS idx_hem_updated  ON hermes_executive_memory(updated_at DESC);

ALTER TABLE hermes_executive_memory ENABLE ROW LEVEL SECURITY;
CREATE POLICY "service_role_all_hem"
    ON hermes_executive_memory FOR ALL
    USING (auth.role() = 'service_role');

-- Seed default categories so rows exist for upsert
INSERT INTO hermes_executive_memory (category, items) VALUES
    ('monetization_priorities',  '[]'),
    ('business_goals',           '[]'),
    ('affiliate_campaigns',      '[]'),
    ('content_backlog',          '[]'),
    ('unfinished_systems',       '[]'),
    ('infrastructure_problems',  '[]'),
    ('active_workers',           '[]'),
    ('operational_philosophy',   '[]'),
    ('execution_priorities',     '[]')
ON CONFLICT (category) DO NOTHING;

-- ── hermes_quality_flags ──────────────────────────────────────────────────────
-- Track response quality escalations for pattern analysis

CREATE TABLE IF NOT EXISTS hermes_quality_flags (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chat_id         TEXT,
    reason          TEXT NOT NULL,
    filler_count    INT  NOT NULL DEFAULT 0,
    ops_signals     INT  NOT NULL DEFAULT 0,
    score           NUMERIC(4,3),
    escalated       BOOLEAN NOT NULL DEFAULT false,
    user_message    TEXT,
    flagged_excerpt TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_hqf_reason  ON hermes_quality_flags(reason);
CREATE INDEX IF NOT EXISTS idx_hqf_date    ON hermes_quality_flags(created_at DESC);

ALTER TABLE hermes_quality_flags ENABLE ROW LEVEL SECURITY;
CREATE POLICY "service_role_all_hqf"
    ON hermes_quality_flags FOR ALL
    USING (auth.role() = 'service_role');
