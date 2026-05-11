/**
 * handlers/credit.js — credit_report_uploaded event handler.
 * Triggers credit analysis workflow and enqueues parsing job.
 */

import { insertRow }    from '../clients/supabase.js';
import { complete }     from '../clients/hermes.js';
import { enqueueJobSafe } from '../routing/enqueue.js';
import { inc }          from '../telemetry/metrics.js';
import { createLogger } from '../telemetry/logger.js';
import { isDuplicate }  from '../guards/dedupe.js';
import { uuidOrNull }   from '../utils/uuid.js';

const logger = createLogger('handler:credit');

export async function handle(event) {
  const { id: eventId, payload = {} } = event;
  const tenantId  = uuidOrNull(payload.tenant_id);
  const reportId  = payload.report_id ?? eventId;
  const dedupeKey = `credit_analyze_report:${tenantId}:${reportId}`;

  if (await isDuplicate(dedupeKey)) {
    logger.info('skipped_duplicate', { event_id: eventId });
    return;
  }

  // AI pre-screen for critical derogatory markers
  let aiFlags = null;
  try {
    const prompt =
      `Credit report uploaded for tenant ${tenantId}. ` +
      `Report metadata: ${JSON.stringify(payload).slice(0, 600)}. ` +
      `List any critical derogatory items or score concerns in 2 sentences max.`;
    aiFlags = await complete(prompt, 'You are a Nexus credit analyst. Be direct and brief.', 150);
  } catch (e) {
    logger.warn('ai_screen_failed', { error: e?.message });
  }

  const workflow = await insertRow('orchestrator_workflow_runs', {
    workflow_type: 'credit_analysis',
    status:        'running',
    trigger_event: eventId,
    tenant_id:     tenantId,
    metadata:      { report_id: reportId, ai_flags: aiFlags, ...payload },
    started_at:    new Date().toISOString(),
  });

  inc('workflows_created');

  const job = await enqueueJobSafe({
    job_type:     'credit_analyze_report',
    tenant_id:    tenantId,
    status:       'pending',
    dedupe_key:   dedupeKey,
    payload:      { workflow_id: workflow.id, tenant_id: tenantId, client_id: payload.client_id ?? null, report_id: reportId, ai_flags: aiFlags, ...payload },
    max_attempts: 3,
    available_at: new Date().toISOString(),
  }, { workflowId: workflow.id, eventId, tenantId });

  if (job) logger.info('credit_analyze_report_enqueued', { workflow_id: workflow.id, event_id: eventId });
}
