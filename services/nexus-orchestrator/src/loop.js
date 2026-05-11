/**
 * loop.js — Main poll loop.
 * Fetches pending events, races to claim each one, dispatches to handler.
 * Errors are recorded via retries guard; claimed events are always released.
 */

import { fetchPendingEvents } from './events/intake.js';
import { claimEvent, completeEvent } from './events/claim.js';
import { dispatch }           from './routing/router.js';
import { recordFailure }      from './guards/retries.js';
import { getEnv, isTransientSupabaseError } from './clients/supabase.js';
import { inc }                from './telemetry/metrics.js';
import { createLogger }       from './telemetry/logger.js';

const logger        = createLogger('loop');
const POLL_INTERVAL = parseInt(getEnv('POLL_INTERVAL_MS', '5000'), 10);

let running = false;
let timer   = null;

async function tick() {
  const events = await fetchPendingEvents();
  if (events.length === 0) return;

  // Process events concurrently (each claim is atomic — no double-processing)
  await Promise.allSettled(
    events.map(async (event) => {
      const won = await claimEvent(event.id);
      if (!won) return; // another orchestrator instance claimed it

      try {
        await dispatch(event);
        await completeEvent(event.id);
      } catch (err) {
        inc('handler_errors');
        logger.error('handler_threw', {
          event_id:   event.id,
          event_type: event.event_type,
          error:      err?.message,
        });
        await recordFailure(event.id, event.event_type, err, event.attempt_count ?? 0);
      }
    })
  );
}

export function startLoop() {
  if (running) return;
  running = true;

  logger.info('started', { poll_interval_ms: POLL_INTERVAL });

  const schedule = async () => {
    if (!running) return;
    try {
      await tick();
    } catch (e) {
      if (isTransientSupabaseError(e)) {
        logger.warn('tick_degraded', { error: e?.message });
      } else {
        logger.error('tick_uncaught', { error: e?.message });
      }
    }
    if (running) timer = setTimeout(schedule, POLL_INTERVAL);
  };

  schedule();
}

export function stopLoop() {
  running = false;
  if (timer) clearTimeout(timer);
  logger.info('stopped');
}
