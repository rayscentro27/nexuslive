-- ── Worker hierarchy: add missing workers to control plane ───────────────────
-- Tier 1: Control & Monitoring (self-healing backbone)
INSERT INTO public.worker_control_plane
  (worker_id, worker_type, desired_state, control_mode, enabled, runtime_label, notes)
VALUES
  ('monitoring-worker', 'monitor', 'running', 'automatic', true,
   'com.nexus.monitoring-worker',
   'Tier 1 — health alerts every 5min, Telegram on breach')
ON CONFLICT (worker_id) DO UPDATE SET
  control_mode = 'automatic', enabled = true,
  runtime_label = EXCLUDED.runtime_label, notes = EXCLUDED.notes;

-- Tier 2: Core workers (event processing + AI dispatch)
INSERT INTO public.worker_control_plane
  (worker_id, worker_type, desired_state, control_mode, enabled, runtime_label, notes)
VALUES
  ('autonomy-worker', 'worker', 'running', 'automatic', true,
   'com.nexus.autonomy-worker',
   'Tier 2 — AI agent dispatch every 30s'),
  ('email-pipeline', 'worker', 'running', 'automatic', true,
   'ai.nexus.email-pipeline',
   'Tier 2 — email → task + YouTube research pipeline every 2min'),
  ('coordination-worker', 'worker', 'running', 'automatic', true,
   'com.nexus.coordination-worker',
   'Tier 2 — task coordination and handoff')
ON CONFLICT (worker_id) DO UPDATE SET
  control_mode = 'automatic', enabled = true,
  runtime_label = EXCLUDED.runtime_label, notes = EXCLUDED.notes;

-- Tier 3: Trading (manual — live trading, human oversight required)
INSERT INTO public.worker_control_plane
  (worker_id, worker_type, desired_state, control_mode, enabled, runtime_label, notes)
VALUES
  ('signal-router', 'worker', 'running', 'automatic', true,
   'com.nexus.signal-router',
   'Tier 3 — TradingView webhook receiver'),
  ('trading-engine', 'worker', 'running', 'manual', true,
   'com.nexus.trading-engine',
   'Tier 3 — live trade execution, manual control only')
ON CONFLICT (worker_id) DO UPDATE SET
  control_mode = EXCLUDED.control_mode, enabled = true,
  runtime_label = EXCLUDED.runtime_label, notes = EXCLUDED.notes;

-- ── Update existing workers with tier notes ───────────────────────────────────
UPDATE public.worker_control_plane SET
  notes = 'Tier 0 — AI gateway, Telegram + email + API on :8642'
WHERE worker_id = 'hermes-gateway';

UPDATE public.worker_control_plane SET
  notes = 'Tier 1 — self-healer, launchd restart every 10min'
WHERE worker_id = 'ops-control-worker';

UPDATE public.worker_control_plane SET
  notes = 'Tier 2 — system_events orchestrator, KeepAlive daemon'
WHERE worker_id = 'nexus-orchestrator';

UPDATE public.worker_control_plane SET
  notes = 'Tier 2 — research job runner, KeepAlive daemon'
WHERE worker_id = 'nexus-research-worker';

UPDATE public.worker_control_plane SET
  notes = 'Tier 2 — grant scoring every 4hrs'
WHERE worker_id = 'grant-worker';

UPDATE public.worker_control_plane SET
  notes = 'Tier 2 — opportunity scoring'
WHERE worker_id = 'opportunity-worker';

UPDATE public.worker_control_plane SET
  notes = 'Tier 2 — YouTube transcript research every 2hrs'
WHERE worker_id = 'research-orchestrator-transcript';

UPDATE public.worker_control_plane SET
  notes = 'Tier 2 — grants browser research'
WHERE worker_id = 'research-orchestrator-grants-browser';
