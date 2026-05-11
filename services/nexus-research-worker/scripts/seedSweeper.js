/**
 * scripts/seedSweeper.js — Seed a stale_state_sweep job directly into job_queue.
 *
 * Usage:
 *   node scripts/seedSweeper.js
 *   STALE_JOB_MINUTES=5 node scripts/seedSweeper.js    # lower threshold for quick test
 */

import { db }     from '../src/supabase.js';
import { config } from '../src/config.js';

const { data, error } = await db.from('job_queue').insert({
  job_type:     'stale_state_sweep',
  status:       'pending',
  payload: {
    stale_job_minutes:       parseInt(process.env.STALE_JOB_MINUTES       ?? String(config.staleJobMinutes), 10),
    stale_workflow_minutes:  parseInt(process.env.STALE_WORKFLOW_MINUTES   ?? String(config.staleWorkflowMinutes), 10),
    stale_heartbeat_minutes: parseInt(process.env.STALE_HEARTBEAT_MINUTES  ?? String(config.staleHeartbeatMinutes), 10),
    seeded_at:               new Date().toISOString(),
  },
  max_attempts: 2,
  available_at: new Date().toISOString(),
}).select('id').single();

if (error) {
  process.stderr.write(`ERROR: ${error.message}\n`);
  process.exit(1);
}

process.stdout.write(`Seeded stale_state_sweep job: ${data.id}\n`);
process.exit(0);
