/**
 * alerts/emit.js — Unified alert emission.
 *
 * Writes to:
 *   - monitoring_alerts  (deduped by alert_key, cooldown 5 min)
 *   - system_errors      (raw log, always)
 *   - Telegram           (if ENABLE_TELEGRAM_ALERTS=true)
 *
 * Never throws — alert failures must not break orchestrator loop.
 */

import { db, getEnv }   from '../clients/supabase.js';
import { createLogger } from '../telemetry/logger.js';
import { inc }          from '../telemetry/metrics.js';

const logger         = createLogger('alerts');
const TELEGRAM_TOKEN = getEnv('TELEGRAM_BOT_TOKEN', '');
const TELEGRAM_CHAT  = getEnv('TELEGRAM_CHAT_ID', '');
const ALERTS_ENABLED = getEnv('ENABLE_TELEGRAM_ALERTS', 'true') !== 'false';
const COOLDOWN_MS    = parseInt(getEnv('ALERT_COOLDOWN_MS', '300000'), 10); // 5 min default

// In-memory cooldown: alert_key → last emitted timestamp
const cooldown = new Map();

// ── Telegram ──────────────────────────────────────────────────────────────────

async function sendTelegram(text) {
  if (!ALERTS_ENABLED || !TELEGRAM_TOKEN || !TELEGRAM_CHAT) return;
  try {
    await fetch(`https://api.telegram.org/bot${TELEGRAM_TOKEN}/sendMessage`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ chat_id: TELEGRAM_CHAT, text, parse_mode: 'Markdown' }),
      signal:  AbortSignal.timeout(10_000),
    });
  } catch (e) {
    logger.warn('telegram_failed', { error: e?.message });
  }
}

function severityEmoji(severity) {
  return { critical: '🔴', warning: '⚠️', info: 'ℹ️' }[severity] ?? '⚠️';
}

function buildTelegramMessage(alert) {
  const em    = severityEmoji(alert.severity);
  const lines = [
    `${em} *Nexus ${alert.severity.toUpperCase()}*`,
    `*${alert.title}*`,
  ];
  if (alert.body)      lines.push(alert.body);
  if (alert.worker_id) lines.push(`Worker: \`${alert.worker_id}\``);
  if (alert.job_type)  lines.push(`Job type: \`${alert.job_type}\``);
  if (alert.tenant_id) lines.push(`Tenant: \`${String(alert.tenant_id).slice(0, 8)}...\``);
  return lines.join('\n');
}

// ── monitoring_alerts (deduped) ───────────────────────────────────────────────

async function upsertMonitoringAlert(alert) {
  const now = new Date().toISOString();
  try {
    // Try update first (increment occurrences)
    const { data: existing } = await db
      .from('monitoring_alerts')
      .select('id, occurrences')
      .eq('alert_key', alert.alert_key)
      .is('resolved_at', null)
      .limit(1)
      .single();

    if (existing) {
      await db.from('monitoring_alerts').update({
        occurrences:      (existing.occurrences ?? 0) + 1,
        last_triggered_at: now,
        severity:          alert.severity,
        summary:           alert.summary ?? alert.title,
        details:           alert.metadata ?? {},
        updated_at:        now,
      }).eq('id', existing.id);
    } else {
      await db.from('monitoring_alerts').insert({
        alert_key:         alert.alert_key,
        severity:          alert.severity,
        status:            'open',
        summary:           alert.summary ?? alert.title,
        details:           alert.metadata ?? {},
        tenant_id:         alert.tenant_id ?? null,
        first_triggered_at: now,
        last_triggered_at:  now,
        last_notified_at:   now,
        occurrences:       1,
      });
    }
  } catch (e) {
    logger.warn('monitoring_alert_write_failed', { error: e?.message, key: alert.alert_key });
  }
}

// ── system_errors (raw log) ───────────────────────────────────────────────────

async function writeSystemError(alert) {
  try {
    await db.from('system_errors').insert({
      source:        alert.source_service ?? 'nexus-orchestrator',
      service:       alert.source_service ?? 'orchestrator',
      component:     alert.job_type ?? alert.alert_type,
      severity:      alert.severity,
      error_code:    alert.alert_type,
      error_message: alert.body ?? alert.title,
      metadata:      {
        alert_key:   alert.alert_key,
        worker_id:   alert.worker_id,
        workflow_id: alert.workflow_id,
        job_id:      alert.job_id,
        job_type:    alert.job_type,
        tenant_id:   alert.tenant_id,
        ...alert.metadata,
      },
    });
  } catch (e) {
    logger.warn('system_error_write_failed', { error: e?.message });
  }
}

