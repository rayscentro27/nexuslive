// ── Workforce Job Types ───────────────────────────────────────────────────────
// Canonical enum of all queue job types across the Nexus AI Workforce.
// Used by workforce_dispatcher.js and any external job schedulers.
// ─────────────────────────────────────────────────────────────────────────────

export const JOB_TYPE = Object.freeze({
  // ── ResearchWorker ──
  RESEARCH_TRANSCRIPT:       "research_transcript",
  RESEARCH_BROWSER:          "research_browser",
  RESEARCH_MANUAL:           "research_manual",
  RESEARCH_ALL:              "research_all",

  // ── GrantWorker ──
  GRANT_SCAN:                "grant_scan",
  GRANT_NORMALIZATION:       "grant_normalization",
  GRANT_BRIEF:               "grant_brief",

  // ── OpportunityWorker ──
  BUSINESS_SCAN:             "business_scan",
  OPPORTUNITY_SCAN:          "opportunity_scan",
  OPPORTUNITY_BRIEF:         "opportunity_brief",

  // ── CreditWorker ──
  CREDIT_ARTIFACT_SCAN:      "credit_artifact_scan",
  CREDIT_DISPUTE_DRAFT:      "credit_dispute_draft",       // requires human approval
  CREDIT_POLICY_REVIEW:      "credit_policy_review",

  // ── ContentWorker ──
  CONTENT_BRIEF_GENERATE:    "content_brief_generate",
  CONTENT_SOCIAL_DRAFT:      "content_social_draft",       // draft only, no publish
  CONTENT_NEWSLETTER_DRAFT:  "content_newsletter_draft",   // draft only

  // ── CRMCopilotWorker ──
  CRM_WORKFLOW_SCAN:         "crm_workflow_scan",
  CRM_SUGGESTION_GENERATE:   "crm_suggestion_generate",   // draft only
  CRM_AUDIT_RUN:             "crm_audit_run",

  // ── ClientPortalAssistantWorker ──
  PORTAL_QUERY_RESPOND:      "portal_query_respond",       // client-facing, scoped
  PORTAL_RESEARCH_LOOKUP:    "portal_research_lookup",

  // ── TradingResearchWorker ──
  TRADING_ARTIFACT_SCAN:     "trading_artifact_scan",
  TRADING_STRATEGY_DRAFT:    "trading_strategy_draft",     // requires human approval
  TRADING_BRIEF_GENERATE:    "trading_brief_generate",

  // ── RiskComplianceWorker ──
  RISK_PROPOSAL_REVIEW:      "risk_proposal_review",
  COMPLIANCE_FLAG_SCAN:      "compliance_flag_scan",
  RISK_BRIEF_GENERATE:       "risk_brief_generate",

  // ── OpsMonitoringWorker ──
  OPS_HEALTH_CHECK:          "ops_health_check",
  OPS_QUEUE_METRICS:         "ops_queue_metrics",
  OPS_ALERT_ON_FAILURE:      "ops_alert_on_failure",
  OPS_DAILY_SUMMARY:         "ops_daily_summary",
});

// ── Role → Job type mapping ──────────────────────────────────────────────────
export const ROLE_JOB_TYPES = Object.freeze({
  research_worker:         [JOB_TYPE.RESEARCH_TRANSCRIPT, JOB_TYPE.RESEARCH_BROWSER, JOB_TYPE.RESEARCH_MANUAL, JOB_TYPE.RESEARCH_ALL],
  grant_worker:            [JOB_TYPE.GRANT_SCAN, JOB_TYPE.GRANT_NORMALIZATION, JOB_TYPE.GRANT_BRIEF],
  opportunity_worker:      [JOB_TYPE.BUSINESS_SCAN, JOB_TYPE.OPPORTUNITY_SCAN, JOB_TYPE.OPPORTUNITY_BRIEF],
  credit_worker:           [JOB_TYPE.CREDIT_ARTIFACT_SCAN, JOB_TYPE.CREDIT_DISPUTE_DRAFT, JOB_TYPE.CREDIT_POLICY_REVIEW],
  content_worker:          [JOB_TYPE.CONTENT_BRIEF_GENERATE, JOB_TYPE.CONTENT_SOCIAL_DRAFT, JOB_TYPE.CONTENT_NEWSLETTER_DRAFT],
  crm_copilot_worker:      [JOB_TYPE.CRM_WORKFLOW_SCAN, JOB_TYPE.CRM_SUGGESTION_GENERATE, JOB_TYPE.CRM_AUDIT_RUN],
  client_portal_assistant: [JOB_TYPE.PORTAL_QUERY_RESPOND, JOB_TYPE.PORTAL_RESEARCH_LOOKUP],
  trading_research_worker: [JOB_TYPE.TRADING_ARTIFACT_SCAN, JOB_TYPE.TRADING_STRATEGY_DRAFT, JOB_TYPE.TRADING_BRIEF_GENERATE],
  risk_compliance_worker:  [JOB_TYPE.RISK_PROPOSAL_REVIEW, JOB_TYPE.COMPLIANCE_FLAG_SCAN, JOB_TYPE.RISK_BRIEF_GENERATE],
  ops_monitoring_worker:   [JOB_TYPE.OPS_HEALTH_CHECK, JOB_TYPE.OPS_QUEUE_METRICS, JOB_TYPE.OPS_ALERT_ON_FAILURE, JOB_TYPE.OPS_DAILY_SUMMARY],
});

// ── Jobs requiring human approval before action ──────────────────────────────
export const APPROVAL_REQUIRED_JOBS = new Set([
  JOB_TYPE.CREDIT_DISPUTE_DRAFT,
  JOB_TYPE.TRADING_STRATEGY_DRAFT,
  JOB_TYPE.CONTENT_SOCIAL_DRAFT,
  JOB_TYPE.CONTENT_NEWSLETTER_DRAFT,
  JOB_TYPE.CRM_SUGGESTION_GENERATE,
  JOB_TYPE.PORTAL_QUERY_RESPOND,
]);
