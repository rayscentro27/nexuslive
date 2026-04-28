/**
 * handlers/signals.js — signal_detected event handler.
 * Fast path: AI enrichment → risk gate → enqueue for execution.
 */

import { insertRow }    from '../clients/supabase.js';
import { complete }     from '../clients/hermes.js';
import { notify }       from '../clients/telegram.js';
import { enqueueJobSafe } from '../routing/enqueue.js';
import { inc }          from '../telemetry/metrics.js';
import { createLogger } from '../telemetry/logger.js';
import { isDuplicate }  from '../guards/dedupe.js';
import { uuidOrNull }   from '../utils/uuid.js';

const logger = createLogger('handler:signals');

export async function handle(event) {
  const { id: eventId, payload = {} } = event;
  const signalId  = payload.signal_id ?? eventId;
  const symbol    = payload.symbol ?? 'UNKNOWN';
  const dedupeKey = `signal_enrich:${signalId}`;

  if (await isDuplicate(dedupeKey)) {
    logger.info('skipped_duplicate', { event_id: eventId, signal_id: signalId });
    return;
  }

  // AI enrichment — quick risk read
  let enrichment = { risk_level: 'unknown', notes: 'AI unavailable', proceed: true };
  try {
    const prompt =
      `Trading signal detected:\n` +
      `${JSON.stringify(payload, null, 2).slice(0, 800)}\n\n` +
      `Respond with JSON only: {"risk_level": "low|medium|high", "notes": "string", "proceed": bool}`;

    const raw = await complete(
      prompt,
      'You are a Nexus risk analyst. Evaluate signal risk briefly. Return JSON only.',
      200
    );

    const match = raw.match(/\{[\s\S]*\}/);
    if (match) enrichment = JSON.parse(match[0]);
  } catch (e) {
    logger.warn('ai_enrichment_failed', { error: e?.message });
    // fail open — let signal through
  }

  const workflow = await insertRow('orchestrator_workflow_runs', {
    workflow_type: 'signal_processing',
    status:        'running',
    trigger_event: eventId,
    tenant_id:     uuidOrNull(payload.tenant_id),
    metadata:      { signal_id: signalId, symbol, enrichment },
    started_at:    new Date().toISOString(),
  });

  inc('workflows_created');

  if (enrichment.risk_level === 'high' && !enrichment.proceed) {
    // Block — notify and mark workflow halted
    await notify(
      `*Signal Blocked*\n` +
      `Symbol: \`${symbol}\`\n` +
      `Risk: ${enrichment.risk_level}\n` +
      `Notes: ${enrichment.notes}`
    );

    logger.warn('signal_blocked', { signal_id: signalId, risk: enrichment.risk_level });
    return;
  }

  // Enqueue signal for execution worker (capability-guarded)
  const tenantId = uuidOrNull(payload.tenant_id);
  await enqueueJobSafe({
    job_type:     'signal_execute',
    tenant_id:    tenantId,
    status:       'pending',
    dedupe_key:   dedupeKey,
    payload:      {
      workflow_id: workflow.id,
      signal_id:   signalId,
      symbol,
      enrichment,
      signal:      payload,
    },
    max_attempts: 2, // signals are time-sensitive, fewer retries
    available_at: new Date().toISOString(),
  }, { workflowId: workflow.id, eventId, tenantId });
  logger.info('signal_enqueued', {
    workflow_id: workflow.id,
    signal_id:   signalId,
    symbol,
    risk:        enrichment.risk_level,
  });
}
