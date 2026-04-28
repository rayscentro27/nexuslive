/**
 * handlers/research.js — research_refresh_due event handler.
 * Creates a workflow_run and enqueues a research_collect job.
 */

import { insertRow, upsertRow } from '../clients/supabase.js';
import { enqueueJobSafe }       from '../routing/enqueue.js';
import { inc }                  from '../telemetry/metrics.js';
import { createLogger }         from '../telemetry/logger.js';
import { isDuplicate }          from '../guards/dedupe.js';
import { uuidOrNull }           from '../utils/uuid.js';

const logger = createLogger('handler:research');

export async function handle(event) {
  const { id: eventId, payload = {} } = event;
  const tenantId  = uuidOrNull(payload.tenant_id);
  const dedupeKey = `research_collect:${tenantId}`;

  if (await isDuplicate(dedupeKey)) {
    logger.info('skipped_duplicate', { event_id: eventId, dedupe_key: dedupeKey });
    return;
  }

  // Create workflow instance
  const workflow = await insertRow('orchestrator_workflow_runs', {
    workflow_type: 'research_refresh',
    status:        'running',
    trigger_event: eventId,
    tenant_id:     tenantId,
    metadata:      payload,
    started_at:    new Date().toISOString(),
  });

  inc('workflows_created');
  logger.info('workflow_created', { workflow_id: workflow.id, event_id: eventId });

  // Enqueue job for mac-mini-worker (capability-guarded)
  const job = await enqueueJobSafe({
    job_type:      'research_collect',
    tenant_id:     tenantId,
    status:        'pending',
    dedupe_key:    dedupeKey,
    payload:       {
      workflow_id:  workflow.id,
      channels:     payload.channels ?? [],
      max_videos:   payload.max_videos ?? 1,
    },
    max_attempts:  3,
    available_at:  new Date().toISOString(),
  }, { workflowId: workflow.id, eventId, tenantId });

  if (job) logger.info('job_enqueued', { job_type: 'research_collect', event_id: eventId });
}
