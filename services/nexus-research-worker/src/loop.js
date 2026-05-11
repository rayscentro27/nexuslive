/**
 * loop.js — Main job poll loop.
 * Fetches one pending research_collect job, claims it atomically,
 * executes the handler, writes the result, marks complete or failed.
 */

import { db, isTransientSupabaseError } from './supabase.js';
import { config }                from './config.js';
import { createLogger }          from './logger.js';
import { runResearchCollect }    from './handler.js';
import { refineWithHermes }      from './hermes.js';
import { runDailySystemDigest }  from './handlers/digest.js';
import { runStaleStateSweep }    from './handlers/sweeper.js';

const logger    = createLogger('loop');
const JOB_TYPES = ['research_collect', 'daily_system_digest', 'stale_state_sweep'];

// Dispatch table: job_type → handler function
const HANDLERS = {
  research_collect:    async (payload) => {
    const base    = await runResearchCollect(payload);
    const refined = await refineWithHermes(base);
    return refined
      ? { base_result: base, hermes_result: refined, refined: true }
      : { ...base, refined: false };
  },
  daily_system_digest: runDailySystemDigest,
  stale_state_sweep:   runStaleStateSweep,
};

// ── Claim ──────────────────────────────────────────────────────────────────

async function fetchAndClaim() {
  const now        = new Date();
  const leaseUntil = new Date(now.getTime() + config.leaseSeconds * 1000).toISOString();
  const nowIso     = now.toISOString();

  // Find one eligible job across all supported types
  const { data: rows, error: fetchErr } = await db
    .from('job_queue')
    .select('id, job_type, payload, attempt_count, max_attempts')
    .in('job_type', JOB_TYPES)
    .eq('status', 'pending')
    .or(`available_at.is.null,available_at.lte.${nowIso}`)
    .order('created_at', { ascending: true })
    .limit(1);

  if (fetchErr) {
    if (isTransientSupabaseError(fetchErr)) {
      logger.warn('fetch_degraded', { error: fetchErr.message });
    } else {
      logger.error('fetch_failed', { error: fetchErr.message });
    }
    return null;
  }
  if (!rows || rows.length === 0) return null;

  const job = rows[0];

  // Atomic claim — only succeeds if still pending (prevents double-claim)
  const { data: claimed, error: claimErr } = await db
    .from('job_queue')
    .update({
      status:           'claimed',
      worker_id:        config.workerId,
      lease_expires_at: leaseUntil,
      leased_at:        nowIso,
    })
    .eq('id', job.id)
    .eq('status', 'pending')
    .select('id');

  if (claimErr || !claimed || claimed.length === 0) {
    logger.debug('claim_lost', { job_id: job.id });
    return null;
  }

  logger.info('job_claimed', { job_id: job.id, lease_until: leaseUntil });
  return job;
}

// ── Execute ────────────────────────────────────────────────────────────────

async function executeJob(job) {
  const { id: jobId, payload = {}, attempt_count = 0, max_attempts = config.maxAttempts } = job;

  // Mark running
  await db.from('job_queue').update({ status: 'running' }).eq('id', jobId);
  logger.info('job_running', { job_id: jobId, attempt: attempt_count + 1 });

  try {
    const handler = HANDLERS[job.job_type];
    if (!handler) throw new Error(`No handler for job_type: ${job.job_type}`);

    const finalResult = await handler(payload);

    // Mark completed — store result inside payload since there's no result column
    await db.from('job_queue').update({
      status:       'completed',
      payload:      { ...payload, result: finalResult },
      completed_at: new Date().toISOString(),
      worker_id:    config.workerId,
    }).eq('id', jobId);

    // Update workflow run if present
    if (payload.workflow_id) {
      await db.from('orchestrator_workflow_runs')
        .update({ status: 'completed', completed_at: new Date().toISOString() })
        .eq('id', payload.workflow_id);
    }

    logger.info('job_completed', { job_id: jobId, refined: !!finalResult?.refined });

  } catch (err) {
    const nextAttempt = attempt_count + 1;
    const terminal    = nextAttempt >= max_attempts;

    logger.error('job_failed', {
      job_id:   jobId,
      attempt:  nextAttempt,
      terminal,
      error:    err?.message,
    });

    await db.from('job_queue').update({
      status:        terminal ? 'failed' : 'pending',
      attempt_count: nextAttempt,
      last_error:    String(err?.message ?? err),
      worker_id:     terminal ? config.workerId : null,
      lease_expires_at: null,
    }).eq('id', jobId);
  }
}

// ── Tick ───────────────────────────────────────────────────────────────────

async function tick() {
  const job = await fetchAndClaim();
  if (!job) return;
  await executeJob(job);
}

// ── Loop ───────────────────────────────────────────────────────────────────

let running = false;
let timer   = null;

export function startLoop() {
  if (running) return;
  running = true;
  logger.info('started', { poll_interval_ms: config.pollIntervalMs, job_types: JOB_TYPES });

  const schedule = async () => {
    if (!running) return;
    try {
      await tick();
    } catch (e) {
      logger.error('tick_uncaught', { error: e?.message });
    }
    if (running) timer = setTimeout(schedule, config.pollIntervalMs);
  };

  schedule();
}

export function stopLoop() {
  running = false;
  if (timer) clearTimeout(timer);
  logger.info('stopped');
}

/**
 * Run exactly one job then resolve. Used by scripts/runOnce.js.
 */
export async function runOnce() {
  logger.info('run_once_start');
  const job = await fetchAndClaim();
  if (!job) {
    logger.info('run_once_no_jobs', { message: 'No pending jobs found', job_types: JOB_TYPES });
    return false;
  }
  await executeJob(job);
  return true;
}
