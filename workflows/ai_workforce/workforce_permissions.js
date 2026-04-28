// ── Workforce Permissions ─────────────────────────────────────────────────────
// Defines and enforces tool + data access boundaries for each AI employee.
// ─────────────────────────────────────────────────────────────────────────────

// ── Permission flags ──────────────────────────────────────────────────────────
export const PERM = Object.freeze({
  // Tool permissions
  BROWSER_RESEARCH:     "browser_research",
  TRANSCRIPT_INGEST:    "transcript_ingest",
  HERMES_INFERENCE:   "hermes_inference",
  TELEGRAM_ALERT:       "telegram_alert",
  SUPABASE_READ:        "supabase_read",
  SUPABASE_WRITE:       "supabase_write",
  BASH_READ_ONLY:       "bash_read_only",

  // Data permissions
  CRM_DATA_READ:        "crm_data_read",
  CRM_DATA_WRITE:       "crm_data_write",   // requires human approval
  CLIENT_PORTAL_READ:   "client_portal_read",
  CLIENT_PORTAL_WRITE:  "client_portal_write",
  CREDIT_REPORT_SCAN:   "credit_report_scan", // research content only — not raw reports
  TRADING_PROPOSALS:    "trading_proposals",

  // Protected (never granted to any AI employee)
  CLIENT_PII_DIRECT:    "client_pii_direct",        // BLOCKED
  BROKER_API:           "broker_api",               // BLOCKED
  ORACLE_SSH:           "oracle_ssh",               // BLOCKED
  BILLING_CONTROL:      "billing_control",          // BLOCKED
  SUPERADMIN:           "superadmin",               // BLOCKED
  LIVE_TRADE_EXECUTION: "live_trade_execution",     // BLOCKED
  AUTO_PUBLISH_CONTENT: "auto_publish_content",     // BLOCKED
  AUTO_EXECUTE_CRM:     "auto_execute_crm",         // BLOCKED
});

// ── Role permission grants ────────────────────────────────────────────────────
const ROLE_PERMISSIONS = Object.freeze({
  research_worker: new Set([
    PERM.BROWSER_RESEARCH,
    PERM.TRANSCRIPT_INGEST,
    PERM.HERMES_INFERENCE,
    PERM.TELEGRAM_ALERT,
    PERM.SUPABASE_READ,
    PERM.SUPABASE_WRITE,
  ]),

  grant_worker: new Set([
    PERM.SUPABASE_READ,
    PERM.SUPABASE_WRITE,
    PERM.TELEGRAM_ALERT,
  ]),

  opportunity_worker: new Set([
    PERM.SUPABASE_READ,
    PERM.SUPABASE_WRITE,
    PERM.TELEGRAM_ALERT,
  ]),

  credit_worker: new Set([
    PERM.SUPABASE_READ,
    PERM.SUPABASE_WRITE,  // writes drafts only
    PERM.TELEGRAM_ALERT,
    PERM.CREDIT_REPORT_SCAN,  // research content only
  ]),

  content_worker: new Set([
    PERM.SUPABASE_READ,
    PERM.SUPABASE_WRITE,  // writes drafts only
    PERM.HERMES_INFERENCE,
  ]),

  crm_copilot_worker: new Set([
    PERM.SUPABASE_READ,
    PERM.SUPABASE_WRITE,  // writes suggestions/drafts only
    PERM.HERMES_INFERENCE,
    PERM.CRM_DATA_READ,
  ]),

  client_portal_assistant: new Set([
    PERM.SUPABASE_READ,   // approved tables only
    PERM.CLIENT_PORTAL_READ,
    PERM.CLIENT_PORTAL_WRITE,
  ]),

  trading_research_worker: new Set([
    PERM.SUPABASE_READ,
    PERM.SUPABASE_WRITE,  // writes proposals only
    PERM.TELEGRAM_ALERT,
    PERM.TRADING_PROPOSALS,
  ]),

  risk_compliance_worker: new Set([
    PERM.SUPABASE_READ,
    PERM.SUPABASE_WRITE,
    PERM.TELEGRAM_ALERT,
  ]),

  ops_monitoring_worker: new Set([
    PERM.SUPABASE_READ,
    PERM.BASH_READ_ONLY,
    PERM.TELEGRAM_ALERT,
  ]),
});

// ── Permanently blocked permissions (no role may ever have these) ─────────────
const BLOCKED_PERMS = new Set([
  PERM.CLIENT_PII_DIRECT,
  PERM.BROKER_API,
  PERM.ORACLE_SSH,
  PERM.BILLING_CONTROL,
  PERM.SUPERADMIN,
  PERM.LIVE_TRADE_EXECUTION,
  PERM.AUTO_PUBLISH_CONTENT,
  PERM.AUTO_EXECUTE_CRM,
]);

// ── Public API ────────────────────────────────────────────────────────────────

/**
 * Check if a role has a specific permission.
 * @param {string} roleId
 * @param {string} permission - PERM constant
 * @returns {boolean}
 */
export function hasPermission(roleId, permission) {
  if (BLOCKED_PERMS.has(permission)) return false; // always blocked
  return ROLE_PERMISSIONS[roleId]?.has(permission) ?? false;
}

/**
 * Get all permissions for a role (excluding blocked).
 * @param {string} roleId
 * @returns {string[]}
 */
export function getRolePermissions(roleId) {
  return [...(ROLE_PERMISSIONS[roleId] ?? [])];
}

/**
 * Assert that a role has permission. Throws if not.
 * @param {string} roleId
 * @param {string} permission
 * @throws {Error} If permission denied
 */
export function assertPermission(roleId, permission) {
  if (BLOCKED_PERMS.has(permission)) {
    throw new Error(`[permissions] BLOCKED: ${permission} is permanently restricted for all AI employees.`);
  }
  if (!hasPermission(roleId, permission)) {
    throw new Error(`[permissions] DENIED: Role '${roleId}' does not have permission '${permission}'.`);
  }
}

/**
 * Check all permissions for a job payload. Returns { allowed, denied }.
 * @param {string} roleId
 * @param {string[]} requiredPerms - Array of PERM constants
 * @returns {{ allowed: boolean, denied: string[] }}
 */
export function checkJobPermissions(roleId, requiredPerms) {
  const denied = requiredPerms.filter((p) => !hasPermission(roleId, p));
  return { allowed: denied.length === 0, denied };
}
