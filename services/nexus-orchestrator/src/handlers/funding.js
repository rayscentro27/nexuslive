/**
 * handlers/funding.js — funding_profile_updated event handler.
 * Creates a workflow run and enqueues a funding_next_step job
 * for the mac-mini-worker to evaluate readiness and produce next actions.
 */

import { insertRow }    from '../clients/supabase.js';
import { enqueueJobSafe } from '../routing/enqueue.js';
import { inc }          from '../telemetry/metrics.js';
import { createLogger } from '../telemetry/logger.js';
import { isDuplicate }  from '../guards/dedupe.js';
import { uuidOrNull }   from '../utils/uuid.js';

const logger = createLogger('handler:funding');

export async function handle(event) {
  const { id: eventId, payload = {} } = event;
  const tenantId  = uuidOrNull(payload.tenant_id);
  const clientId  = payload.client_id ?? null;
  const dedupeKey = `funding_next_step:${tenantId ?? eventId}:${payload.profile_version ?? eventId}`;

  if (await isDuplicate(dedupeKey)) {
    logger.info('skipped_duplicate', { event_id: eventId });
    return;
  }

  const workflow = await insertRow('orchestrator_workflow_runs', {
    workflow_type: 'funding_review',
    status:        'running',
    trigger_event: eventId,
    tenant_id:     tenantId,
    metadata:      { client_id: clientId, ...payload },
    started_at:    new Date().toISOString(),
  });

  inc('workflows_created');

  const job = await enqueueJobSafe({
    job_type:     'funding_next_step',
    tenant_id:    tenantId,
    status:       'pending',
    dedupe_key:   dedupeKey,
    payload:      { workflow_id: workflow.id, tenant_id: tenantId, client_id: clientId, ...payload },
    max_attempts: 3,
    available_at: new Date().toISOString(),
  }, { workflowId: workflow.id, eventId, tenantId });

  if (job) logger.info('funding_job_enqueued', { workflow_id: workflow.id, event_id: eventId, tenant_id: tenantId });
}
