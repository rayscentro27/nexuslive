// ── Ops Alert Formatter ────────────────────────────────────────────────────────
// Formats Ops Worker alerts and summaries for Telegram and console output.
// ─────────────────────────────────────────────────────────────────────────────

import { ALERT_SEVERITY } from "./ops_rules.js";

// ── Severity icons ────────────────────────────────────────────────────────────

const SEVERITY_ICON = {
  [ALERT_SEVERITY.CRITICAL]: "🔴",
  [ALERT_SEVERITY.WARNING]:  "🟡",
  [ALERT_SEVERITY.INFO]:     "🔵",
};

const SEVERITY_LABEL = {
  [ALERT_SEVERITY.CRITICAL]: "CRITICAL",
  [ALERT_SEVERITY.WARNING]:  "WARNING",
  [ALERT_SEVERITY.INFO]:     "INFO",
};

// ── Console formatters ────────────────────────────────────────────────────────

/**
 * Format a health summary for console output.
 * @param {Object} summary - Output from buildOpsSummary()
 * @returns {string}
 */
export function formatConsoleHealth(summary) {
  const lines = [
    "",
    "╔═══════════════════════════════════════════════════════════╗",
    "║  NEXUS OPS HEALTH REPORT                                  ║",
    "╚═══════════════════════════════════════════════════════════╝",
    `  Generated : ${new Date(summary.generated_at).toLocaleString()}`,
    `  System    : ${summary.system_mode ?? "unknown"}`,
    `  Artifacts : ${summary.artifact_count ?? 0} total`,
    `  Queue     : ${summary.queue_depth ?? 0} pending`,
    `  Workers   : ${summary.worker_count ?? 0} tracked`,
    "",
  ];

  // Service status table
  if (summary.services?.length > 0) {
    lines.push("  Services:");
    for (const svc of summary.services) {
      const icon = svc.running ? "✅" : svc.loaded ? "⚠️ " : "🔴";
      const pid  = svc.running ? ` (pid ${svc.pid})` : "";
      lines.push(`    ${icon} ${svc.name}${pid}`);
    }
    lines.push("");
  }

  if (summary.alerts.length === 0) {
    lines.push("  ✅ All checks passed — no alerts.");
  } else {
    lines.push(`  ${summary.alerts.length} alert(s) detected:\n`);
    for (const alert of summary.alerts) {
      const icon = SEVERITY_ICON[alert.severity] ?? "⚪";
      lines.push(`  ${icon} [${SEVERITY_LABEL[alert.severity]}] ${alert.message}`);
    }
  }

  lines.push("");
  return lines.join("\n");
}

/**
 * Format alerts for concise console display.
 * @param {Array} alerts
 * @returns {string}
 */
export function formatConsoleAlerts(alerts) {
  if (!alerts.length) return "No active alerts.";
  return alerts.map((a) => {
    const icon = SEVERITY_ICON[a.severity] ?? "⚪";
    return `${icon} [${a.rule}] ${a.message}`;
  }).join("\n");
}

// ── Telegram formatters ───────────────────────────────────────────────────────

/**
 * Format a full ops summary for Telegram (MarkdownV2).
 * @param {Object} summary
 * @returns {string}
 */
