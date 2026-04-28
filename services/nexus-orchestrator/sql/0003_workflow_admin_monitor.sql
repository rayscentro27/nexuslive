-- 0003_workflow_admin_monitor.sql
-- Joined admin monitoring view.
-- Combines workflow_outputs + orchestrator_workflow_runs + job_queue
-- into one flat row per workflow — ready for the Windows Workforce Monitor UI.
--
-- Usage:
--   SELECT * FROM workflow_admin_monitor ORDER BY workflow_started_at DESC;
--   SELECT * FROM workflow_admin_monitor WHERE tenant_id = '...' AND workflow_type = 'credit_analysis';

CREATE OR REPLACE VIEW workflow_admin_monitor AS
SELECT
  -- ── Workflow identity ─────────────────────────────────────────────────────
  wr.id                        AS workflow_id,
  wr.workflow_type,
  wr.status                    AS workflow_status,
  wr.trigger_event             AS event_id,
  wr.tenant_id,
  wr.started_at                AS workflow_started_at,
  wr.completed_at              AS workflow_completed_at,

  -- ── Clean output (what the UI actually shows) ─────────────────────────────
  wo.status                    AS output_status,
  wo.summary,
  wo.readiness_level,
  wo.score,
  wo.primary_action_key,
  wo.primary_action_title,
  wo.primary_action_description,
  wo.priority,
  wo.blockers,
  wo.strengths,
  wo.suggested_tasks,
  wo.client_id,
  wo.subject_type,
  wo.subject_id,
  wo.updated_at                AS output_updated_at,

  -- ── Job execution details ─────────────────────────────────────────────────
  jq.id                        AS job_id,
  jq.job_type,
  jq.status                    AS job_status,
  jq.attempt_count,
  jq.last_error,
  jq.worker_id                 AS executed_by_worker,
  jq.created_at                AS job_created_at,
  jq.completed_at              AS job_completed_at,

  -- ── Timing ────────────────────────────────────────────────────────────────
  EXTRACT(EPOCH FROM (jq.completed_at - jq.created_at))::INTEGER
                               AS job_duration_secs,
  EXTRACT(EPOCH FROM (wr.completed_at - wr.started_at))::INTEGER
                               AS workflow_duration_secs

FROM orchestrator_workflow_runs wr

-- Join output summary (may not exist yet if workflow in flight)
LEFT JOIN workflow_outputs wo
  ON wo.workflow_id = wr.id

-- Join the most recent job for this workflow
-- (matches on workflow_id stored in job payload)
LEFT JOIN LATERAL (
  SELECT
    id,
    job_type,
    status,
    attempt_count,
    last_error,
    worker_id,
    created_at,
    completed_at
  FROM   job_queue
  WHERE  (payload->>'workflow_id') = wr.id::TEXT
  ORDER BY created_at DESC
  LIMIT  1
) jq ON true;

-- Grant read to authenticated and anon roles (RLS on base tables still applies)
GRANT SELECT ON workflow_admin_monitor TO authenticated, anon;
