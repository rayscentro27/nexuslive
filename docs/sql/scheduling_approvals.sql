-- ============================================================
-- Source Scheduling + Scan Policies + Command Approvals
-- Run in Supabase SQL editor
-- ============================================================

-- 1. Source Schedules
CREATE TABLE IF NOT EXISTS source_schedules (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  source_id        uuid        NOT NULL,
  schedule_type    text        NOT NULL DEFAULT 'manual',
  interval_minutes integer,
  next_run_at      timestamptz,
  last_run_at      timestamptz,
  status           text        NOT NULL DEFAULT 'active',
  created_at       timestamptz DEFAULT now(),
  updated_at       timestamptz DEFAULT now(),
  UNIQUE(source_id)
);

CREATE INDEX IF NOT EXISTS idx_source_schedules_source   ON source_schedules(source_id);
CREATE INDEX IF NOT EXISTS idx_source_schedules_next_run ON source_schedules(next_run_at);
CREATE INDEX IF NOT EXISTS idx_source_schedules_status   ON source_schedules(status);

-- 2. Source Scan Policies
CREATE TABLE IF NOT EXISTS source_scan_policies (
  id                       uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  source_type              text        NOT NULL,
  domain_keyword           text,
  default_priority         text        NOT NULL DEFAULT 'medium',
  default_schedule_type    text        NOT NULL DEFAULT 'daily',
  default_interval_minutes integer     DEFAULT 1440,
  stale_after_hours        integer     DEFAULT 24,
  max_runs_per_day         integer     DEFAULT 2,
  active                   boolean     DEFAULT true,
  created_at               timestamptz DEFAULT now(),
  UNIQUE(source_type, domain_keyword)
);

CREATE INDEX IF NOT EXISTS idx_scan_policies_type   ON source_scan_policies(source_type);
CREATE INDEX IF NOT EXISTS idx_scan_policies_active ON source_scan_policies(active);

-- Seed default policies
INSERT INTO source_scan_policies
  (source_type, domain_keyword, default_priority, default_schedule_type, default_interval_minutes, stale_after_hours, max_runs_per_day)
VALUES
  ('youtube_channel', NULL,       'high',   'interval', 120,  8,   12),
  ('rss_feed',        NULL,       'medium', 'interval', 60,   4,   24),
  ('website',         'grant',    'medium', 'daily',    1440, 24,  2),
  ('website',         'funding',  'medium', 'daily',    1440, 24,  2),
  ('website',         'trading',  'high',   'daily',    480,  12,  3),
  ('website',         NULL,       'low',    'daily',    1440, 48,  1),
  ('generic',         NULL,       'low',    'daily',    1440, 48,  1)
ON CONFLICT (source_type, domain_keyword) DO NOTHING;

-- 3. Command Approvals
CREATE TABLE IF NOT EXISTS command_approvals (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  command_id      uuid        NOT NULL,
  approval_level  text        NOT NULL DEFAULT 'low',
  approval_status text        NOT NULL DEFAULT 'not_required',
  approved_by     text,
  approved_at     timestamptz,
  notes           text,
  created_at      timestamptz DEFAULT now(),
  UNIQUE(command_id)
);

CREATE INDEX IF NOT EXISTS idx_cmd_approvals_command ON command_approvals(command_id);
CREATE INDEX IF NOT EXISTS idx_cmd_approvals_status  ON command_approvals(approval_status);
CREATE INDEX IF NOT EXISTS idx_cmd_approvals_level   ON command_approvals(approval_level);
CREATE INDEX IF NOT EXISTS idx_cmd_approvals_created ON command_approvals(created_at DESC);
