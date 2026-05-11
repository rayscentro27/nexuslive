/**
 * telemetry/metrics.js — In-memory counters.
 * Logged to stdout every 5 minutes.
 */

const counters = {
  events_polled:    0,
  events_claimed:   0,
  events_skipped:   0,
  workflows_created: 0,
  jobs_enqueued:    0,
  jobs_blocked:     0,
  handler_errors:   0,
  alerts_emitted:   0,
};

export function inc(key, n = 1) {
  if (key in counters) counters[key] += n;
}

export function snapshot() {
  return { ...counters, ts: new Date().toISOString() };
}

export function startMetricsReporter(intervalMs = 300_000) {
  setInterval(() => {
    process.stdout.write(JSON.stringify({ level: 'info', component: 'metrics', ...snapshot() }) + '\n');
  }, intervalMs);
}
