/**
 * scripts/runSweeper.js — Seed and immediately process one stale_state_sweep job.
 *
 * Usage:
 *   node scripts/runSweeper.js
 *   STALE_JOB_MINUTES=1 node scripts/runSweeper.js   # low threshold to force detections
 */

import { db }                from '../src/supabase.js';
import { config }            from '../src/config.js';
import { runStaleStateSweep } from '../src/handlers/sweeper.js';

const payload = {
  stale_job_minutes:       parseInt(process.env.STALE_JOB_MINUTES       ?? String(config.staleJobMinutes), 10),
  stale_workflow_minutes:  parseInt(process.env.STALE_WORKFLOW_MINUTES   ?? String(config.staleWorkflowMinutes), 10),
  stale_heartbeat_minutes: parseInt(process.env.STALE_HEARTBEAT_MINUTES  ?? String(config.staleHeartbeatMinutes), 10),
};

const { data: job, error: insertErr } = await db.from('job_queue').insert({
  job_type:     'stale_state_sweep',
  status:       'pending',
  payload,
  max_attempts: 1,
  available_at: new Date().toISOString(),
}).select('id').single();

if (insertErr) {
  process.stderr.write(`Insert failed: ${insertErr.message}\n`);
  process.exit(1);
}

process.stdout.write(`Job created: ${job.id}\n`);

await db.from('job_queue').update({ status: 'running', worker_id: config.workerId }).eq('id', job.id);

try {
  const result = await runStaleStateSweep(payload);
  await db.from('job_queue').update({
    status:       'completed',
    payload:      { ...payload, result },
    completed_at: new Date().toISOString(),
    worker_id:    config.workerId,
  }).eq('id', job.id);

  process.stdout.write('\n=== SWEEP RESULT ===\n');
  process.stdout.write(JSON.stringify(result, null, 2) + '\n');
  process.exit(0);
} catch (err) {
  await db.from('job_queue').update({ status: 'failed', last_error: err?.message }).eq('id', job.id);
  process.stderr.write(`Sweep failed: ${err?.message}\n`);
  process.exit(1);
}
