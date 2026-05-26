-- =============================================================================
-- Nexus Intelligence Divisions — Scout + Consensus + KPI Tables
-- Migration: 20260526000001_nexus_intelligence_divisions
-- =============================================================================

-- ── scout_outputs ─────────────────────────────────────────────────────────────
-- Raw findings from each intelligence scout

CREATE TABLE IF NOT EXISTS scout_outputs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scout_id        TEXT NOT NULL,
    division        TEXT NOT NULL,          -- market_intelligence | monetization_intelligence
    output_type     TEXT NOT NULL,          -- signal, opportunity, briefing, report, script
    title           TEXT NOT NULL,
    summary         TEXT NOT NULL DEFAULT '',
    raw_data        JSONB,
    confidence      NUMERIC(5,2),           -- 0-100
    priority        TEXT NOT NULL DEFAULT 'medium',
    evidence_ref    TEXT,
    processed       BOOLEAN NOT NULL DEFAULT false,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_so_scout    ON scout_outputs(scout_id);
CREATE INDEX IF NOT EXISTS idx_so_division ON scout_outputs(division);
CREATE INDEX IF NOT EXISTS idx_so_priority ON scout_outputs(priority);
CREATE INDEX IF NOT EXISTS idx_so_date     ON scout_outputs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_so_unproc  ON scout_outputs(processed) WHERE processed = false;

ALTER TABLE scout_outputs ENABLE ROW LEVEL SECURITY;
CREATE POLICY "service_role_all_so"
    ON scout_outputs FOR ALL
    USING (auth.role() = 'service_role');

-- ── opportunity_rankings ──────────────────────────────────────────────────────
-- Consensus-scored and ranked opportunities

CREATE TABLE IF NOT EXISTS opportunity_rankings (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    opportunity_type    TEXT NOT NULL,
    title               TEXT NOT NULL,
    summary             TEXT NOT NULL DEFAULT '',
    consensus_score     NUMERIC(5,1) NOT NULL DEFAULT 0,
    priority            TEXT NOT NULL DEFAULT 'medium',
    roi_potential       NUMERIC(5,1),
    traffic_potential   NUMERIC(5,1),
    ease_of_execution   NUMERIC(5,1),
    urgency             NUMERIC(5,1),
    scout_alignment     INT  NOT NULL DEFAULT 1,
    source              TEXT,
    action_taken        BOOLEAN NOT NULL DEFAULT false,
    dismissed           BOOLEAN NOT NULL DEFAULT false,
    ranked_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_or_score    ON opportunity_rankings(consensus_score DESC);
CREATE INDEX IF NOT EXISTS idx_or_priority ON opportunity_rankings(priority);
CREATE INDEX IF NOT EXISTS idx_or_date     ON opportunity_rankings(ranked_at DESC);

ALTER TABLE opportunity_rankings ENABLE ROW LEVEL SECURITY;
CREATE POLICY "service_role_all_or"
    ON opportunity_rankings FOR ALL
    USING (auth.role() = 'service_role');

-- ── kpi_snapshots ─────────────────────────────────────────────────────────────
-- Daily KPI tracking for revenue, membership, market intelligence goals

CREATE TABLE IF NOT EXISTS kpi_snapshots (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    snapshot_date           DATE NOT NULL DEFAULT CURRENT_DATE,
    division                TEXT NOT NULL,
    metric_name             TEXT NOT NULL,
    metric_value            NUMERIC,
    target_value            NUMERIC,
    pct_to_target           NUMERIC GENERATED ALWAYS AS (
                                CASE WHEN target_value > 0
                                THEN ROUND((metric_value / target_value * 100)::numeric, 1)
                                ELSE NULL END
                            ) STORED,
    notes                   TEXT,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (snapshot_date, division, metric_name)
);

CREATE INDEX IF NOT EXISTS idx_kpi_date     ON kpi_snapshots(snapshot_date DESC);
CREATE INDEX IF NOT EXISTS idx_kpi_division ON kpi_snapshots(division);
CREATE INDEX IF NOT EXISTS idx_kpi_metric   ON kpi_snapshots(metric_name);

ALTER TABLE kpi_snapshots ENABLE ROW LEVEL SECURITY;
CREATE POLICY "service_role_all_kpi"
    ON kpi_snapshots FOR ALL
    USING (auth.role() = 'service_role');

-- ── optimization_experiments ──────────────────────────────────────────────────
-- Recursive optimization loop: test one variable, measure, score, keep/reject

CREATE TABLE IF NOT EXISTS optimization_experiments (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    experiment_name TEXT NOT NULL,
    division        TEXT NOT NULL,
    variable_tested TEXT NOT NULL,
    hypothesis      TEXT,
    baseline_value  NUMERIC,
    result_value    NUMERIC,
    improvement_pct NUMERIC GENERATED ALWAYS AS (
                        CASE WHEN baseline_value > 0
                        THEN ROUND(((result_value - baseline_value) / baseline_value * 100)::numeric, 1)
                        ELSE NULL END
                    ) STORED,
    outcome         TEXT,              -- winner | loser | inconclusive
    status          TEXT NOT NULL DEFAULT 'running',
    evidence_ref    TEXT,
    started_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_oe_division ON optimization_experiments(division);
CREATE INDEX IF NOT EXISTS idx_oe_outcome  ON optimization_experiments(outcome);
CREATE INDEX IF NOT EXISTS idx_oe_status   ON optimization_experiments(status);

ALTER TABLE optimization_experiments ENABLE ROW LEVEL SECURITY;
CREATE POLICY "service_role_all_oe"
    ON optimization_experiments FOR ALL
    USING (auth.role() = 'service_role');

-- Seed Day 1 KPI baseline
INSERT INTO kpi_snapshots (snapshot_date, division, metric_name, metric_value, target_value, notes)
VALUES
    (CURRENT_DATE, 'monetization_intelligence', 'newsletter_subscribers', 0, 250, 'Day 1 baseline'),
    (CURRENT_DATE, 'monetization_intelligence', 'affiliate_clicks', 0, 500, 'Day 1 baseline'),
    (CURRENT_DATE, 'monetization_intelligence', 'weekly_revenue_usd', 0, 1000, 'Day 1 baseline'),
    (CURRENT_DATE, 'monetization_intelligence', 'funding_leads', 0, 15, 'Day 1 baseline'),
    (CURRENT_DATE, 'market_intelligence', 'strategies_in_paper_testing', 0, 3, 'Day 1 baseline'),
    (CURRENT_DATE, 'market_intelligence', 'backtest_count', 0, 100, 'Day 1 baseline')
ON CONFLICT (snapshot_date, division, metric_name) DO NOTHING;
