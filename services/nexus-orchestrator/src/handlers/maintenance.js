/**
 * handlers/maintenance.js — Handles maintenance trigger events.
 *
 * Supported event_types:
 *   daily_system_digest_due   → enqueues daily_system_digest job
 *   stale_state_sweep_due     → enqueues stale_state_sweep job
 *
 * These are fire-and-forget maintenance jobs: no workflow_run is created,
 * no client/tenant context is needed. Jobs are inserted directly.
 */

import { insertRow }  from '../clients/supabase.js';
import { inc }        from '../telemetry/metrics.js';
import { createLogger } from '../telemetry/logger.js';
import { isDuplicate }  from '../guards/dedupe.js';

const logger = createLogger('handler:maintenance');

const JOB_MAP = {
  daily_system_digest_due: 'daily_system_digest',
  stale_state_sweep_due:   'stale_state_sweep',
};

export async function handle(event) {
  const { id: eventId, event_type, payload = {} } = event;
  const jobType    = JOB_MAP[event_type];
  const dedupeKey  = `${jobType}:singleton`;

  if (await isDuplicate(dedupeKey)) {
    logger.info('skipped_duplicate', { event_type, event_id: eventId, job_type: jobType });
    return;
  }

  const job = await insertRow('job_queue', {
    job_type:     jobType,
    status:       'pending',
    dedupe_key:   dedupeKey,
    payload:      { triggered_by: eventId, ...payload },
    max_attempts: 2,
    available_at: new Date().toISOString(),
  });

  inc('jobs_enqueued');
  logger.info('maintenance_job_enqueued', { job_type: jobType, job_id: job.id, event_id: eventId });
}
