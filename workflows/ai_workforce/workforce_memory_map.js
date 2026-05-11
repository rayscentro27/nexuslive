// ── Workforce Memory Map ──────────────────────────────────────────────────────
// Defines which Supabase tables each AI employee role may read and/or write.
// "draft" = writes staging/draft records only, requires human promotion.
// ─────────────────────────────────────────────────────────────────────────────

export const ACCESS = Object.freeze({
  READ:  "read",
  WRITE: "write",
  DRAFT: "draft",  // writes to draft/staging — not production records
  NONE:  "none",
});

// ── Table access map ──────────────────────────────────────────────────────────
// Format: { [tableId]: { [roleId]: ACCESS level } }

export const MEMORY_MAP = Object.freeze({

  // Core research tables
  research_artifacts: {
    research_worker:         ACCESS.WRITE,
    grant_worker:            ACCESS.READ,
    opportunity_worker:      ACCESS.READ,
    credit_worker:           ACCESS.READ,
    content_worker:          ACCESS.READ,
    crm_copilot_worker:      ACCESS.READ,
    client_portal_assistant: ACCESS.NONE,   // too raw for clients
    trading_research_worker: ACCESS.READ,
    risk_compliance_worker:  ACCESS.READ,
    ops_monitoring_worker:   ACCESS.READ,   // counts only
  },

  research_claims: {
    research_worker:         ACCESS.WRITE,
    grant_worker:            ACCESS.READ,
    opportunity_worker:      ACCESS.READ,
    credit_worker:           ACCESS.READ,
    content_worker:          ACCESS.NONE,
    crm_copilot_worker:      ACCESS.READ,
    client_portal_assistant: ACCESS.NONE,
    trading_research_worker: ACCESS.READ,
    risk_compliance_worker:  ACCESS.READ,
    ops_monitoring_worker:   ACCESS.READ,   // counts only
  },

  research_briefs: {
    research_worker:         ACCESS.WRITE,
    grant_worker:            ACCESS.WRITE,
    opportunity_worker:      ACCESS.WRITE,
    credit_worker:           ACCESS.DRAFT,
    content_worker:          ACCESS.READ,
    crm_copilot_worker:      ACCESS.READ,
    client_portal_assistant: ACCESS.READ,   // approved briefs only
    trading_research_worker: ACCESS.WRITE,
    risk_compliance_worker:  ACCESS.READ,
    ops_monitoring_worker:   ACCESS.READ,
  },

  research_clusters: {
    research_worker:         ACCESS.WRITE,
    grant_worker:            ACCESS.READ,
    opportunity_worker:      ACCESS.READ,
    credit_worker:           ACCESS.READ,
    content_worker:          ACCESS.READ,
    crm_copilot_worker:      ACCESS.READ,
    client_portal_assistant: ACCESS.NONE,
    trading_research_worker: ACCESS.READ,
    risk_compliance_worker:  ACCESS.NONE,
    ops_monitoring_worker:   ACCESS.NONE,
  },

  research_relationships: {
    research_worker:         ACCESS.WRITE,
    grant_worker:            ACCESS.READ,
    opportunity_worker:      ACCESS.READ,
    credit_worker:           ACCESS.NONE,
    content_worker:          ACCESS.NONE,
    crm_copilot_worker:      ACCESS.NONE,
    client_portal_assistant: ACCESS.NONE,
    trading_research_worker: ACCESS.READ,
    risk_compliance_worker:  ACCESS.NONE,
    ops_monitoring_worker:   ACCESS.NONE,
  },

  // Research memory (Nexus Brain)
  research: {
    research_worker:         ACCESS.WRITE,   // memory_enricher writes here
    grant_worker:            ACCESS.NONE,
    opportunity_worker:      ACCESS.NONE,
    credit_worker:           ACCESS.NONE,
    content_worker:          ACCESS.READ,
    crm_copilot_worker:      ACCESS.NONE,
    client_portal_assistant: ACCESS.NONE,
    trading_research_worker: ACCESS.NONE,
    risk_compliance_worker:  ACCESS.NONE,
    ops_monitoring_worker:   ACCESS.NONE,
  },

  // Specialized worker output tables
  grant_opportunities: {
    research_worker:         ACCESS.NONE,
    grant_worker:            ACCESS.WRITE,
    opportunity_worker:      ACCESS.NONE,
    credit_worker:           ACCESS.NONE,
    content_worker:          ACCESS.READ,
    crm_copilot_worker:      ACCESS.NONE,
    client_portal_assistant: ACCESS.READ,
    trading_research_worker: ACCESS.NONE,
    risk_compliance_worker:  ACCESS.NONE,
    ops_monitoring_worker:   ACCESS.READ,
  },

  business_opportunities: {
    research_worker:         ACCESS.NONE,
    grant_worker:            ACCESS.NONE,
    opportunity_worker:      ACCESS.WRITE,
    credit_worker:           ACCESS.NONE,
    content_worker:          ACCESS.READ,
    crm_copilot_worker:      ACCESS.READ,
    client_portal_assistant: ACCESS.READ,
    trading_research_worker: ACCESS.NONE,
    risk_compliance_worker:  ACCESS.NONE,
    ops_monitoring_worker:   ACCESS.READ,
  },

  // Trading pipeline tables
  reviewed_signal_proposals: {
    research_worker:         ACCESS.NONE,
    grant_worker:            ACCESS.NONE,
    opportunity_worker:      ACCESS.NONE,
    credit_worker:           ACCESS.NONE,
    content_worker:          ACCESS.NONE,
    crm_copilot_worker:      ACCESS.NONE,
    client_portal_assistant: ACCESS.NONE,
    trading_research_worker: ACCESS.DRAFT,  // writes proposals for human review
    risk_compliance_worker:  ACCESS.READ,
    ops_monitoring_worker:   ACCESS.READ,   // counts only
  },

  approval_queue: {
    research_worker:         ACCESS.NONE,
    grant_worker:            ACCESS.NONE,
    opportunity_worker:      ACCESS.NONE,
    credit_worker:           ACCESS.NONE,
    content_worker:          ACCESS.NONE,
    crm_copilot_worker:      ACCESS.NONE,
    client_portal_assistant: ACCESS.NONE,
    trading_research_worker: ACCESS.NONE,
    risk_compliance_worker:  ACCESS.WRITE,  // writes approvals/rejections
    ops_monitoring_worker:   ACCESS.READ,
  },

  risk_decisions: {
    research_worker:         ACCESS.NONE,
    grant_worker:            ACCESS.NONE,
    opportunity_worker:      ACCESS.NONE,
    credit_worker:           ACCESS.NONE,
    content_worker:          ACCESS.NONE,
    crm_copilot_worker:      ACCESS.NONE,
    client_portal_assistant: ACCESS.NONE,
    trading_research_worker: ACCESS.READ,
    risk_compliance_worker:  ACCESS.WRITE,
    ops_monitoring_worker:   ACCESS.READ,
  },
});

