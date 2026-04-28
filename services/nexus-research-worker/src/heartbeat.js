/**
 * heartbeat.js — Worker heartbeat to worker_heartbeats table.
 */

import { isTransientSupabaseError, upsertRow } from './supabase.js';
import { config }       from './config.js';
import { createLogger } from './logger.js';

const logger = createLogger('heartbeat');
let timer    = null;

async function beat() {
  try {
    await upsertRow('worker_heartbeats', {
      worker_id:         config.workerId,
      worker_type:       'research_worker',
      status:            'running',
      last_heartbeat_at: new Date().toISOString(),
      pid:               process.pid,
      host:              process.env.HOSTNAME ?? 'mac-mini',
      metadata: {
        version:             '1.0.0',
        node:                process.version,
        uptime_s:            Math.floor(process.uptime()),
        memory_usage_mb:     Math.round(process.memoryUsage().heapUsed / 1024 / 1024),
        hermes_enabled:      config.enableHermes,
        supported_job_types: ['research_collect', 'daily_system_digest', 'stale_state_sweep'],
      },
    }, 'worker_id');
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
  beat();
  timer = setInterval(beat, config.heartbeatIntervalMs);
  logger.info('started', { interval_ms: config.heartbeatIntervalMs });
}

export function stopHeartbeat() {
  if (timer) clearInterval(timer);
}
