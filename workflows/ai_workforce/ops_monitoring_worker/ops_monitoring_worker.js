#!/usr/bin/env node
// ── Ops / Monitoring Worker ────────────────────────────────────────────────────
// Monitors Nexus system health and queue metrics, evaluates detection rules,
// and sends alerts to Telegram when thresholds are exceeded.
//
// Data sources (READ only — no writes to business tables):
//   - Supabase: research_artifacts counts, worker_heartbeats, job_queue tables
//   - Supabase: system_errors table (if available)
//   - (Future) Oracle VM /api/system/health endpoint (Windows machine scope)
//
// Direct run:
//   node ops_monitoring_worker.js [--dry-run] [--quiet] [--summary]
//
// Queue mode (imported):
//   import { runOpsMonitoringWorker } from "./ops_monitoring_worker.js";
//   await runOpsMonitoringWorker({ dry_run: false, quiet: false });
//
// This worker never writes to business tables, never restarts services, and
// never modifies any configuration automatically.
// ─────────────────────────────────────────────────────────────────────────────

import "../env.js";
import { execFileSync } from "child_process";
import { evaluateAllRules, ALERT_SEVERITY } from "./ops_rules.js";
import {
  buildOpsSummary,
  formatConsoleHealth,
  formatTelegramOpsSummary,
  formatTelegramAlertMessage,
} from "./ops_alert_formatter.js";

// Services the ops worker actively monitors via launchctl.
// Add or remove labels here as the system topology changes.
const MONITORED_SERVICES = [
  { label: "com.nexus.hermes",              name: "Hermes",       critical: true },
  { label: "com.nexus.signal-router",          name: "Signal Router",  critical: true },
  { label: "com.raymonddavis.nexus.dashboard", name: "Dashboard",      critical: false },
  { label: "com.raymonddavis.nexus.telegram",  name: "Telegram Bot",   critical: true },
];

const SUPABASE_URL = process.env.SUPABASE_URL;
const SUPABASE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY ?? process.env.SUPABASE_KEY;
const TELEGRAM_BOT_TOKEN = process.env.TELEGRAM_BOT_TOKEN;
const TELEGRAM_CHAT_ID   = process.env.TELEGRAM_CHAT_ID;

// ── Supabase helpers (read-only) ──────────────────────────────────────────────

