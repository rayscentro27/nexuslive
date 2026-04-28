/**
 * guards/retries.js — Retry cap + system_alerts escalation.
 */

import { db, insertRow, getEnv } from '../clients/supabase.js';
import { notify }                from '../clients/telegram.js';
import { inc }                   from '../telemetry/metrics.js';
import { createLogger }          from '../telemetry/logger.js';

const logger      = createLogger('retries');
const MAX_ATTEMPTS = parseInt(getEnv('MAX_EVENT_ATTEMPTS', '3'), 10);

/**
 * Record an error on a system_event row and escalate to
 * system_errors alert if attempt cap is reached.
 */
export async function recordFailure(eventId, eventType, error, attemptCount) {
  logger.warn('event_failed', { event_id: eventId, event_type: eventType, attempt: attemptCount, error: error?.message });

  const nextAttempt = (attemptCount ?? 0) + 1;

  await db.from('system_events').update({
    status:        nextAttempt >= MAX_ATTEMPTS ? 'failed' : 'pending',
    attempt_count: nextAttempt,
    last_error:    String(error?.message ?? error),
    claimed_by:    null,
    claimed_at:    null,
  }).eq('id', eventId);

  if (nextAttempt >= MAX_ATTEMPTS) {
    inc('alerts_emitted');
    try {
      await insertRow('system_errors', {
        source:        'nexus-orchestrator',
        service:       'orchestrator',
        component:     eventType,
        severity:      'high',
        error_code:    'MAX_RETRIES_EXCEEDED',
        error_message: `Event ${eventId} (${eventType}) failed ${MAX_ATTEMPTS} times: ${error?.message}`,
        metadata:      { event_id: eventId, event_type: eventType, attempts: nextAttempt },
      });
    } catch (e) {
      logger.error('alert_write_failed', { error: e?.message });
    }

    await notify(
      `*Nexus Orchestrator Alert*\n` +
      `Event type \`${eventType}\` failed ${MAX_ATTEMPTS} times.\n` +
      `Event ID: \`${eventId}\`\n` +
      `Error: ${error?.message ?? error}`
    );
  }
}
