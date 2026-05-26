-- =============================================================================
-- Nexus Worker Quota + Failure Tracking
-- Migration: 20260525000002_worker_quotas
-- Created: 2026-05-25
-- =============================================================================

-- ── worker_daily_quotas ───────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS worker_daily_quotas (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    worker_id       TEXT NOT NULL,
    quota_type      TEXT NOT NULL,          -- content_pieces, insights, opportunities, strategy_tests, reports
    target_per_day  INT NOT NULL DEFAULT 1,
    current_count   INT NOT NULL DEFAULT 0,
    quota_date      DATE NOT NULL DEFAULT CURRENT_DATE,
    met             BOOLEAN NOT NULL DEFAULT false,
    missed          BOOLEAN NOT NULL DEFAULT false,
    last_updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (worker_id, quota_type, quota_date)
);

CREATE INDEX IF NOT EXISTS idx_wdq_worker ON worker_daily_quotas(worker_id);
CREATE INDEX IF NOT EXISTS idx_wdq_date   ON worker_daily_quotas(quota_date DESC);
CREATE INDEX IF NOT EXISTS idx_wdq_missed ON worker_daily_quotas(missed) WHERE missed = true;

ALTER TABLE worker_daily_quotas ENABLE ROW LEVEL SECURITY;
CREATE POLICY "service_role_all_wdq"
    ON worker_daily_quotas FOR ALL
    USING (auth.role() = 'service_role');

-- ── worker_failure_events ─────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS worker_failure_events (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    worker_id       TEXT NOT NULL,
    failure_type    TEXT NOT NULL,          -- quota_miss, task_error, timeout, crash, stalled
    task_id         UUID,                   -- linked agent_dispatch_task if applicable
    error_message   TEXT,
    stack_trace     TEXT,
    context         JSONB,                  -- additional metadata
    resolved        BOOLEAN NOT NULL DEFAULT false,
    resolved_at     TIMESTAMPTZ,
    alerted_hermes  BOOLEAN NOT NULL DEFAULT false,
    alerted_at      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_wfe_worker   ON worker_failure_events(worker_id);
CREATE INDEX IF NOT EXISTS idx_wfe_type     ON worker_failure_events(failure_type);
CREATE INDEX IF NOT EXISTS idx_wfe_unresolved ON worker_failure_events(resolved) WHERE resolved = false;
CREATE INDEX IF NOT EXISTS idx_wfe_date     ON worker_failure_events(created_at DESC);

ALTER TABLE worker_failure_events ENABLE ROW LEVEL SECURITY;
CREATE POLICY "service_role_all_wfe"
    ON worker_failure_events FOR ALL
    USING (auth.role() = 'service_role');

-- ── content_outputs ───────────────────────────────────────────────────────────
-- Generated worker outputs: content, reports, insights (separate from legacy workflow_outputs)

CREATE TABLE IF NOT EXISTS content_outputs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    worker_id       TEXT NOT NULL,
    output_type     TEXT NOT NULL,          -- youtube_script, newsletter, tiktok_hook, x_post, linkedin_post, seo_article, strategy_report, insight, recommendation
    title           TEXT NOT NULL,
    body            TEXT NOT NULL DEFAULT '',
    metadata        JSONB,
    status          TEXT NOT NULL DEFAULT 'draft',
    evidence_path   TEXT,
    evidence_ref    TEXT,
    word_count      INT,
    generated_by    TEXT NOT NULL DEFAULT 'content_worker',
    requires_approval BOOLEAN NOT NULL DEFAULT true,
    approved_at     TIMESTAMPTZ,
    approved_by     TEXT,
    published_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_co_worker  ON content_outputs(worker_id);
CREATE INDEX IF NOT EXISTS idx_co_type    ON content_outputs(output_type);
CREATE INDEX IF NOT EXISTS idx_co_status  ON content_outputs(status);
CREATE INDEX IF NOT EXISTS idx_co_date    ON content_outputs(created_at DESC);

ALTER TABLE content_outputs ENABLE ROW LEVEL SECURITY;
CREATE POLICY "service_role_all_co"
    ON content_outputs FOR ALL
    USING (auth.role() = 'service_role');

CREATE OR REPLACE TRIGGER trg_co_updated_at
    BEFORE UPDATE ON content_outputs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
