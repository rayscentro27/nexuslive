/**
 * scripts/runDigest.js — Seed and immediately process one daily_system_digest job.
 * Usage: node scripts/runDigest.js
 */

import { db }                   from '../src/supabase.js';
import { config }               from '../src/config.js';
import { runDailySystemDigest } from '../src/handlers/digest.js';

// Insert job
const { data: job, error: insertErr } = await db.from('job_queue').insert({
  job_type:     'daily_system_digest',
  status:       'pending',
  payload:      { window_hours: config.digestWindowHours },
  max_attempts: 1,
  available_at: new Date().toISOString(),
}).select('id, payload').single();

if (insertErr) {
  process.stderr.write(`Insert failed: ${insertErr.message}\n`);
  process.exit(1);
}

process.stdout.write(`Job created: ${job.id}\n`);

// Claim + run
await db.from('job_queue').update({ status: 'running', worker_id: config.workerId }).eq('id', job.id);

try {
  const result = await runDailySystemDigest(job.payload);
  await db.from('job_queue').update({
    status:       'completed',
    payload:      { ...job.payload, result },
    completed_at: new Date().toISOString(),
    worker_id:    config.workerId,
  }).eq('id', job.id);

  process.stdout.write('\n=== DIGEST RESULT ===\n');
  process.stdout.write(JSON.stringify(result, null, 2) + '\n');
  process.exit(0);
} catch (err) {
  await db.from('job_queue').update({ status: 'failed', last_error: err?.message }).eq('id', job.id);
  process.stderr.write(`Digest failed: ${err?.message}\n`);
  process.exit(1);
}
