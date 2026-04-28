/**
 * events/intake.js — Poll system_events for claimable work.
 * Returns pending events ordered by created_at, up to BATCH_SIZE.
 */

import { db }           from '../clients/supabase.js';
import { getEnv, isTransientSupabaseError } from '../clients/supabase.js';
import { inc }          from '../telemetry/metrics.js';
import { createLogger } from '../telemetry/logger.js';

const logger     = createLogger('intake');
const BATCH_SIZE = parseInt(getEnv('POLL_BATCH_SIZE', '10'), 10);

/**
 * Fetch up to BATCH_SIZE unclaimed pending events.
 * Excludes rows that are already claimed and whose lease hasn't expired.
 */
export async function fetchPendingEvents() {
  const now = new Date().toISOString();

  const { data, error } = await db
    .from('system_events')
    .select('id, event_type, payload, status, attempt_count, created_at, lease_expires_at')
    .eq('status', 'pending')
    .or(`lease_expires_at.is.null,lease_expires_at.lt.${now}`)
    .order('created_at', { ascending: true })
    .limit(BATCH_SIZE);

  if (error) {
    if (isTransientSupabaseError(error)) {
      logger.warn('poll_degraded', { error: error.message });
    } else {
      logger.error('poll_failed', { error: error.message });
    }
    return [];
  }

  const events = data ?? [];
  if (events.length > 0) {
    inc('events_polled', events.length);
    logger.debug('polled', { count: events.length });
  }

  return events;
}
