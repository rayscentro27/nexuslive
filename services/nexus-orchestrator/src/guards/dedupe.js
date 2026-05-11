/**
 * guards/dedupe.js — Idempotency key check against job_queue.
 * Prevents duplicate jobs for the same event/workflow.
 */

import { db } from '../clients/supabase.js';

/**
 * Returns true if a job with this dedupe_key already exists
 * in a non-terminal state (pending/claimed/running).
 */
export async function isDuplicate(dedupeKey) {
  const { data, error } = await db
    .from('job_queue')
    .select('id')
    .eq('dedupe_key', dedupeKey)
    .in('status', ['pending', 'claimed', 'running'])
    .limit(1);

  if (error) return false; // fail open
  return (data?.length ?? 0) > 0;
}