async function supabaseGetOrNull(path) {
  try {
    const res = await fetch(`${SUPABASE_URL}/rest/v1/${path}`, {
      headers: {
        apikey: SUPABASE_KEY,
        Authorization: `Bearer ${SUPABASE_KEY}`,
        "Content-Type": "application/json",
      },
    });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

// ── Metrics collection ────────────────────────────────────────────────────────

async function collectArtifactMetrics() {
  // Total artifact count
  const countResult = await supabaseGetOrNull(
    "research_artifacts?select=id&limit=1000"
  );
  const total_artifact_count = countResult?.length ?? 0;

  // Most recent artifact
  const recentResult = await supabaseGetOrNull(
    "research_artifacts?select=created_at&order=created_at.desc&limit=1"
  );
  let last_artifact_age_hours = null;
  if (recentResult?.[0]?.created_at) {
    const age = Date.now() - new Date(recentResult[0].created_at).getTime();
    last_artifact_age_hours = Math.round(age / 3600000);
  }

  return { total_artifact_count, last_artifact_age_hours };
}

async function collectWorkerMetrics() {
  // Try worker_heartbeats table (may not exist yet)
  const workers = await supabaseGetOrNull(
    "worker_heartbeats?select=worker_id,last_heartbeat,status&order=last_heartbeat.desc&limit=20"
  ) ?? [];
  return { workers };
}

async function collectQueueMetrics() {
  // Try job_queue table (may not exist yet)
  const allJobs = await supabaseGetOrNull(
    "job_queue?select=id,status,job_type,created_at&order=created_at.asc&limit=500"
  ) ?? [];

  const pending = allJobs.filter((j) => j.status === "pending");
  const failed  = allJobs.filter((j) => j.status === "failed" || j.status === "dead_letter");

  const queue_depth = pending.length;
  const dead_letter_count = failed.filter((j) => j.status === "dead_letter").length;

  // Oldest pending job
  let oldest_pending_job_minutes = null;
  if (pending.length > 0 && pending[0].created_at) {
    const age = Date.now() - new Date(pending[0].created_at).getTime();
    oldest_pending_job_minutes = Math.round(age / 60000);
  }

  // Failure counts by job_type
  const failure_counts_by_type = {};
  for (const job of failed) {
    const t = job.job_type ?? "unknown";
    failure_counts_by_type[t] = (failure_counts_by_type[t] ?? 0) + 1;
  }

  return { queue_depth, dead_letter_count, oldest_pending_job_minutes, failure_counts_by_type };
}

async function collectSystemMetrics() {
  // Try system_errors table (may not exist yet)
  const recentErrors = await supabaseGetOrNull(
    "system_errors?select=error_type,created_at&order=created_at.desc&limit=20"
  ) ?? [];

  const system_mode = process.env.NODE_ENV ?? "unknown";

  return { system_mode, recent_error_count: recentErrors.length };
}

// ── Launchd service status (READ-ONLY) ───────────────────────────────────────

function tryLaunchctlList() {
  try {
    return execFileSync("launchctl", ["list"], {
      encoding: "utf8",
      timeout: 10_000,
      maxBuffer: 1024 * 1024,
    });
  } catch {
    return "";
  }
}

/**
 * Parse one row of `launchctl list` output (tab-separated: PID Status Label).
 * Returns { pid: number|null, exitStatus: number } or null if unparseable.
 */
function parseLaunchctlRow(line, label) {
  const cols = line.split("\t");
  if (cols.length < 3) return null;
  const [rawPid, rawStatus] = cols;
  return {
    pid:        rawPid === "-" ? null : parseInt(rawPid, 10),
    exitStatus: parseInt(rawStatus, 10) || 0,
  };
}

function collectLaunchdMetrics() {
  const raw = tryLaunchctlList();
  const services = MONITORED_SERVICES.map(({ label, name, critical }) => {
    const matchingLine = raw.split("\n").find((l) => l.includes(label));
    if (!matchingLine) {
      return { label, name, critical, loaded: false, running: false, pid: null, exit_status: null };
    }
    const parsed = parseLaunchctlRow(matchingLine, label);
    const pid        = parsed?.pid ?? null;
    const exitStatus = parsed?.exitStatus ?? 0;
    return {
      label,
      name,
      critical,
      loaded:      true,
      running:     pid !== null,
      pid,
      exit_status: exitStatus,
    };
  });
  return { services };
}

// ── Metrics snapshot ──────────────────────────────────────────────────────────

async function collectAllMetrics() {
  const [artifacts, workers, queue, system] = await Promise.all([
    collectArtifactMetrics(),
    collectWorkerMetrics(),
    collectQueueMetrics(),
    collectSystemMetrics(),
  ]);

  // launchd is synchronous — run after the async batch to avoid blocking
  const launchd = collectLaunchdMetrics();

  return {
    ...artifacts,
    ...workers,
    ...queue,
    ...system,
    ...launchd,
  };
}

// ── Telegram sender ───────────────────────────────────────────────────────────

async function sendTelegramMessage(text) {
  if (!TELEGRAM_BOT_TOKEN || !TELEGRAM_CHAT_ID) {
    console.warn("[ops-worker] Telegram not configured — skipping alert.");
    return;
  }
  try {
    const res = await fetch(`https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        chat_id: TELEGRAM_CHAT_ID,
        text,
        parse_mode: "MarkdownV2",
      }),
    });
    if (!res.ok) console.warn(`[ops-worker] Telegram error: ${await res.text()}`);
  } catch (err) {
    console.warn(`[ops-worker] Telegram send failed: ${err.message}`);
  }
}

// ── Core worker ───────────────────────────────────────────────────────────────

/**
 * Main OpsMonitoringWorker execution.
 *
 * @param {Object} [opts]
 * @param {boolean} [opts.dry_run=false]    - Collect + evaluate but don't send alerts
 * @param {boolean} [opts.quiet=false]      - Suppress console output
 * @param {boolean} [opts.summary_only=false] - Always send summary (not just alerts)
 * @param {string}  [opts.alert_threshold="warning"] - Minimum severity to alert on
 * @returns {Promise<Object>} ops summary
 */
export async function runOpsMonitoringWorker({
  dry_run = false,
  quiet = false,
  summary_only = false,
  alert_threshold = "warning",
} = {}) {
  if (!quiet) {
    console.log(`\n[ops-worker] Starting health check — dry_run=${dry_run}`);
  }

  // 1. Collect metrics
  const metrics = await collectAllMetrics();

  // 2. Evaluate rules
  const alerts = evaluateAllRules(metrics);

  // 3. Build summary
  const summary = buildOpsSummary(metrics, alerts);

  // 4. Console output
  if (!quiet) {
    console.log(formatConsoleHealth(summary));
  }

  if (dry_run) {
    console.log("[ops-worker] DRY RUN — no Telegram alerts sent.");
    return summary;
  }

  // 5. Determine what to send to Telegram
  const severityOrder = { critical: 0, warning: 1, info: 2 };
  const thresholdLevel = severityOrder[alert_threshold] ?? 1;

  const alertsToSend = alerts.filter(
    (a) => (severityOrder[a.severity] ?? 3) <= thresholdLevel
  );

  if (summary_only) {
    // Always send full summary
    await sendTelegramMessage(formatTelegramOpsSummary(summary));
  } else if (alertsToSend.length > 0) {
    // Only send when there are alerts above threshold
    const hasCritical = alertsToSend.some((a) => a.severity === ALERT_SEVERITY.CRITICAL);
    const recommendedAction = hasCritical
      ? "Check Supabase queue tables and worker heartbeats."
      : null;
    const text = formatTelegramAlertMessage(alertsToSend, { recommended_action: recommendedAction });
    if (text) await sendTelegramMessage(text);
  }
  // If no alerts and not summary_only — stay quiet (don't spam Telegram daily)

  if (!quiet) {
    console.log(`[ops-worker] Done — ${summary.overall_status.toUpperCase()} | ${alerts.length} alert(s)`);
  }

  return summary;
}

// ── CLI entry ─────────────────────────────────────────────────────────────────

const args = process.argv.slice(2);

if (args.includes("--help")) {
  console.log([
    "Usage: node ops_monitoring_worker.js [options]",
    "",
    "Options:",
    "  --dry-run         Collect metrics, evaluate rules, no Telegram",
    "  --summary         Always send full summary to Telegram (not just alerts)",
    "  --quiet           Suppress console output",
    "  --threshold <lvl> Alert threshold: warning (default) | critical | info",
    "  --help            Show this help",
    "",
    "Data sources: Supabase (research_artifacts, worker_heartbeats, job_queue, system_errors)",
    "Outputs: Console health report + Telegram alert (when thresholds exceeded)",
  ].join("\n"));
  process.exit(0);
}

function getArg(f, d) { const i = args.indexOf(f); return i !== -1 ? args[i + 1] : d; }

const isDirect = process.argv[1]?.endsWith("ops_monitoring_worker.js");
if (isDirect) {
  runOpsMonitoringWorker({
    dry_run:       args.includes("--dry-run"),
    quiet:         args.includes("--quiet"),
    summary_only:  args.includes("--summary"),
    alert_threshold: getArg("--threshold", "warning"),
  }).catch((err) => {
    console.error(`[ops-worker] Fatal: ${err.message}`);
    if (process.env.DEBUG) console.error(err.stack);
    process.exit(1);
  });
}
