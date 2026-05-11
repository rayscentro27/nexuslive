/**
 * telemetry/logger.js — Structured JSON logger.
 */

const LEVELS = { debug: 0, info: 1, warn: 2, error: 3 };
const currentLevel = LEVELS[process.env.LOG_LEVEL?.toLowerCase() ?? 'info'] ?? 1;

function log(level, component, message, data = {}) {
  if (LEVELS[level] < currentLevel) return;
  const entry = {
    ts:        new Date().toISOString(),
    level,
    component,
    message,
    ...data,
  };
  const out = level === 'error' ? process.stderr : process.stdout;
  out.write(JSON.stringify(entry) + '\n');
}

export function createLogger(component) {
  return {
    debug: (msg, data) => log('debug', component, msg, data),
    info:  (msg, data) => log('info',  component, msg, data),
    warn:  (msg, data) => log('warn',  component, msg, data),
    error: (msg, data) => log('error', component, msg, data),
  };
}
