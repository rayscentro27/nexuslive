// ── Workforce Roles ───────────────────────────────────────────────────────────
// Defines all 10 Nexus AI Employee roles with mission, tasks, I/O, and
// tool/permission boundaries.
// ─────────────────────────────────────────────────────────────────────────────

export const ROLES = Object.freeze({

  // ── 1. ResearchWorker ───────────────────────────────────────────────────────
  research_worker: {
    id: "research_worker",
    name: "Research Worker",
    mission: "Ingest content from all lanes (transcript/manual/browser), extract claims, and write artifacts to the Nexus Brain.",
    audience: "internal",
    primary_tasks: [
      "YouTube transcript extraction via yt-dlp",
      "Manual JSON/text source ingestion",
      "Comet browser research (placeholder or real)",
      "Topic classification and claim extraction via OpenClaw",
      "Writing research_artifacts, research_claims, memory, graph, clusters",
    ],
    input_sources: [
      "sample_sources.json (source registry)",
      "manual_sources/ folder",
      "sample_manual_research.json",
      "YouTube channels/videos",
      "Websites (via Comet adapter)",
    ],
    output_tables: [
      "research_artifacts", "research_claims", "research",
      "research_relationships", "research_clusters", "research_briefs",
    ],
    allowed_tools: ["yt-dlp", "Hermes (localhost:8642)", "Supabase REST API", "Telegram"],
    disallowed_tools: ["broker APIs", "client CRM data", "live trading systems", "Oracle VM"],
    implementation: "workflows/autonomous_research_supernode/research_orchestrator.js",
    status: "implemented",
  },

  // ── 2. GrantWorker ──────────────────────────────────────────────────────────
  grant_worker: {
    id: "grant_worker",
    name: "Grant Worker",
    mission: "Scan grant research artifacts, normalize, score, and surface actionable grant opportunities for small business owners.",
    audience: "internal",
    primary_tasks: [
      "Load research_artifacts WHERE topic = 'grant_research'",
      "Extract funding amounts, deadlines, geography, eligibility",
      "Score 0-100 using heuristic scoring model",
      "Write ranked opportunities to grant_opportunities",
      "Generate brief and Telegram alert for top grants",
    ],
    input_sources: ["research_artifacts (grant_research topic)"],
    output_tables: ["grant_opportunities", "research_briefs (optional)"],
    allowed_tools: ["Supabase REST API", "Telegram"],
    disallowed_tools: ["yt-dlp", "OpenClaw", "broker APIs", "client PII", "Oracle VM"],
    implementation: "workflows/ai_workforce/grant_worker/grant_worker.js",
    status: "implemented",
  },

  // ── 3. OpportunityWorker ────────────────────────────────────────────────────
  opportunity_worker: {
    id: "opportunity_worker",
    name: "Opportunity Worker",
    mission: "Scan business opportunity artifacts, detect recurring niches and service gaps, score, and surface monetizable ideas.",
    audience: "internal",
    primary_tasks: [
      "Load research_artifacts WHERE topic IN ('business_opportunities', 'crm_automation')",
      "Detect opportunity type, niche, monetization hint, urgency",
      "Score 0-100 using heuristic scoring model",
      "Identify repeated niches as demand signals",
      "Write ranked opportunities to business_opportunities",
      "Generate brief and Telegram alert",
    ],
    input_sources: ["research_artifacts (business_opportunities, crm_automation topics)"],
    output_tables: ["business_opportunities", "research_briefs (optional)"],
    allowed_tools: ["Supabase REST API", "Telegram"],
    disallowed_tools: ["yt-dlp", "OpenClaw", "broker APIs", "client PII", "Oracle VM"],
    implementation: "workflows/ai_workforce/opportunity_worker/opportunity_worker.js",
    status: "implemented",
  },

  // ── 4. CreditWorker ─────────────────────────────────────────────────────────
  credit_worker: {
    id: "credit_worker",
    name: "Credit Worker",
    mission: "Analyze credit repair research artifacts, generate PII-safe dispute workflow templates, and track FCRA policy updates.",
    audience: "internal (draft outputs require human review before client exposure)",
    primary_tasks: [
      "Load research_artifacts WHERE topic = 'credit_repair'",
      "Extract dispute strategies, FCRA references, statute citations",
      "Generate dispute letter templates (PII-free scaffolds only)",
      "Identify policy updates from CFPB/FTC sources",
      "Flag medical debt, authorized user, and high-impact strategies",
    ],
    input_sources: ["research_artifacts (credit_repair topic)"],
    output_tables: ["research_briefs", "credit_dispute_drafts (future table)"],
    allowed_tools: ["Supabase REST API", "Telegram (internal alerts only)"],
    disallowed_tools: [
      "raw client credit reports", "client SSN/DOB/account numbers",
      "broker APIs", "Oracle VM", "direct credit bureau API",
    ],
    human_approval_required: ["credit_dispute_draft — all drafts need review before client use"],
    implementation: "workflows/ai_workforce/credit_worker/ (stub — pending implementation)",
    status: "stub",
  },

  // ── 5. ContentWorker ────────────────────────────────────────────────────────
  content_worker: {
    id: "content_worker",
    name: "Content Worker",
    mission: "Generate content briefs, social post drafts, and newsletter outlines from research briefs and opportunity findings.",
    audience: "internal (drafts only — human publishes)",
    primary_tasks: [
      "Read research_briefs and business_opportunities",
      "Generate social post drafts (LinkedIn, Twitter/X format)",
      "Generate email newsletter outlines",
      "Create content calendars based on research themes",
    ],
    input_sources: ["research_briefs", "business_opportunities", "grant_opportunities"],
    output_tables: ["content_drafts (future table)"],
    allowed_tools: ["Supabase REST API", "OpenClaw (for drafting)"],
    disallowed_tools: [
      "social media APIs (no auto-posting)", "client PII",
      "broker APIs", "Oracle VM",
    ],
    human_approval_required: ["All content drafts before publication"],
    implementation: "workflows/ai_workforce/content_worker/ (stub — pending implementation)",
    status: "stub",
  },

  // ── 6. CRMCopilotWorker ─────────────────────────────────────────────────────
  crm_copilot_worker: {
    id: "crm_copilot_worker",
    name: "CRM Copilot Worker",
    mission: "Analyze CRM automation research and generate actionable GoHighLevel/workflow improvement suggestions for the Nexus CRM stack.",
    audience: "internal (staff-facing)",
    primary_tasks: [
      "Load research_artifacts WHERE topic = 'crm_automation'",
      "Identify workflow gaps and automation opportunities",
      "Generate GHL pipeline improvement suggestions",
      "Draft Zapier/Make.com workflow templates (no auto-execution)",
      "Suggest lead response SLA improvements",
    ],
    input_sources: ["research_artifacts (crm_automation topic)", "business_opportunities"],
    output_tables: ["research_briefs", "crm_suggestions (future table)"],
    allowed_tools: ["Supabase REST API", "OpenClaw (for suggestion drafting)"],
    disallowed_tools: [
      "CRM write access without human approval", "client PII",
      "auto-executing workflows", "broker APIs", "Oracle VM",
    ],
    human_approval_required: ["CRM workflow changes before implementation"],
    implementation: "workflows/ai_workforce/crm_copilot_worker/ (stub — pending implementation)",
    status: "stub",
  },

  // ── 7. ClientPortalAssistantWorker ──────────────────────────────────────────
  client_portal_assistant: {
    id: "client_portal_assistant",
    name: "Client Portal Assistant",
    mission: "Answer client questions using the Nexus research knowledge base. Scoped to approved content only — no raw data exposure.",
    audience: "client-facing (via goclearonline.cc portal)",
    primary_tasks: [
      "Respond to client questions about credit repair, grants, business opportunities",
      "Retrieve approved research_briefs relevant to client query",
      "Generate plain-language explanations from research content",
      "Escalate to human staff for sensitive or account-specific questions",
    ],
    input_sources: ["research_briefs", "grant_opportunities", "business_opportunities"],
    output_tables: ["portal_responses (future table — Oracle side)"],
    allowed_tools: ["Supabase REST API (read-only, approved tables only)"],
    disallowed_tools: [
      "raw research_artifacts content unfiltered",
      "client account records", "billing data", "credit reports",
      "research_claims (too raw for clients)", "broker APIs",
      "Oracle admin actions",
    ],
    human_approval_required: ["Any client-facing response involving account-specific advice"],
    implementation: "TBD — Oracle-side integration (Windows machine scope)",
    status: "planned",
  },

  // ── 8. TradingResearchWorker ────────────────────────────────────────────────
  trading_research_worker: {
    id: "trading_research_worker",
    name: "Trading Research Worker",
    mission: "Scan trading research artifacts and generate educational strategy proposals for human review. NO live trading, NO broker connections.",
    audience: "internal (Ray review only)",
    primary_tasks: [
      "Load research_artifacts WHERE topic = 'trading'",
      "Extract strategy patterns, risk frameworks, session timing",
      "Generate strategy proposal drafts for human review",
      "Write proposals to reviewed_signal_proposals for manual approval",
      "Generate trading research briefs and Telegram alerts",
    ],
    input_sources: ["research_artifacts (trading topic)"],
    output_tables: ["reviewed_signal_proposals", "research_briefs"],
    allowed_tools: ["Supabase REST API", "Telegram (internal alerts only)"],
    disallowed_tools: [
      "OANDA API", "broker execution APIs", "live signal generation",
      "automatic order placement", "Oracle VM", "client PII",
    ],
    human_approval_required: ["ALL strategy proposals — no automated execution ever"],
    implementation: "workflows/trading_analyst/ (partial) + stub extension",
    status: "partial",
  },

  // ── 9. RiskComplianceWorker ─────────────────────────────────────────────────
  risk_compliance_worker: {
    id: "risk_compliance_worker",
    name: "Risk / Compliance Worker",
    mission: "Review AI-generated proposals and research outputs for compliance issues, flag risks, and enforce Nexus safety rules.",
    audience: "internal",
    primary_tasks: [
      "Review trading strategy proposals against risk rules",
      "Flag compliance issues in credit repair content",
      "Enforce max daily loss, position sizing, and R:R rules",
      "Log all risk decisions to risk_decisions table",
      "Reject or escalate non-compliant proposals",
    ],
    input_sources: ["reviewed_signal_proposals", "research_briefs", "research_artifacts"],
    output_tables: ["risk_decisions", "approval_queue"],
    allowed_tools: ["Supabase REST API", "Telegram (alerts for high-risk flags)"],
    disallowed_tools: [
      "auto-approving trades", "broker APIs", "client PII",
      "bypassing risk rules", "Oracle VM",
    ],
    human_approval_required: ["Final trade execution — risk worker approves, human executes"],
    implementation: "workflows/risk_office/ (implemented)",
    status: "implemented",
  },

  // ── 10. OpsMonitoringWorker ─────────────────────────────────────────────────
  ops_monitoring_worker: {
    id: "ops_monitoring_worker",
    name: "Ops / Monitoring Worker",
    mission: "Monitor Nexus system health, track queue metrics, detect failures, and send daily operational summaries.",
    audience: "internal",
    primary_tasks: [
      "Check launchd service status (OpenClaw, signal router, dashboard, Telegram)",
      "Monitor Supabase artifact ingestion rate",
      "Detect stalled or failed research runs",
      "Count ai_jobs/ai_runs queue depth",
      "Send daily health summary via Telegram",
      "Alert on critical failures",
    ],
    input_sources: ["launchd service status", "Supabase table counts", "system logs"],
    output_tables: ["ops_metrics (future table)"],
    allowed_tools: ["Bash (read-only system commands)", "Supabase REST API (read-only)", "Telegram"],
    disallowed_tools: [
      "modifying launchd plists", "deploying code", "Oracle VM",
      "broker APIs", "client data",
    ],
    human_approval_required: ["Service restarts or config changes"],
    implementation: "workflows/ai_workforce/ops_monitoring_worker/ (stub — pending implementation)",
    status: "stub",
  },
});

// ── Helper: get role by ID ────────────────────────────────────────────────────
export function getRole(roleId) {
  return ROLES[roleId] ?? null;
}

export function listRoles() {
  return Object.values(ROLES);
}

export function listImplementedRoles() {
  return Object.values(ROLES).filter((r) => r.status === "implemented");
}
