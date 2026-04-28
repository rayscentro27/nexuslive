/**
 * routing/enqueue.js — Safe job enqueue with capability guard.
 *
 * Before inserting into job_queue, checks that at least one active
 * worker supports the job type. Blocks + alerts if not.
 */

import { insertRow, db } from '../clients/supabase.js';
import { checkCapability } from './capability.js';
import { alertUnsupportedJobType, alertWorkflowBlocked } from '../alerts/emit.js';
import { inc }            from '../telemetry/metrics.js';
import { createLogger }   from '../telemetry/logger.js';

const logger = createLogger('enqueue');

/**
 * Enqueue a job safely.
 * Returns the created job row, or null if blocked.
 *
 * @param {object} jobRow      — full job_queue row to insert
 * @param {object} context     — { workflowId, eventId, tenantId } for alerts
 */
export async function enqueueJobSafe(jobRow, context = {}) {
  const { job_type: jobType } = jobRow;
  const { workflowId, eventId, tenantId } = context;

  const { allowed, workers, unknown } = await checkCapability(jobType);

  if (!allowed && !unknown) {
    logger.warn('job_blocked_no_worker', { job_type: jobType, workflow_id: workflowId });

    // Mark workflow as blocked
    if (workflowId) {
      await db
        .from('orchestrator_workflow_runs')
        .update({ status: 'blocked', completed_at: new Date().toISOString() })
        .eq('id', workflowId);
    }

    // Emit alerts
    await alertUnsupportedJobType({ jobType, workflowId, eventId, tenantId });

    inc('jobs_blocked');
    return null;
  }

  if (unknown) {
    logger.warn('capability_unknown_proceeding', { job_type: jobType });
  } else {
    logger.debug('capability_ok', { job_type: jobType, workers });
  }

  const job = await insertRow('job_queue', jobRow);
  inc('jobs_enqueued');
  return job;
}