// ── Public API ────────────────────────────────────────────────────────────────

/**
 * Emit an alert. Deduped by alert_key within COOLDOWN_MS window.
 *
 * @param {object} alert
 * @param {string} alert.alert_type      — e.g. 'unsupported_job_type'
 * @param {string} alert.severity        — 'info' | 'warning' | 'critical'
 * @param {string} alert.title           — short human-readable title
 * @param {string} [alert.body]          — longer explanation
 * @param {string} [alert.alert_key]     — dedup key (auto-derived if omitted)
 * @param {string} [alert.source_service]
 * @param {string} [alert.worker_id]
 * @param {string} [alert.workflow_id]
 * @param {string} [alert.job_id]
 * @param {string} [alert.job_type]
 * @param {string} [alert.tenant_id]
 * @param {object} [alert.metadata]
 */
export async function emitAlert(alert) {
  try {
    const key = alert.alert_key ?? `${alert.alert_type}:${alert.worker_id ?? alert.job_type ?? 'system'}`;
    const now  = Date.now();

    const lastEmit = cooldown.get(key) ?? 0;
    const inCooldown = (now - lastEmit) < COOLDOWN_MS;

    inc('alerts_emitted');
    logger.warn('alert', { type: alert.alert_type, severity: alert.severity, key, in_cooldown: inCooldown, title: alert.title });

    // Always write system_error for raw log
    await writeSystemError({ ...alert, alert_key: key });

    if (!inCooldown) {
      cooldown.set(key, now);
      await upsertMonitoringAlert({ ...alert, alert_key: key });
      await sendTelegram(buildTelegramMessage(alert));
    } else {
      // Still increment occurrence count
      await upsertMonitoringAlert({ ...alert, alert_key: key });
    }
  } catch (e) {
    logger.error('emit_alert_failed', { error: e?.message });
  }
}

// ── Convenience wrappers ──────────────────────────────────────────────────────

export function alertUnsupportedJobType({ jobType, workflowId, eventId, tenantId }) {
  return emitAlert({
    alert_type:     'unsupported_job_type',
    severity:       'warning',
    title:          `No active worker supports \`${jobType}\``,
    body:           `Workflow blocked safely — job type has no registered worker. Workflow: ${workflowId ?? eventId ?? 'unknown'}.`,
    alert_key:      `unsupported_job_type:${jobType}`,
    source_service: 'nexus-orchestrator',
    job_type:       jobType,
    workflow_id:    workflowId,
    tenant_id:      tenantId,
    metadata:       { event_id: eventId, workflow_id: workflowId },
  });
}

export function alertWorkflowBlocked({ workflowId, eventId, reason, tenantId }) {
  return emitAlert({
    alert_type:     'workflow_blocked',
    severity:       'warning',
    title:          `Workflow blocked`,
    body:           reason,
    alert_key:      `workflow_blocked:${workflowId ?? eventId}`,
    source_service: 'nexus-orchestrator',
    workflow_id:    workflowId,
    tenant_id:      tenantId,
    metadata:       { event_id: eventId, reason },
  });
}

export function alertWorkerFailure({ workerId, jobType, jobId, errorMsg, attempt }) {
  const isCritical = attempt >= 3;
  return emitAlert({
    alert_type:     'worker_failure',
    severity:       isCritical ? 'critical' : 'warning',
    title:          `${workerId} failed on \`${jobType}\`${isCritical ? ' (max retries)' : ''}`,
    body:           errorMsg,
    alert_key:      `worker_failure:${workerId}:${jobType}`,
    source_service: workerId,
    worker_id:      workerId,
    job_id:         jobId,
    job_type:       jobType,
    metadata:       { attempt, error: errorMsg },
  });
}

export function alertHeartbeatMissing({ workerId, lastSeen }) {
  return emitAlert({
    alert_type:     'heartbeat_missing',
    severity:       'warning',
    title:          `Worker \`${workerId}\` heartbeat is stale`,
    body:           `Last seen: ${lastSeen ?? 'unknown'}. Worker may be offline.`,
    alert_key:      `heartbeat_missing:${workerId}`,
    source_service: 'nexus-orchestrator',
    worker_id:      workerId,
    metadata:       { last_seen: lastSeen },
  });
}

export function alertRecovery({ workerId, message }) {
  return emitAlert({
    alert_type:     'recovery',
    severity:       'info',
    title:          `${workerId} recovered`,
    body:           message,
    alert_key:      `recovery:${workerId}`,
    source_service: workerId,
    worker_id:      workerId,
    metadata:       {},
  });
}
