/**
 * logger.js — Structured JSON logger (matches orchestrator pattern).
 */

export function createLogger(component) {
  const write = (level, message, meta = {}) => {
    process.stdout.write(
      JSON.stringify({ ts: new Date().toISOString(), level, component, message, ...meta }) + '\n'
    );
  };
  return {
    info:  (msg, meta) => write('info',  msg, meta),
    warn:  (msg, meta) => write('warn',  msg, meta),
    error: (msg, meta) => write('error', msg, meta),
    debug: (msg, meta) => write('debug', msg, meta),
  };
}
