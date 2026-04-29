/**
 * routing/rules.js — Map event_type → handler module name.
 * Add new event types here as the system grows.
 */

export const EVENT_ROUTES = {
  // Research
  research_refresh_due:      'research',

  // Financial / CRM
  // funding_profile_updated is intentionally disabled. Funding recommendation refresh
  // is handled by the Python funding_engine path: DB trigger → funding_recommendation_jobs
  // → operations_center/scheduler.py → process_pending_recommendation_jobs().
  // Re-enable and wire to the Python job queue before routing events here.
  // funding_profile_updated:   'funding',
  credit_report_uploaded:    'credit',

  // Trading
  strategy_submitted:        'trading',
  signal_detected:           'signals',

  // Maintenance / operations
  daily_system_digest_due:   'maintenance',
  stale_state_sweep_due:     'maintenance',
};

/**
 * Returns the handler name for a given event_type, or null if unknown.
 */
export function resolveHandler(eventType) {
  return EVENT_ROUTES[eventType] ?? null;
}
