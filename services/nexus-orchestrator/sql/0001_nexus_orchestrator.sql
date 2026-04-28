-- ============================================================
-- 0001_nexus_orchestrator.sql
-- Run once in Supabase SQL editor (Dashboard → SQL Editor).
-- Safe to re-run: all statements use IF NOT EXISTS / OR REPLACE.
-- ============================================================

-- ── system_events ────────────────────────────────────────────────────────
-- Central event bus. Orchestrator polls this table.

CREATE TABLE IF NOT EXISTS system_events (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  event_type       text        NOT NULL,
  status           text        NOT NULL DEFAULT 'pending',   -- pending | claimed | completed | failed
  payload          jsonb       NOT NULL DEFAULT '{}',
  attempt_count    int         NOT NULL DEFAULT 0,
  last_error       text,
  claimed_by       text,
  claimed_at       timestamptz,
  lease_expires_at timestamptz,
  completed_at     timestamptz,
  created_at       timestamptz NOT NULL DEFAULT now(),
  updated_at       timestamptz NOT NULL DEFAULT now()
);

-- Index for the hot poll path
CREATE INDEX IF NOT EXISTS idx_system_events_poll
  ON system_events (status, created_at)
  WHERE status = 'pending';

CREATE INDEX IF NOT EXISTS idx_system_events_lease
  ON system_events (lease_expires_at)
  WHERE status = 'claimed';

-- Auto-update updated_at
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_system_events_updated_at ON system_events;
CREATE TRIGGER trg_system_events_updated_at
  BEFORE UPDATE ON system_events
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ── workflow_instances ────────────────────────────────────────────────────
-- One row per workflow execution spawned by the orchestrator.

CREATE TABLE IF NOT EXISTS workflow_instances (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  workflow_type   text        NOT NULL,
  status          text        NOT NULL DEFAULT 'running',   -- running | completed | failed
  trigger_event   uuid        REFERENCES system_events(id) ON DELETE SET NULL,
  tenant_id       text,
  metadata        jsonb       NOT NULL DEFAULT '{}',
  started_at      timestamptz NOT NULL DEFAULT now(),
  completed_at    timestamptz,
  created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_workflow_instances_type_status
  ON workflow_instances (workflow_type, status);

CREATE INDEX IF NOT EXISTS idx_workflow_instances_tenant
  ON workflow_instances (tenant_id);

-- ── job_queue additions ───────────────────────────────────────────────────
-- Add columns if they don't already exist (safe ALTER TABLE).

ALTER TABLE job_queue ADD COLUMN IF NOT EXISTS dedupe_key    text;
ALTER TABLE job_queue ADD COLUMN IF NOT EXISTS max_attempts  int NOT NULL DEFAULT 3;
ALTER TABLE job_queue ADD COLUMN IF NOT EXISTS available_at  timestamptz DEFAULT now();
ALTER TABLE job_queue ADD COLUMN IF NOT EXISTS lease_expires_at timestamptz;

CREATE INDEX IF NOT EXISTS idx_job_queue_dedupe
  ON job_queue (dedupe_key, status)
  WHERE dedupe_key IS NOT NULL;

-- ── system_errors additions ───────────────────────────────────────────────
ALTER TABLE system_errors ADD COLUMN IF NOT EXISTS service   text;
ALTER TABLE system_errors ADD COLUMN IF NOT EXISTS component text;
ALTER TABLE system_errors ADD COLUMN IF NOT EXISTS metadata  jsonb DEFAULT '{}';

-- ── RLS ───────────────────────────────────────────────────────────────────
-- Service role key bypasses RLS. Enable for anon safety if needed.
ALTER TABLE system_events      ENABLE ROW LEVEL SECURITY;
ALTER TABLE workflow_instances ENABLE ROW LEVEL SECURITY;

-- Allow service role full access (policy only applies to non-service roles)
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename='system_events' AND policyname='service_full_access') THEN
    CREATE POLICY service_full_access ON system_events USING (true) WITH CHECK (true);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename='workflow_instances' AND policyname='service_full_access') THEN
    CREATE POLICY service_full_access ON workflow_instances USING (true) WITH CHECK (true);
  END IF;
END $$;
