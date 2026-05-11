/**
 * routing/capability.js — Worker capability guard.
 *
 * Checks whether at least one active worker currently supports
 * a given job type by reading worker_heartbeats.
 *
 * A worker is considered "active" if its last_heartbeat_at is
 * within the staleness window (default 90 seconds).
 */

import { db, getEnv }   from '../clients/supabase.js';
import { createLogger } from '../telemetry/logger.js';

const logger          = createLogger('capability');
const STALE_SECS      = parseInt(getEnv('WORKER_STALE_SECONDS', '90'), 10);

/**
 * Returns the list of job types supported by all currently active workers.
 * Reads supported_job_types from worker_heartbeats.metadata.
 */
export async function getActiveCapabilities() {
  const cutoff = new Date(Date.now() - STALE_SECS * 1000).toISOString();

  const { data, error } = await db
    .from('worker_heartbeats')
    .select('worker_id, worker_type, status, metadata, last_heartbeat_at')
    .gte('last_heartbeat_at', cutoff);

  if (error) {
    logger.warn('capability_lookup_failed', { error: error.message });
    return null; // null = unknown, fail open
  }

  const capabilities = new Map(); // job_type → [worker_id, ...]
  for (const w of data ?? []) {
    const supported = w.metadata?.supported_job_types ?? [];
    for (const jt of supported) {
      if (!capabilities.has(jt)) capabilities.set(jt, []);
      capabilities.get(jt).push(w.worker_id);
    }
  }

  return capabilities;
}

/**
 * Returns true if at least one active worker supports the job type.
 * Returns true (fail-open) if the capability lookup itself fails.
 */
export async function isJobTypeSupported(jobType) {
  const caps = await getActiveCapabilities();
  if (caps === null) {
    logger.warn('capability_unknown_fail_open', { job_type: jobType });
    return true; // fail open — don't block if we can't read heartbeats
  }

  const supported = caps.has(jobType);
  if (!supported) {
    logger.warn('job_type_unsupported', {
      job_type:       jobType,
      active_workers: [...new Set([...caps.values()].flat())],
      known_types:    [...caps.keys()],
    });
  }
  return supported;
}

/**
 * Guard helper — call before enqueuing a job.
 * Returns { allowed: bool, workers: string[] }
 */
export async function checkCapability(jobType) {
  const caps    = await getActiveCapabilities();
  if (caps === null) return { allowed: true, workers: [], unknown: true };
  const workers = caps.get(jobType) ?? [];
  return { allowed: workers.length > 0, workers, unknown: false };
}
