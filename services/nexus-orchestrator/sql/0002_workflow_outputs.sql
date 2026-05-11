-- 0002_workflow_outputs.sql
-- Clean frontend-facing summary layer for all completed workflows.
-- Workers upsert one row per workflow_id after completing their job.
-- Frontend reads this table instead of digging into job_queue.payload.result.

CREATE TABLE IF NOT EXISTS workflow_outputs (
  id                         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),

  -- Workflow identity
  workflow_id                UUID        NOT NULL,  -- references orchestrator_workflow_runs.id (soft ref)
  workflow_type              TEXT        NOT NULL,  -- 'research_refresh', 'funding_review', 'credit_analysis'
  tenant_id                  UUID,
  client_id                  TEXT,

  -- Subject (what was analyzed)
  subject_type               TEXT,                  -- 'funding_profile', 'credit_report', 'research'
  subject_id                 TEXT,                  -- report_id, tenant_id as text, etc.

  -- Outcome
  status                     TEXT        NOT NULL DEFAULT 'completed', -- 'completed', 'blocked', 'failed'
  summary                    TEXT,

  -- Primary recommended action
  primary_action_key         TEXT,
  primary_action_title       TEXT,
  primary_action_description TEXT,
  priority                   TEXT,                  -- 'low', 'medium', 'high'

  -- Scoring
  score                      INTEGER,               -- 0-100 readiness/quality score
  readiness_level            TEXT,                  -- 'poor','improving','fair','strong' / 'not_ready','preparing','near_ready','ready'

  -- Structured lists (frontend renders these directly)
  blockers                   JSONB       NOT NULL DEFAULT '[]',
  strengths                  JSONB       NOT NULL DEFAULT '[]',
  suggested_tasks            JSONB       NOT NULL DEFAULT '[]',

  -- Source traceability
  source_job_id              UUID,                  -- job_queue.id that produced this output
  raw_output                 JSONB,                 -- overflow — extra fields not in schema above

  created_at                 TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at                 TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  -- One summary row per workflow run; re-runs overwrite
  CONSTRAINT workflow_outputs_workflow_id_unique UNIQUE (workflow_id)
);

-- Indexes for common frontend queries
CREATE INDEX IF NOT EXISTS workflow_outputs_tenant_id_idx      ON workflow_outputs (tenant_id);
CREATE INDEX IF NOT EXISTS workflow_outputs_workflow_type_idx  ON workflow_outputs (workflow_type);
CREATE INDEX IF NOT EXISTS workflow_outputs_status_idx         ON workflow_outputs (status);
CREATE INDEX IF NOT EXISTS workflow_outputs_created_at_idx     ON workflow_outputs (created_at DESC);

-- RLS — service role has full access; authenticated users see own tenant
ALTER TABLE workflow_outputs ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE tablename = 'workflow_outputs' AND policyname = 'service_role_all'
  ) THEN
    CREATE POLICY service_role_all ON workflow_outputs
      FOR ALL TO service_role USING (true) WITH CHECK (true);
  END IF;
END $$;
