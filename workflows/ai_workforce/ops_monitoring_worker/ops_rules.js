// ── Ops Monitoring Rules ──────────────────────────────────────────────────────
// Detection rules for the Nexus Ops / Monitoring Worker.
// Each rule defines a threshold and produces a structured alert when triggered.
// ─────────────────────────────────────────────────────────────────────────────

export const ALERT_SEVERITY = Object.freeze({
  INFO:    "info",
  WARNING: "warning",
  CRITICAL: "critical",
});

// ── Rule definitions ──────────────────────────────────────────────────────────
// Each rule is a function: (metrics) → Alert | null
// Returns null if the condition is not triggered.

/**
 * Stale worker: last heartbeat older than threshold
 */
export function ruleStaleWorker(metrics) {
  const alerts = [];
  const now = Date.now();
  const WARNING_THRESHOLD_MS  = 30 * 60 * 1000;  // 30 minutes
  const CRITICAL_THRESHOLD_MS = 90 * 60 * 1000;  // 90 minutes

  for (const worker of (metrics.workers ?? [])) {
    if (!worker.last_heartbeat) continue;
    const age = now - new Date(worker.last_heartbeat).getTime();
    if (age > CRITICAL_THRESHOLD_MS) {
      alerts.push({
        rule:     "stale_worker",
        severity: ALERT_SEVERITY.CRITICAL,
        worker:   worker.worker_id ?? worker.id ?? "unknown",
        message:  `Worker has not sent a heartbeat in ${Math.round(age / 60000)}m`,
        detail:   { last_heartbeat: worker.last_heartbeat, age_minutes: Math.round(age / 60000) },
      });
    } else if (age > WARNING_THRESHOLD_MS) {
      alerts.push({
        rule:     "stale_worker",
        severity: ALERT_SEVERITY.WARNING,
        worker:   worker.worker_id ?? worker.id ?? "unknown",
        message:  `Worker heartbeat is ${Math.round(age / 60000)}m old`,
        detail:   { last_heartbeat: worker.last_heartbeat, age_minutes: Math.round(age / 60000) },
      });
    }
  }
  return alerts;
}

/**
 * Queue buildup: oldest pending job exceeds threshold
 */
export function ruleQueueBuildup(metrics) {
  const alerts = [];
  const WARNING_AGE_MINUTES  = 15;
  const CRITICAL_AGE_MINUTES = 60;

  const oldest = metrics.oldest_pending_job_minutes ?? null;
  if (oldest === null) return alerts;

  if (oldest > CRITICAL_AGE_MINUTES) {
    alerts.push({
      rule:     "queue_buildup",
      severity: ALERT_SEVERITY.CRITICAL,
      message:  `Oldest pending job is ${oldest}m old — queue may be stalled`,
      detail:   { oldest_pending_minutes: oldest },
    });
  } else if (oldest > WARNING_AGE_MINUTES) {
    alerts.push({
      rule:     "queue_buildup",
      severity: ALERT_SEVERITY.WARNING,
      message:  `Oldest pending job is ${oldest}m old`,
      detail:   { oldest_pending_minutes: oldest },
    });
  }
  return alerts;
}

/**
 * Dead-letter queue: too many failed jobs
 */
export function ruleDeadLetterCount(metrics) {
  const alerts = [];
  const WARNING_COUNT  = 5;
  const CRITICAL_COUNT = 20;

  const dlq = metrics.dead_letter_count ?? 0;
  if (dlq >= CRITICAL_COUNT) {
    alerts.push({
      rule:     "dead_letter_growth",
      severity: ALERT_SEVERITY.CRITICAL,
      message:  `${dlq} jobs in dead-letter queue — investigate failures`,
      detail:   { dead_letter_count: dlq },
    });
  } else if (dlq >= WARNING_COUNT) {
    alerts.push({
      rule:     "dead_letter_growth",
      severity: ALERT_SEVERITY.WARNING,
      message:  `${dlq} jobs in dead-letter queue`,
      detail:   { dead_letter_count: dlq },
    });
  }
  return alerts;
}

/**
 * Repeated failures: same job_type failing multiple times
 */
export function ruleRepeatedFailures(metrics) {
  const alerts = [];
  const THRESHOLD = 3;

  for (const [jobType, count] of Object.entries(metrics.failure_counts_by_type ?? {})) {
    if (count >= THRESHOLD) {
      alerts.push({
        rule:     "repeated_failures",
        severity: count >= 10 ? ALERT_SEVERITY.CRITICAL : ALERT_SEVERITY.WARNING,
        message:  `Job type "${jobType}" has failed ${count} time(s)`,
        detail:   { job_type: jobType, failure_count: count },
      });
    }
  }
  return alerts;
}

