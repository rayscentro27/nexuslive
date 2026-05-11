/**
 * routing/router.js — Dynamic handler dispatch.
 * Loads handler module by name and calls handle(event).
 */

import { resolveHandler } from './rules.js';
import { createLogger }   from '../telemetry/logger.js';
import { inc }            from '../telemetry/metrics.js';

const logger = createLogger('router');

// Cache loaded handler modules to avoid re-importing on every event
const handlerCache = new Map();

async function loadHandler(name) {
  if (handlerCache.has(name)) return handlerCache.get(name);
  const mod = await import(`../handlers/${name}.js`);
  handlerCache.set(name, mod);
  return mod;
}

/**
 * Dispatch an event to its handler.
 * Throws if the handler throws (caller handles retry/failure logic).
 */
export async function dispatch(event) {
  const handlerName = resolveHandler(event.event_type);

  if (!handlerName) {
    logger.warn('no_handler', { event_type: event.event_type, event_id: event.id });
    inc('handler_errors');
    throw new Error(`No handler registered for event_type: ${event.event_type}`);
  }

  logger.info('dispatching', { event_type: event.event_type, handler: handlerName, event_id: event.id });

  const mod = await loadHandler(handlerName);
  await mod.handle(event);
}
