// ── Workforce Registry ────────────────────────────────────────────────────────
// Maps role IDs to their implementation module paths.
// Used by workforce_dispatcher.js to lazy-import the correct worker.
//
// Status values:
//   "implemented" — module exists and is production-ready
//   "partial"     — module exists but some functions are stubs
//   "stub"        — module file is a placeholder, not yet runnable
//   "planned"     — no module yet; dispatcher will throw if dispatched
// ─────────────────────────────────────────────────────────────────────────────

export const REGISTRY = Object.freeze({

  research_worker: {
    id:     "research_worker",
    module: "../autonomous_research_supernode/research_orchestrator.js",
    runner: "runResearchOrchestrator",
    status: "implemented",
  },

  grant_worker: {
    id:     "grant_worker",
    module: "./grant_worker/grant_worker.js",
    runner: "runGrantWorker",
    status: "implemented",
  },

  opportunity_worker: {
    id:     "opportunity_worker",
    module: "./opportunity_worker/opportunity_worker.js",
    runner: "runOpportunityWorker",
    status: "implemented",
  },

  credit_worker: {
    id:     "credit_worker",
    module: "./credit_worker/credit_worker.js",
    runner: "runCreditWorker",
    status: "implemented",
  },

  content_worker: {
    id:     "content_worker",
    module: "./content_worker/content_worker.js",
    runner: "runContentWorker",
    status: "implemented",
  },

  crm_copilot_worker: {
    id:     "crm_copilot_worker",
    module: "./crm_copilot_worker/crm_copilot_worker.js",
    runner: "runCRMCopilotWorker",
    status: "implemented",
  },

  client_portal_assistant: {
    id:     "client_portal_assistant",
    module: "./client_portal_assistant/client_portal_assistant.js",
    runner: "runClientPortalAssistant",
    status: "planned",
  },

  trading_research_worker: {
    id:     "trading_research_worker",
    module: "./trading_research_worker/trading_research_worker.js",
    runner: "runTradingResearchWorker",
    status: "implemented",
  },

  risk_compliance_worker: {
    id:     "risk_compliance_worker",
    module: "./risk_compliance_worker/risk_compliance_worker.js",
    runner: "runRiskComplianceWorker",
    status: "implemented",
  },

  ops_monitoring_worker: {
    id:     "ops_monitoring_worker",
    module: "./ops_monitoring_worker/ops_monitoring_worker.js",
    runner: "runOpsMonitoringWorker",
    status: "implemented",
  },

  ops_control_worker: {
    id:     "ops_control_worker",
    module: "./ops_control_worker/ops_control_worker.js",
    runner: "runOpsControlWorker",
    status: "implemented",
  },

});

// ── Public helpers ────────────────────────────────────────────────────────────

/**
 * Look up a role's registry entry.
 * @param {string} roleId
 * @returns {Object|null}
 */
export function getRegistryEntry(roleId) {
  return REGISTRY[roleId] ?? null;
}

/**
 * Return all role IDs with a given status.
 * @param {string} status - "implemented" | "partial" | "stub" | "planned"
 * @returns {string[]}
 */
export function getRolesByStatus(status) {
  return Object.values(REGISTRY)
    .filter((r) => r.status === status)
    .map((r) => r.id);
}

/**
 * Return all runnable roles (implemented + partial).
 * @returns {string[]}
 */
export function getRunnableRoles() {
  return Object.values(REGISTRY)
    .filter((r) => r.status === "implemented" || r.status === "partial")
    .map((r) => r.id);
}
