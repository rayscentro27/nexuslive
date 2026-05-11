/**
 * index.js — Nexus Orchestrator entry point.
 * Validates config, starts heartbeat, starts poll loop.
 */

import { getEnv }        from './clients/supabase.js';
import { startHeartbeat, stopHeartbeat } from './heartbeat.js';
import { startLoop, stopLoop }           from './loop.js';
import { startMetricsReporter }          from './telemetry/metrics.js';
import { createLogger }                  from './telemetry/logger.js';
import { notify }                        from './clients/telegram.js';

const logger = createLogger('main');

// ── Config validation ──────────────────────────────────────────────────────

const REQUIRED_VARS = ['SUPABASE_URL', 'SUPABASE_KEY'];

function validateConfig() {
  const missing = REQUIRED_VARS.filter((k) => !getEnv(k));
  if (missing.length > 0) {
    process.stderr.write(`FATAL: Missing required env vars: ${missing.join(', ')}\n`);
    process.exit(1);
  }
}

// ── Graceful shutdown ──────────────────────────────────────────────────────

async function shutdown(signal) {
  logger.info('shutdown', { signal });
  stopLoop();
  stopHeartbeat();

  try {
    await notify(`*Nexus Orchestrator* stopped (${signal})`);
  } catch { /* best-effort */ }

  process.exit(0);
}

process.on('SIGTERM', () => shutdown('SIGTERM'));
process.on('SIGINT',  () => shutdown('SIGINT'));
process.on('uncaughtException', (err) => {
  logger.error('uncaught_exception', { error: err?.message, stack: err?.stack });
});
process.on('unhandledRejection', (reason) => {
  logger.error('unhandled_rejection', { reason: String(reason) });
});

// ── Start ──────────────────────────────────────────────────────────────────

async function main() {
  validateConfig();

  logger.info('starting', {
    worker_id:     getEnv('WORKER_ID', 'nexus-orchestrator-1'),
    poll_interval: getEnv('POLL_INTERVAL_MS', '5000'),
    batch_size:    getEnv('POLL_BATCH_SIZE', '10'),
    max_attempts:  getEnv('MAX_EVENT_ATTEMPTS', '3'),
  });

  startMetricsReporter();
  startHeartbeat();
  startLoop();

  await notify(
    `*Nexus Orchestrator* started\n` +
    `Worker: \`${getEnv('WORKER_ID', 'nexus-orchestrator-1')}\`\n` +
    `Poll interval: ${getEnv('POLL_INTERVAL_MS', '5000')}ms`
  );
}

main().catch((err) => {
  process.stderr.write(`FATAL: ${err?.message}\n`);
  process.exit(1);
});
