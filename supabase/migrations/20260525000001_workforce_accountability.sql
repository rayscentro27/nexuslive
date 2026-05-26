-- =============================================================================
-- Nexus Workforce Accountability Layer
-- Migration: 20260525000001_workforce_accountability
-- Created:   2026-05-25
--
-- Tables:
--   worker_productivity_rollups  -- daily per-worker metrics
--   worker_daily_reports         -- generated briefing text per worker
--   worker_recommendations       -- autonomous improvement suggestions
--
-- Also:
--   Extends agent_dispatch_tasks with evidence columns
--   Adds completed_with_evidence status support
-- =============================================================================

-- ── worker_productivity_rollups ───────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS worker_productivity_rollups (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    report_date         DATE NOT NULL,
    worker_id           TEXT NOT NULL,
    worker_role         TEXT,
    tasks_completed     INT NOT NULL DEFAULT 0,
    tasks_failed        INT NOT NULL DEFAULT 0,
    tasks_planned       INT NOT NULL DEFAULT 0,
    tasks_awaiting      INT NOT NULL DEFAULT 0,
    avg_completion_ms   BIGINT,
    productivity_score  NUMERIC(5,2) DEFAULT 0.00,  -- 0.00 – 100.00
    evidence_ratio      NUMERIC(5,2) DEFAULT 0.00,  -- % tasks with evidence
    false_completion_count INT NOT NULL DEFAULT 0,  -- tasks marked complete without evidence
    last_heartbeat_at   TIMESTAMPTZ,
    is_active           BOOLEAN NOT NULL DEFAULT true,
    notes               TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (report_date, worker_id)
);

CREATE INDEX IF NOT EXISTS idx_wpr_date  ON worker_productivity_rollups(report_date DESC);
CREATE INDEX IF NOT EXISTS idx_wpr_worker ON worker_productivity_rollups(worker_id);
CREATE INDEX IF NOT EXISTS idx_wpr_score  ON worker_productivity_rollups(productivity_score DESC);

ALTER TABLE worker_productivity_rollups ENABLE ROW LEVEL SECURITY;
CREATE POLICY "service_role_all_wpr"
    ON worker_productivity_rollups FOR ALL
    USING (auth.role() = 'service_role');

-- ── worker_daily_reports ──────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS worker_daily_reports (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    report_date     DATE NOT NULL,
    worker_id       TEXT NOT NULL,
    report_type     TEXT NOT NULL DEFAULT 'daily',   -- daily, weekly, incident
    status          TEXT NOT NULL DEFAULT 'draft',   -- draft, published, archived
    headline        TEXT,
    body_markdown   TEXT NOT NULL DEFAULT '',
    top_output      TEXT,   -- single best output of the day
    blockers        TEXT,
    recommendations TEXT,
    productivity_score NUMERIC(5,2),
    generated_by    TEXT NOT NULL DEFAULT 'ceo_briefing_system',
    sent_to_telegram BOOLEAN NOT NULL DEFAULT false,
    sent_at          TIMESTAMPTZ,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (report_date, worker_id, report_type)
);

CREATE INDEX IF NOT EXISTS idx_wdr_date   ON worker_daily_reports(report_date DESC);
CREATE INDEX IF NOT EXISTS idx_wdr_worker ON worker_daily_reports(worker_id);
CREATE INDEX IF NOT EXISTS idx_wdr_status ON worker_daily_reports(status);

ALTER TABLE worker_daily_reports ENABLE ROW LEVEL SECURITY;
CREATE POLICY "service_role_all_wdr"
    ON worker_daily_reports FOR ALL
    USING (auth.role() = 'service_role');

-- ── worker_recommendations ────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS worker_recommendations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    generated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    worker_id       TEXT,                    -- NULL = system-wide recommendation
    category        TEXT NOT NULL,           -- seo, content, affiliate, infra, monetization, audit, docs
    priority        TEXT NOT NULL DEFAULT 'medium',  -- critical, high, medium, low
    title           TEXT NOT NULL,
    description     TEXT NOT NULL,
    action_required TEXT,                    -- concrete next step
    evidence        TEXT,                    -- what triggered this recommendation
    estimated_value TEXT,                    -- revenue/time/risk impact
    status          TEXT NOT NULL DEFAULT 'open',  -- open, acknowledged, actioned, dismissed
    actioned_at     TIMESTAMPTZ,
    actioned_by     TEXT,
    expires_at      TIMESTAMPTZ,             -- NULL = never expires
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_wrec_cat      ON worker_recommendations(category);
CREATE INDEX IF NOT EXISTS idx_wrec_priority ON worker_recommendations(priority);
CREATE INDEX IF NOT EXISTS idx_wrec_status   ON worker_recommendations(status);
CREATE INDEX IF NOT EXISTS idx_wrec_gen      ON worker_recommendations(generated_at DESC);

ALTER TABLE worker_recommendations ENABLE ROW LEVEL SECURITY;
CREATE POLICY "service_role_all_wrec"
    ON worker_recommendations FOR ALL
    USING (auth.role() = 'service_role');

-- ── ceo_briefings ─────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS ceo_briefings (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    briefing_date   DATE NOT NULL DEFAULT CURRENT_DATE,
    briefing_type   TEXT NOT NULL DEFAULT 'morning',  -- morning, evening, incident, weekly
    status          TEXT NOT NULL DEFAULT 'generated', -- generated, delivered, acknowledged
    title           TEXT NOT NULL DEFAULT 'CEO Operational Briefing',
    body_markdown   TEXT NOT NULL DEFAULT '',
    system_health   JSONB,
    workforce_kpis  JSONB,
    top_actions     JSONB,          -- array of {rank, action, urgency}
    delivery_log    JSONB,          -- {telegram: true, dashboard: true, email: false}
    generated_by    TEXT NOT NULL DEFAULT 'ceo_morning_briefing',
    generated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    delivered_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_ceo_date   ON ceo_briefings(briefing_date DESC);
CREATE INDEX IF NOT EXISTS idx_ceo_type   ON ceo_briefings(briefing_type);
CREATE INDEX IF NOT EXISTS idx_ceo_status ON ceo_briefings(status);

ALTER TABLE ceo_briefings ENABLE ROW LEVEL SECURITY;
CREATE POLICY "service_role_all_ceo"
    ON ceo_briefings FOR ALL
    USING (auth.role() = 'service_role');

-- ── Evidence columns on agent_dispatch_tasks ──────────────────────────────────
-- Add evidence tracking to the existing task table.
-- Alters are idempotent via IF NOT EXISTS / DO blocks.

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='agent_dispatch_tasks' AND column_name='evidence_type') THEN
        ALTER TABLE agent_dispatch_tasks
            ADD COLUMN evidence_type    TEXT,       -- file_path | db_row_id | screenshot | commit_hash | url | execution_log | message_id
            ADD COLUMN evidence_ref     TEXT,       -- the actual value (path, ID, hash, URL, etc.)
            ADD COLUMN evidence_notes   TEXT,
            ADD COLUMN false_completion BOOLEAN NOT NULL DEFAULT false;
    END IF;
END $$;

-- ── Trigger: auto-update updated_at ──────────────────────────────────────────

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER trg_wpr_updated_at
    BEFORE UPDATE ON worker_productivity_rollups
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE OR REPLACE TRIGGER trg_wdr_updated_at
    BEFORE UPDATE ON worker_daily_reports
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE OR REPLACE TRIGGER trg_wrec_updated_at
    BEFORE UPDATE ON worker_recommendations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
