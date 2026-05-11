/**
 * index.js — Nexus Research Worker entry point.
 */

import { config }                        from './config.js';
import { startLoop, stopLoop }           from './loop.js';
import { startHeartbeat, stopHeartbeat } from './heartbeat.js';
import { createLogger }                  from './logger.js';

const logger = createLogger('main');

async function shutdown(signal) {
  logger.info('shutdown', { signal });
  stopLoop();
  stopHeartbeat();
  process.exit(0);
}

process.on('SIGTERM', () => shutdown('SIGTERM'));
process.on('SIGINT',  () => shutdown('SIGINT'));
process.on('uncaughtException',  (err) => logger.error('uncaught', { error: err?.message }));
process.on('unhandledRejection', (r)   => logger.error('unhandled_rejection', { reason: String(r) }));

logger.info('starting', {
  worker_id:      config.workerId,
  poll_interval:  config.pollIntervalMs,
  hermes_enabled: config.enableHermes,
});

startHeartbeat();
startLoop();
