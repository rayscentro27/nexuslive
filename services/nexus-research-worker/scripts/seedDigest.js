/**
 * scripts/seedDigest.js — Seed a daily_system_digest job directly into job_queue.
 *
 * Usage:
 *   node scripts/seedDigest.js
 *   DIGEST_WINDOW_HOURS=12 node scripts/seedDigest.js
 */

import { db }     from '../src/supabase.js';
import { config } from '../src/config.js';

const windowHours = parseInt(process.env.DIGEST_WINDOW_HOURS ?? String(config.digestWindowHours), 10);

const { data, error } = await db.from('job_queue').insert({
  job_type:     'daily_system_digest',
  status:       'pending',
  payload:      { window_hours: windowHours, seeded_at: new Date().toISOString() },
  max_attempts: 2,
  available_at: new Date().toISOString(),
}).select('id').single();

if (error) {
  process.stderr.write(`ERROR: ${error.message}\n`);
  process.exit(1);
}

process.stdout.write(`Seeded daily_system_digest job: ${data.id} (window: ${windowHours}h)\n`);
process.exit(0);
