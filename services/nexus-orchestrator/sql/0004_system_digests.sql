-- 0004_system_digests.sql
-- Daily system digest storage.
-- Run in Supabase SQL editor after 0003_workflow_admin_monitor.sql.

CREATE TABLE IF NOT EXISTS system_digests (
  id           uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  digest_type  text        NOT NULL DEFAULT 'daily',
  window_hours int         NOT NULL DEFAULT 24,
  summary      text,
  payload      jsonb       NOT NULL DEFAULT '{}',
  created_at   timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_system_digests_created ON system_digests (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_system_digests_type    ON system_digests (digest_type, created_at DESC);

-- PostgREST schema cache reload
NOTIFY pgrst, 'reload schema';
