/**
 * handlers/trading.js — strategy_submitted event handler.
 * Routes new strategy submissions through AI review before
 * they reach the strategy library.
 */

import { insertRow }    from '../clients/supabase.js';
import { complete }     from '../clients/hermes.js';
import { notify }       from '../clients/telegram.js';
import { enqueueJobSafe } from '../routing/enqueue.js';
import { inc }          from '../telemetry/metrics.js';
import { createLogger } from '../telemetry/logger.js';
import { isDuplicate }  from '../guards/dedupe.js';
import { uuidOrNull }   from '../utils/uuid.js';

const logger = createLogger('handler:trading');

export async function handle(event) {
  const { id: eventId, payload = {} } = event;
  const strategyId = payload.strategy_id ?? eventId;
  const dedupeKey  = `strategy_review:${strategyId}`;

  if (await isDuplicate(dedupeKey)) {
    logger.info('skipped_duplicate', { event_id: eventId });
    return;
  }

  // AI strategy review via Hermes
  let review = { approved: false, confidence: 0, reason: 'AI review unavailable' };
  try {
    const prompt =
      `Review this trading strategy submission:\n` +
      `${JSON.stringify(payload, null, 2).slice(0, 1200)}\n\n` +
      `Respond with JSON only: {"approved": bool, "confidence": 0-100, "reason": "string", "risk_notes": "string"}`;

    const raw = await complete(prompt, 'You are a Nexus trading strategy reviewer. Return JSON only.', 300);

    // Extract JSON from response
    const match = raw.match(/\{[\s\S]*\}/);
    if (match) review = JSON.parse(match[0]);
  } catch (e) {
    logger.warn('ai_review_failed', { error: e?.message });
  }

  const workflow = await insertRow('orchestrator_workflow_runs', {
    workflow_type: 'strategy_review',
    status:        'running',
    trigger_event: eventId,
    tenant_id:     uuidOrNull(payload.tenant_id),
    metadata:      { strategy_id: strategyId, review },
    started_at:    new Date().toISOString(),
  });

  inc('workflows_created');

  // Enqueue for deeper backtesting regardless of AI decision (capability-guarded)
  const tenantId = uuidOrNull(payload.tenant_id);
  await enqueueJobSafe({
    job_type:     'strategy_backtest',
    tenant_id:    tenantId,
    status:       'pending',
    dedupe_key:   dedupeKey,
    payload:      {
      workflow_id:  workflow.id,
      strategy_id:  strategyId,
      ai_review:    review,
      strategy:     payload,
    },
    max_attempts: 3,
    available_at: new Date().toISOString(),
  }, { workflowId: workflow.id, eventId, tenantId });

  // Alert if AI flagged issues
  if (!review.approved && review.confidence > 60) {
    await notify(
      `*Strategy Review Alert*\n` +
      `Strategy \`${strategyId}\` flagged by AI.\n` +
      `Confidence: ${review.confidence}%\n` +
      `Reason: ${review.reason}`
    );
  }

  logger.info('strategy_job_enqueued', {
    workflow_id:  workflow.id,
    strategy_id:  strategyId,
    ai_approved:  review.approved,
    confidence:   review.confidence,
  });
}