export function formatTelegramOpsSummary(summary) {
  const hasCritical = summary.alerts.some((a) => a.severity === ALERT_SEVERITY.CRITICAL);
  const hasWarning  = summary.alerts.some((a) => a.severity === ALERT_SEVERITY.WARNING);

  const header = hasCritical ? "🔴 *NEXUS OPS — CRITICAL ALERT*"
               : hasWarning  ? "🟡 *NEXUS OPS — WARNING*"
               :               "✅ *NEXUS OPS SUMMARY*";

  const escape = (s) => String(s).replace(/[_*[\]()~`>#+=|{}.!-]/g, "\\$&");

  const lines = [header, ""];

  // Status line
  const statusEmoji = hasCritical ? "🔴" : hasWarning ? "🟡" : "✅";
  lines.push(`${statusEmoji} Status: ${escape(hasCritical ? "Needs attention" : hasWarning ? "Warnings present" : "Healthy")}`);
  lines.push(`📦 Queue depth: ${escape(summary.queue_depth ?? 0)}`);
  lines.push(`🔬 Artifacts: ${escape(summary.artifact_count ?? 0)}`);
  lines.push(`⚙️  Workers: ${escape(summary.worker_count ?? 0)}`);

  // Service status block
  if (summary.services?.length > 0) {
    lines.push("");
    lines.push("*Services:*");
    for (const svc of summary.services) {
      const icon = svc.running ? "✅" : svc.loaded ? "⚠️" : "🔴";
      lines.push(`${icon} ${escape(svc.name)}`);
    }
  }

  lines.push("");

  if (summary.alerts.length === 0) {
    lines.push("All checks passed\\.");
  } else {
    for (const alert of summary.alerts.slice(0, 5)) {
      const icon = SEVERITY_ICON[alert.severity] ?? "⚪";
      lines.push(`${icon} ${escape(alert.message)}`);
    }
    if (summary.alerts.length > 5) {
      lines.push(`_\\.\\.\\. and ${summary.alerts.length - 5} more_`);
    }
  }

  return lines.join("\n");
}

/**
 * Format a compact alert-only message for Telegram.
 * Used when only critical/warning alerts are present.
 * @param {Array} alerts - Filtered alerts (critical/warning only)
 * @param {Object} [context] - Optional context (queue_depth, worker_count, etc.)
 * @returns {string}
 */
export function formatTelegramAlertMessage(alerts, context = {}) {
  if (!alerts.length) return null;

  const escape = (s) => String(s).replace(/[_*[\]()~`>#+=|{}.!-]/g, "\\$&");
  const hasCritical = alerts.some((a) => a.severity === ALERT_SEVERITY.CRITICAL);

  const lines = [
    hasCritical ? "🔴 *NEXUS OPS ALERT*" : "🟡 *NEXUS OPS WARNING*",
    "",
  ];

  for (const alert of alerts.slice(0, 5)) {
    const icon = SEVERITY_ICON[alert.severity] ?? "⚪";
    lines.push(`${icon} ${escape(alert.message)}`);
  }

  if (context.recommended_action) {
    lines.push("", `💡 ${escape(context.recommended_action)}`);
  }

  lines.push("", `_${escape(new Date().toLocaleString())}_`);
  return lines.join("\n");
}

// ── Summary builder ───────────────────────────────────────────────────────────

/**
 * Build a structured ops summary object from raw metrics and alerts.
 * @param {Object} metrics - Raw metrics snapshot
 * @param {Array} alerts - Evaluated alerts from ops_rules.js
 * @returns {Object}
 */
export function buildOpsSummary(metrics, alerts) {
  return {
    generated_at:         new Date().toISOString(),
    system_mode:          metrics.system_mode ?? "unknown",
    artifact_count:       metrics.total_artifact_count ?? 0,
    queue_depth:          metrics.queue_depth ?? 0,
    worker_count:         (metrics.workers ?? []).length,
    dead_letter_count:    metrics.dead_letter_count ?? 0,
    oldest_pending_minutes: metrics.oldest_pending_job_minutes ?? null,
    last_artifact_age_hours: metrics.last_artifact_age_hours ?? null,
    services:             metrics.services ?? [],
    alerts,
    alert_count: {
      critical: alerts.filter((a) => a.severity === ALERT_SEVERITY.CRITICAL).length,
      warning:  alerts.filter((a) => a.severity === ALERT_SEVERITY.WARNING).length,
      info:     alerts.filter((a) => a.severity === ALERT_SEVERITY.INFO).length,
    },
    overall_status: alerts.some((a) => a.severity === ALERT_SEVERITY.CRITICAL) ? "critical"
                  : alerts.some((a) => a.severity === ALERT_SEVERITY.WARNING)  ? "warning"
                  : "healthy",
  };
}