/**
 * Queue depth spike: total queue depth above threshold
 */
export function ruleQueueDepth(metrics) {
  const alerts = [];
  const WARNING_DEPTH  = 50;
  const CRITICAL_DEPTH = 200;

  const depth = metrics.queue_depth ?? 0;
  if (depth >= CRITICAL_DEPTH) {
    alerts.push({
      rule:     "queue_depth_spike",
      severity: ALERT_SEVERITY.CRITICAL,
      message:  `Queue depth is ${depth} — processing may be overwhelmed`,
      detail:   { queue_depth: depth },
    });
  } else if (depth >= WARNING_DEPTH) {
    alerts.push({
      rule:     "queue_depth_spike",
      severity: ALERT_SEVERITY.WARNING,
      message:  `Queue depth is ${depth}`,
      detail:   { queue_depth: depth },
    });
  }
  return alerts;
}

/**
 * Research pipeline stalled: no new artifacts in expected window
 */
export function ruleResearchPipelineStalled(metrics) {
  const alerts = [];
  const STALE_HOURS = 48;

  const lastArtifactAgeHours = metrics.last_artifact_age_hours ?? null;
  if (lastArtifactAgeHours === null) return alerts;

  if (lastArtifactAgeHours > STALE_HOURS) {
    alerts.push({
      rule:     "research_pipeline_stalled",
      severity: ALERT_SEVERITY.WARNING,
      message:  `No new research artifacts in ${lastArtifactAgeHours}h — research pipeline may be paused`,
      detail:   { last_artifact_age_hours: lastArtifactAgeHours },
    });
  }
  return alerts;
}

/**
 * Low total artifact count: database may not be populated
 */
export function ruleArtifactCount(metrics) {
  const alerts = [];
  const MIN_EXPECTED = 5;

  const count = metrics.total_artifact_count ?? 0;
  if (count < MIN_EXPECTED) {
    alerts.push({
      rule:     "low_artifact_count",
      severity: ALERT_SEVERITY.INFO,
      message:  `Only ${count} research artifact(s) in database — run research pipeline`,
      detail:   { artifact_count: count },
    });
  }
  return alerts;
}

/**
 * Launchd services: critical services not loaded or not running.
 * Warning for non-critical services, critical for critical ones.
 */
export function ruleServiceDown(metrics) {
  const alerts = [];
  for (const svc of (metrics.services ?? [])) {
    if (!svc.loaded) {
      alerts.push({
        rule:     "service_not_loaded",
        severity: svc.critical ? ALERT_SEVERITY.CRITICAL : ALERT_SEVERITY.WARNING,
        message:  `Service "${svc.name}" (${svc.label}) is not loaded in launchd`,
        detail:   { label: svc.label, name: svc.name, critical: svc.critical },
      });
    } else if (!svc.running) {
      const exitNote = svc.exit_status ? ` (exit ${svc.exit_status})` : "";
      alerts.push({
        rule:     "service_not_running",
        severity: svc.critical ? ALERT_SEVERITY.CRITICAL : ALERT_SEVERITY.WARNING,
        message:  `Service "${svc.name}" (${svc.label}) is loaded but not running${exitNote}`,
        detail:   { label: svc.label, name: svc.name, critical: svc.critical, exit_status: svc.exit_status },
      });
    }
  }
  return alerts;
}

// ── Rule runner ────────────────────────────────────────────────────────────────

const ALL_RULES = [
  ruleServiceDown,
  ruleStaleWorker,
  ruleQueueBuildup,
  ruleDeadLetterCount,
  ruleRepeatedFailures,
  ruleQueueDepth,
  ruleResearchPipelineStalled,
  ruleArtifactCount,
];

/**
 * Run all rules against a metrics snapshot and return triggered alerts.
 * @param {Object} metrics
 * @returns {Array} Triggered alerts, sorted by severity (critical first)
 */
export function evaluateAllRules(metrics) {
  const alerts = [];
  for (const rule of ALL_RULES) {
    const result = rule(metrics);
    if (Array.isArray(result)) alerts.push(...result);
    else if (result) alerts.push(result);
  }

  // Sort: critical > warning > info
  const order = { critical: 0, warning: 1, info: 2 };
  return alerts.sort((a, b) => (order[a.severity] ?? 3) - (order[b.severity] ?? 3));
}
