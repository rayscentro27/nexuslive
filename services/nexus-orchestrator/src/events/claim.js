/**
 * events/claim.js — Atomic lease/claim on a system_event row.
 * Uses optimistic concurrency: update WHERE status='pending' AND
 * (lease_expires_at IS NULL OR lease_expires_at < now).
 * Returns true if this worker won the claim.
 */

import { db }           from '../clients/supabase.js';
import { getEnv, isTransientSupabaseError } from '../clients/supabase.js';
import { inc }          from '../telemetry/metrics.js';
import { createLogger } from '../telemetry/logger.js';

const logger       = createLogger('claim');
const WORKER_ID    = getEnv('WORKER_ID', 'nexus-orchestrator-1');
const LEASE_SECS   = parseInt(getEnv('EVENT_LEASE_SECONDS', '120'), 10);

/**
 * Attempt to atomically claim an event.
 * Returns true if this instance claimed it; false if already taken.
 */
export async function claimEvent(eventId) {
  const now        = new Date();
  const leaseUntil = new Date(now.getTime() + LEASE_SECS * 1000).toISOString();
  const nowIso     = now.toISOString();

  const { data, error } = await db
    .from('system_events')
    .update({
      status:          'claimed',
      claimed_by:      WORKER_ID,
      claimed_at:      nowIso,
      lease_expires_at: leaseUntil,
    })
    .eq('id', eventId)
    .eq('status', 'pending')
    .select('id');

  if (error) {
    logger.warn(isTransientSupabaseError(error) ? 'claim_degraded' : 'claim_error', {
      event_id: eventId,
      error: error.message,
    });
    return false;
  }

  const claimed = (data?.length ?? 0) > 0;
  if (claimed) {
    inc('events_claimed');
    logger.info('claimed', { event_id: eventId, lease_until: leaseUntil });
  } else {
    logger.debug('claim_lost', { event_id: eventId });
  }
  return claimed;
}

/**
 * Mark a claimed event as completed.
 */
export async function completeEvent(eventId) {
  const { error } = await db
    .from('system_events')
    .update({
      status:          'completed',
      claimed_by:      null,
      claimed_at:      null,
      lease_expires_at: null,
      completed_at:    new Date().toISOString(),
    })
    .eq('id', eventId);

  if (error) {
    logger[isTransientSupabaseError(error) ? 'warn' : 'error'](
      isTransientSupabaseError(error) ? 'complete_degraded' : 'complete_failed',
      { event_id: eventId, error: error.message },
    );
  } else {
    logger.info('completed', { event_id: eventId });
  }
}