// ── Public helpers ────────────────────────────────────────────────────────────

/**
 * Check if a role can access a table at the given access level.
 * @param {string} roleId
 * @param {string} table
 * @param {string} accessLevel - ACCESS constant
 * @returns {boolean}
 */
export function canAccess(roleId, table, accessLevel) {
  const level = MEMORY_MAP[table]?.[roleId];
  if (!level || level === ACCESS.NONE) return false;
  if (accessLevel === ACCESS.READ) return true; // all non-NONE levels allow read
  if (accessLevel === ACCESS.WRITE) return level === ACCESS.WRITE;
  if (accessLevel === ACCESS.DRAFT) return level === ACCESS.DRAFT || level === ACCESS.WRITE;
  return false;
}

/**
 * Get all tables a role can read.
 * @param {string} roleId
 * @returns {string[]}
 */
export function getReadableTables(roleId) {
  return Object.entries(MEMORY_MAP)
    .filter(([, roleMap]) => roleMap[roleId] && roleMap[roleId] !== ACCESS.NONE)
    .map(([table]) => table);
}

/**
 * Get all tables a role can write to.
 * @param {string} roleId
 * @returns {string[]}
 */
export function getWritableTables(roleId) {
  return Object.entries(MEMORY_MAP)
    .filter(([, roleMap]) => [ACCESS.WRITE, ACCESS.DRAFT].includes(roleMap[roleId]))
    .map(([table]) => table);
}
