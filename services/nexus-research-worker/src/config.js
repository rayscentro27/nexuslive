/**
 * config.js — All env-based config in one place.
 * Reads from ~/nexus-ai/.env (same pattern as orchestrator).
 */

import { readFileSync } from 'fs';
import { resolve }      from 'path';

function loadEnv() {
  try {
    const envPath = resolve(process.env.HOME ?? '/Users/raymonddavis', 'nexus-ai/.env');
    const lines = readFileSync(envPath, 'utf-8').split('\n');
    const env = {};
    for (const line of lines) {
      if (!line || line.startsWith('#')) continue;
      const [key, ...rest] = line.split('=');
      if (key) env[key.trim()] = rest.join('=').trim();
    }
    return env;
  } catch {
    return {};
  }
}

const env = { ...loadEnv(), ...process.env };

export function getEnv(key, def = null) {
  return env[key] ?? def;
}

export const config = {
  supabaseUrl:          getEnv('SUPABASE_URL'),
  supabaseKey:          getEnv('SUPABASE_KEY') || getEnv('SUPABASE_SERVICE_ROLE_KEY'),
  workerId:             getEnv('WORKER_ID', 'nexus-research-worker'),
  pollIntervalMs:       parseInt(getEnv('POLL_INTERVAL_MS', '5000'), 10),
  leaseSeconds:         parseInt(getEnv('JOB_LEASE_SECONDS', '120'), 10),
  heartbeatIntervalMs:  parseInt(getEnv('HEARTBEAT_INTERVAL_MS', '30000'), 10),
  maxAttempts:          parseInt(getEnv('MAX_JOB_ATTEMPTS', '3'), 10),
  enableHermes:         getEnv('ENABLE_HERMES_REFINEMENT', 'false') === 'true',
  hermesUrl:          getEnv('HERMES_GATEWAY_URL', 'http://localhost:8642'),
  hermesToken:        getEnv('HERMES_GATEWAY_TOKEN', ''),
  hermesModel:        getEnv('HERMES_MODEL', 'hermes'),

  // Digest
  digestWindowHours:           parseInt(getEnv('DIGEST_WINDOW_HOURS', '24'), 10),
  enableHermesDigestSynthesis: getEnv('ENABLE_HERMES_DIGEST_SYNTHESIS', 'false') === 'true',
  enableTelegramDigests:       getEnv('ENABLE_TELEGRAM_DIGESTS', 'false') === 'true',

  // Sweeper thresholds
  staleJobMinutes:       parseInt(getEnv('STALE_JOB_MINUTES', '15'), 10),
  staleWorkflowMinutes:  parseInt(getEnv('STALE_WORKFLOW_MINUTES', '30'), 10),
  staleHeartbeatMinutes: parseInt(getEnv('STALE_HEARTBEAT_MINUTES', '5'), 10),
  autoRequeueStaleJobs:  getEnv('AUTO_REQUEUE_STALE_JOBS', 'true') === 'true',
  staleJobRecoveryDelaySeconds: parseInt(getEnv('STALE_JOB_RECOVERY_DELAY_SECONDS', '60'), 10),
  enableTelegramSweepAlerts: getEnv('ENABLE_TELEGRAM_SWEEP_ALERTS', 'false') === 'true',

  // Telegram (shared by digest + sweeper)
  telegramToken:  getEnv('TELEGRAM_BOT_TOKEN', ''),
  telegramChatId: getEnv('TELEGRAM_CHAT_ID', ''),
};

if (!config.supabaseUrl || !config.supabaseKey) {
  process.stderr.write('FATAL: SUPABASE_URL and SUPABASE_KEY are required\n');
  process.exit(1);
}
