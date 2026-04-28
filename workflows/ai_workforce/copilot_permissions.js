// ── Copilot Permissions ───────────────────────────────────────────────────────
// Defines the data access boundaries for both copilot roles.
// This is the authoritative source of truth for what each copilot
// is and is not permitted to read, write, or act on.
//
// These permissions complement the broader workforce_permissions.js by
// adding copilot-specific data scoping rules.
// ─────────────────────────────────────────────────────────────────────────────

// ── Allowed read tables per copilot role ─────────────────────────────────────

export const COPILOT_READ_TABLES = Object.freeze({

  // Client Portal Assistant — approved tables only
  portal: Object.freeze([
    "research_briefs",          // approved, curated summaries
    "grant_opportunities",      // funding info (score >= 30, status = new)
    "business_opportunities",   // business ideas (score >= 35, status = new)
    // DENIED: research_artifacts — too raw
    // DENIED: research_claims — too detailed
    // DENIED: research_clusters — internal categorization
    // DENIED: research_relationships — internal graph data
    // DENIED: reviewed_signal_proposals — trading data
    // DENIED: risk_decisions — internal
    // DENIED: approval_queue — internal
  ]),

  // Staff CRM Copilot — broader access than portal, still gated
  staff: Object.freeze([
    "research_artifacts",       // full artifact access for staff
    "research_claims",          // claim-level detail for staff
    "research_briefs",          // curated summaries
    "business_opportunities",   // business opportunity data
    "grant_opportunities",      // grant data
    // DENIED: research_relationships — internal graph
    // DENIED: reviewed_signal_proposals — trading only
    // DENIED: risk_decisions — risk/compliance only
    // DENIED: approval_queue — risk/compliance only
  ]),
});

// ── Approved write targets per copilot role ───────────────────────────────────

export const COPILOT_WRITE_TABLES = Object.freeze({
  // Portal assistant has no write access on the Mac Mini side.
  // Oracle VM (nexus-oracle-api) writes portal_responses — managed from Windows.
  portal: Object.freeze([]),

  // Staff copilot can write draft suggestions only (future table)
  staff: Object.freeze([
    "crm_suggestions",   // draft only — future table, pending Supabase setup
    "research_briefs",   // staff copilot can write briefs
  ]),
});

// ── Permanently blocked for all copilots ─────────────────────────────────────

export const COPILOT_BLOCKED_ACTIONS = Object.freeze([
  "access_client_credit_reports",
  "access_client_account_records",
  "access_billing_data",
  "mutate_crm_workflows_directly",
  "execute_automation_scripts",
  "post_to_social_media",
  "send_emails_to_clients",
  "access_broker_api",
  "access_oracle_vm_directly",
  "cross_tenant_data_read",
  "read_raw_research_artifacts_as_portal",
]);

// ── Row-level filtering rules (safety defaults) ───────────────────────────────

export const COPILOT_ROW_FILTERS = Object.freeze({
  portal: {
    research_briefs:        "limit=10&order=created_at.desc",
    grant_opportunities:    "status=eq.new&order=score.desc&limit=5",
    business_opportunities: "status=eq.new&order=score.desc&limit=5",
  },
  staff: {
    research_artifacts:     "order=created_at.desc&limit=20",
    research_claims:        "order=created_at.desc&limit=20",
    research_briefs:        "order=created_at.desc&limit=10",
    business_opportunities: "status=eq.new&order=score.desc&limit=10",
    grant_opportunities:    "status=eq.new&order=score.desc&limit=10",
  },
});

// ── Public helpers ────────────────────────────────────────────────────────────

/**
 * Check if a copilot role is allowed to read a specific table.
 * @param {"portal"|"staff"} role
 * @param {string} table
 * @returns {boolean}
 */
export function copilotCanRead(role, table) {
  return (COPILOT_READ_TABLES[role] ?? []).includes(table);
}

/**
 * Check if a copilot role is allowed to write to a specific table.
 * @param {"portal"|"staff"} role
 * @param {string} table
 * @returns {boolean}
 */
export function copilotCanWrite(role, table) {
  return (COPILOT_WRITE_TABLES[role] ?? []).includes(table);
}

/**
 * Get the safe default query filter for a table.
 * @param {"portal"|"staff"} role
 * @param {string} table
 * @returns {string} PostgREST query string fragment
 */
export function getCopilotRowFilter(role, table) {
  return COPILOT_ROW_FILTERS[role]?.[table] ?? "limit=10";
}

/**
 * Assert that an action is not in the blocked list.
 * @param {string} action
 * @throws {Error} if action is blocked
 */
export function assertCopilotAction(action) {
  if (COPILOT_BLOCKED_ACTIONS.includes(action)) {
    throw new Error(`[copilot-permissions] Action "${action}" is permanently blocked for all copilot roles.`);
  }
}
