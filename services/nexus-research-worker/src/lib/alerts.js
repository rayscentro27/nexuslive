/**
 * lib/alerts.js — Alert emission helper for the research worker.
 * Mirrors the orchestrator alert pattern but is self-contained.
 * Never throws — alert failures must not break job execution.
 */

import { db }           from '../supabase.js';
import { config }       from '../config.js';
import { createLogger } from '../logger.js';

const logger      = createLogger('alerts');
const COOLDOWN_MS = 5 * 60 * 1000; // 5 min dedup window
const cooldown    = new Map();

async function upsertMonitoringAlert(key, alert) {
  const now = new Date().toISOString();
  try {
    const { data: existing } = await db
      .from('monitoring_alerts')
      .select('id, occurrences')
      .eq('alert_key', key)
      .is('resolved_at', null)
      .limit(1)
      .single();

    if (existing) {
      await db.from('monitoring_alerts').update({
        occurrences:       (existing.occurrences ?? 0) + 1,
        last_triggered_at: now,
        severity:          alert.severity,
        summary:           alert.summary ?? alert.title,
        details:           alert.metadata ?? {},
        updated_at:        now,
      }).eq('id', existing.id);
    } else {
      await db.from('monitoring_alerts').insert({
        alert_key:          key,
        severity:           alert.severity,
        status:             'open',
        summary:            alert.summary ?? alert.title,
        details:            alert.metadata ?? {},
        tenant_id:          alert.tenant_id ?? null,
        first_triggered_at: now,
        last_triggered_at:  now,
        last_notified_at:   now,
        occurrences:        1,
      });
    }
  } catch (e) {
    logger.warn('monitoring_alert_write_failed', { error: e?.message, key });
  }
}

async function writeSystemError(key, alert) {
  try {
    await db.from('system_errors').insert({
      source:        alert.source_service ?? config.workerId,
      service:       alert.source_service ?? config.workerId,
      component:     alert.alert_type,
      severity:      alert.severity,
      error_code:    alert.alert_type,
      error_message: alert.body ?? alert.title,
      metadata: {
        alert_key:   key,
        worker_id:   alert.worker_id  ?? config.workerId,
        workflow_id: alert.workflow_id ?? null,
        job_id:      alert.job_id     ?? null,
        ...alert.metadata,
      },
    });
  } catch (e) {
    logger.warn('system_error_write_failed', { error: e?.message });
  }
}

/**
 * Emit an alert with dedup cooldown.
 *
 * @param {object} alert
 * @param {string} alert.alert_type
 * @param {string} alert.severity       'info' | 'warning' | 'critical'
 * @param {string} alert.title
 * @param {string} [alert.body]
 * @param {string} [alert.alert_key]    auto-derived if omitted
 * @param {string} [alert.source_service]
 * @param {string} [alert.worker_id]
 * @param {string} [alert.workflow_id]
 * @param {string} [alert.job_id]
 * @param {string} [alert.tenant_id]
 * @param {object} [alert.metadata]
 */
export async function emitAlert(alert) {
  try {
    const key = alert.alert_key ?? `${alert.alert_type}:${alert.worker_id ?? config.workerId}`;
    const now = Date.now();
    const inCooldown = (now - (cooldown.get(key) ?? 0)) < COOLDOWN_MS;

    logger.warn('alert', { type: alert.alert_type, severity: alert.severity, key, in_cooldown: inCooldown });

    // Always write raw system_error
    await writeSystemError(key, alert);

    // Upsert monitoring_alert (increment if in cooldown, new row otherwise)
    if (!inCooldown) {
      cooldown.set(key, now);
    }
    await upsertMonitoringAlert(key, alert);
  } catch (e) {
    logger.error('emit_alert_failed', { error: e?.message });
  }
}
