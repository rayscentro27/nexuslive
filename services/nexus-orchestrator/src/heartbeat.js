/**
 * heartbeat.js — Writes a periodic heartbeat to worker_heartbeats.
 * Allows the monitoring dashboard to detect if the orchestrator dies.
 */

import { upsertRow }    from './clients/supabase.js';
import { getEnv, isTransientSupabaseError } from './clients/supabase.js';
import { createLogger } from './telemetry/logger.js';
import { snapshot }     from './telemetry/metrics.js';

const logger    = createLogger('heartbeat');
const WORKER_ID = getEnv('WORKER_ID', 'nexus-orchestrator-1');
const INTERVAL  = parseInt(getEnv('HEARTBEAT_INTERVAL_MS', '30000'), 10);

let timer = null;

async function beat() {
  try {
    await upsertRow(
      'worker_heartbeats',
      {
        worker_id:         WORKER_ID,
        worker_type:       'orchestrator',
        status:            'running',
        last_heartbeat_at: new Date().toISOString(),
        last_seen_at:      new Date().toISOString(),
        pid:               process.pid,
        host:              process.env.HOSTNAME ?? 'mac-mini',
        metadata: {
          version:          '1.0.0',
          node:             process.version,
          uptime_s:         Math.floor(process.uptime()),
          memory_usage_mb:  Math.round(process.memoryUsage().heapUsed / 1024 / 1024),
          counters:         snapshot(),
        },
      },
      'worker_id'
    );
  } catch (e) {
    const message = e?.message;
    if (isTransientSupabaseError(e)) {
      logger.warn('heartbeat_degraded', { error: message });
      return;
    }
    logger.warn('heartbeat_failed', { error: message });
  }
}

export function startHeartbeat() {
  beat(); // immediate first beat
  timer = setInterval(beat, INTERVAL);
  logger.info('started', { interval_ms: INTERVAL, worker_id: WORKER_ID });
}

export function stopHeartbeat() {
  if (timer) clearInterval(timer);
}
