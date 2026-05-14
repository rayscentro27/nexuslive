export function boolFlag(name, defaultValue = "false") {
  return (process.env[name] || defaultValue).toLowerCase() === "true";
}

const ALLOWED = new Set([
  "conversational_reply",
  "critical_alert",
  "explicit_operator_requested_digest",
  "coding_agent_completion_ack",
]);

const BLOCKED = new Set([
  "opportunity_summary",
  "grant_summary",
  "research_summary",
  "ingestion_summary",
  "queue_summary",
  "scheduler_summary",
  "worker_summary",
  "ticket_summary",
  "provider_summary",
  "topic_brief",
  "run_summary",
  "auto_digest",
  "full_report",
  "opportunities_detected",
]);

export function shouldSendTelegramNotification(eventType, opts = {}) {
  const et = String(eventType || "").trim().toLowerCase();
  const userRequested = !!opts.userRequested;
  const conversational = !!opts.conversational;
  const critical = !!opts.critical;

  if (!et) return { ok: false, reason: "missing_event_type" };
  if (BLOCKED.has(et)) return { ok: false, reason: "blocked_event_type" };

  if (conversational && et === "conversational_reply") {
    return { ok: true, reason: "allowed_conversational" };
  }
  if (critical && et === "critical_alert") {
    return {
      ok: boolFlag("TELEGRAM_CRITICAL_ALERTS_ENABLED", "true"),
      reason: "critical_gate",
    };
  }
  if (userRequested && et === "explicit_operator_requested_digest") {
    return { ok: true, reason: "allowed_user_requested_digest" };
  }
  if (userRequested && et === "coding_agent_completion_ack") {
    return { ok: true, reason: "allowed_coding_ack" };
  }

  if (!boolFlag("TELEGRAM_OPERATIONAL_NOTIFICATIONS_ENABLED", "false")) {
    return { ok: false, reason: "operational_notifications_disabled" };
  }
  if (!ALLOWED.has(et)) return { ok: false, reason: "default_deny_not_allowlisted" };
  return { ok: true, reason: "allowlisted" };
}
