// ── Workforce Dispatcher ──────────────────────────────────────────────────────
// Routes incoming job payloads to the correct AI employee role.
// Enforces permission checks, approval gates, and memory map access rules
// before delegating to the worker module.
//
// Usage (direct):
//   node workforce_dispatcher.js --role grant_worker --job grant_scan --dry-run
//
// Usage (programmatic):
//   import { dispatch } from "./workforce_dispatcher.js";
//   await dispatch({ role: "grant_worker", job: "grant_scan", payload: { since_days: 7 } });
//
// RESEARCH ONLY — no live trading, no broker connections.
// ─────────────────────────────────────────────────────────────────────────────

import "./env.js";
import { REGISTRY, getRegistryEntry } from "./workforce_registry.js";
import { ROLES } from "./workforce_roles.js";
import { JOB_TYPE, ROLE_JOB_TYPES, APPROVAL_REQUIRED_JOBS } from "./workforce_job_types.js";
import { hasPermission, PERM } from "./workforce_permissions.js";

// ── Job → required permissions map ───────────────────────────────────────────

const JOB_PERMISSION_REQUIREMENTS = Object.freeze({
  [JOB_TYPE.RESEARCH_TRANSCRIPT]:       [PERM.TRANSCRIPT_INGEST, PERM.SUPABASE_READ, PERM.SUPABASE_WRITE],
  [JOB_TYPE.RESEARCH_BROWSER]:          [PERM.BROWSER_RESEARCH, PERM.SUPABASE_READ, PERM.SUPABASE_WRITE],
  [JOB_TYPE.RESEARCH_MANUAL]:           [PERM.SUPABASE_READ, PERM.SUPABASE_WRITE],
  [JOB_TYPE.RESEARCH_ALL]:              [PERM.SUPABASE_READ, PERM.SUPABASE_WRITE],

  [JOB_TYPE.GRANT_SCAN]:                [PERM.SUPABASE_READ, PERM.SUPABASE_WRITE],
  [JOB_TYPE.GRANT_NORMALIZATION]:       [PERM.SUPABASE_READ],
  [JOB_TYPE.GRANT_BRIEF]:               [PERM.SUPABASE_READ, PERM.TELEGRAM_ALERT],

  [JOB_TYPE.BUSINESS_SCAN]:             [PERM.SUPABASE_READ, PERM.SUPABASE_WRITE],
  [JOB_TYPE.OPPORTUNITY_SCAN]:          [PERM.SUPABASE_READ, PERM.SUPABASE_WRITE],
  [JOB_TYPE.OPPORTUNITY_BRIEF]:         [PERM.SUPABASE_READ, PERM.TELEGRAM_ALERT],

  [JOB_TYPE.CREDIT_ARTIFACT_SCAN]:      [PERM.SUPABASE_READ, PERM.CREDIT_REPORT_SCAN],
  [JOB_TYPE.CREDIT_DISPUTE_DRAFT]:      [PERM.SUPABASE_READ, PERM.SUPABASE_WRITE],
  [JOB_TYPE.CREDIT_POLICY_REVIEW]:      [PERM.SUPABASE_READ, PERM.CREDIT_REPORT_SCAN],

  [JOB_TYPE.CONTENT_BRIEF_GENERATE]:    [PERM.SUPABASE_READ, PERM.SUPABASE_WRITE, PERM.HERMES_INFERENCE],
  [JOB_TYPE.CONTENT_SOCIAL_DRAFT]:      [PERM.SUPABASE_READ, PERM.SUPABASE_WRITE, PERM.HERMES_INFERENCE],
  [JOB_TYPE.CONTENT_NEWSLETTER_DRAFT]:  [PERM.SUPABASE_READ, PERM.SUPABASE_WRITE, PERM.HERMES_INFERENCE],

  [JOB_TYPE.CRM_WORKFLOW_SCAN]:         [PERM.SUPABASE_READ, PERM.CRM_DATA_READ],
  [JOB_TYPE.CRM_SUGGESTION_GENERATE]:   [PERM.SUPABASE_READ, PERM.SUPABASE_WRITE, PERM.CRM_DATA_READ, PERM.HERMES_INFERENCE],
  [JOB_TYPE.CRM_AUDIT_RUN]:             [PERM.SUPABASE_READ, PERM.CRM_DATA_READ],

  [JOB_TYPE.PORTAL_QUERY_RESPOND]:      [PERM.SUPABASE_READ, PERM.CLIENT_PORTAL_READ, PERM.CLIENT_PORTAL_WRITE],
  [JOB_TYPE.PORTAL_RESEARCH_LOOKUP]:    [PERM.SUPABASE_READ, PERM.CLIENT_PORTAL_READ],

  [JOB_TYPE.TRADING_ARTIFACT_SCAN]:     [PERM.SUPABASE_READ, PERM.TRADING_PROPOSALS],
  [JOB_TYPE.TRADING_STRATEGY_DRAFT]:    [PERM.SUPABASE_READ, PERM.SUPABASE_WRITE, PERM.TRADING_PROPOSALS],
  [JOB_TYPE.TRADING_BRIEF_GENERATE]:    [PERM.SUPABASE_READ, PERM.TELEGRAM_ALERT, PERM.TRADING_PROPOSALS],

  [JOB_TYPE.RISK_PROPOSAL_REVIEW]:      [PERM.SUPABASE_READ, PERM.SUPABASE_WRITE],
  [JOB_TYPE.COMPLIANCE_FLAG_SCAN]:      [PERM.SUPABASE_READ],
  [JOB_TYPE.RISK_BRIEF_GENERATE]:       [PERM.SUPABASE_READ, PERM.TELEGRAM_ALERT],

  [JOB_TYPE.OPS_HEALTH_CHECK]:          [PERM.SUPABASE_READ, PERM.BASH_READ_ONLY],
  [JOB_TYPE.OPS_QUEUE_METRICS]:         [PERM.SUPABASE_READ],
  [JOB_TYPE.OPS_ALERT_ON_FAILURE]:      [PERM.TELEGRAM_ALERT],
  [JOB_TYPE.OPS_DAILY_SUMMARY]:         [PERM.SUPABASE_READ, PERM.TELEGRAM_ALERT],
});

// ── Dispatcher core ───────────────────────────────────────────────────────────

/**
 * Validate the dispatch request before running the worker.
 * @param {string} roleId
 * @param {string} jobType
 * @param {boolean} requireApproval - if true, hard-block approval-required jobs
 * @throws {Error} with descriptive message on any validation failure
 */
function validateDispatch(roleId, jobType, requireApproval = true) {
  // 1. Role must exist
  const entry = getRegistryEntry(roleId);
  if (!entry) throw new Error(`[dispatcher] Unknown role: "${roleId}"`);

  // 2. Role must be runnable
  if (entry.status === "planned") {
    throw new Error(`[dispatcher] Role "${roleId}" is not yet implemented (status: planned).`);
  }
  if (entry.status === "stub") {
    throw new Error(`[dispatcher] Role "${roleId}" is a stub — module not yet runnable.`);
  }

  // 3. Job must be allowed for this role
  const allowedJobs = ROLE_JOB_TYPES[roleId] ?? [];
  if (!allowedJobs.includes(jobType)) {
    throw new Error(
      `[dispatcher] Job "${jobType}" is not permitted for role "${roleId}". ` +
      `Allowed: ${allowedJobs.join(", ")}`
    );
  }

  // 4. Approval gate — block human-approval-required jobs unless explicitly bypassed
  if (requireApproval && APPROVAL_REQUIRED_JOBS.has(jobType)) {
    throw new Error(
      `[dispatcher] Job "${jobType}" requires human approval before execution. ` +
      `Pass { skipApprovalGate: true } only after human sign-off.`
    );
  }

  // 5. Permission check
  const requiredPerms = JOB_PERMISSION_REQUIREMENTS[jobType] ?? [];
  const missing = requiredPerms.filter((p) => !hasPermission(roleId, p));
  if (missing.length) {
    throw new Error(
      `[dispatcher] Role "${roleId}" is missing permissions for job "${jobType}": ` +
      missing.join(", ")
    );
  }
}

/**
 * Dynamically import a worker module and invoke its runner function.
 * @param {Object} entry - Registry entry
 * @param {Object} payload - Job options/arguments passed to the runner
 * @returns {Promise<any>} - Whatever the runner returns
 */
async function invokeWorker(entry, payload) {
  // Dynamic import relative to this file's directory
  const { createRequire } = await import("module");
  const { fileURLToPath } = await import("url");
  const { dirname, resolve } = await import("path");

  const __dirname = dirname(fileURLToPath(import.meta.url));
  const modulePath = resolve(__dirname, entry.module);

  const mod = await import(modulePath);
  const runner = mod[entry.runner];

  if (typeof runner !== "function") {
    throw new Error(
      `[dispatcher] Module "${entry.module}" does not export "${entry.runner}". ` +
      `Check the registry entry for role "${entry.id}".`
    );
  }

  return runner(payload);
}

// ── Public dispatch function ──────────────────────────────────────────────────

/**
 * Dispatch a job to the appropriate AI employee.
 *
 * @param {Object} opts
 * @param {string} opts.role              - Role ID (e.g. "grant_worker")
 * @param {string} opts.job               - Job type (JOB_TYPE constant value)
 * @param {Object} [opts.payload={}]      - Arguments forwarded to the worker runner
 * @param {boolean} [opts.skipApprovalGate=false] - Skip human-approval gate (only after sign-off)
 * @param {boolean} [opts.dryRun=false]   - Validate only, do not invoke worker
 * @returns {Promise<Object>} - { role, job, result, elapsed_ms }
 */
export async function dispatch({
  role,
  job,
  payload = {},
  skipApprovalGate = false,
  dryRun = false,
} = {}) {
  const requireApproval = !skipApprovalGate;

  // Validate before doing any work
  validateDispatch(role, job, requireApproval);

  const entry = REGISTRY[role];
  const start = Date.now();

  if (dryRun) {
    console.log(`[dispatcher] DRY RUN — role="${role}" job="${job}" — validation passed.`);
    return { role, job, result: null, elapsed_ms: 0, dry_run: true };
  }

  console.log(`[dispatcher] Dispatching — role="${role}" job="${job}"`);

  try {
    const result = await invokeWorker(entry, { ...payload, dry_run: payload.dry_run ?? false });
    const elapsed_ms = Date.now() - start;
    console.log(`[dispatcher] Completed — role="${role}" job="${job}" elapsed=${elapsed_ms}ms`);
    return { role, job, result, elapsed_ms };
  } catch (err) {
    const elapsed_ms = Date.now() - start;
    console.error(`[dispatcher] Failed — role="${role}" job="${job}" elapsed=${elapsed_ms}ms — ${err.message}`);
    throw err;
  }
}

// ── CLI entry point ───────────────────────────────────────────────────────────

const args = process.argv.slice(2);

if (args.includes("--help")) {
  console.log([
    "Usage: node workforce_dispatcher.js --role <roleId> --job <jobType> [options]",
    "",
    "Options:",
    "  --role <id>         Role ID (e.g. grant_worker, opportunity_worker)",
    "  --job <type>        Job type (e.g. grant_scan, business_scan)",
    "  --dry-run           Validate only, do not invoke worker",
    "  --skip-approval     Bypass approval gate (use only after human sign-off)",
    "  --since <days>      Forwarded to worker: look back N days",
    "  --min-score <n>     Forwarded to worker: minimum score threshold",
    "  --quiet             Forwarded to worker: suppress verbose output",
    "  --list-roles        List all registered roles and their status",
    "  --list-jobs <role>  List allowed job types for a role",
    "  --help              Show this help",
  ].join("\n"));
  process.exit(0);
}

function getArg(flag, defaultVal) {
  const idx = args.indexOf(flag);
  return idx !== -1 ? args[idx + 1] : defaultVal;
}

const isDirect = process.argv[1]?.endsWith("workforce_dispatcher.js");

if (isDirect) {
  // List modes
  if (args.includes("--list-roles")) {
    console.log("\nRegistered Nexus AI Workforce Roles:\n");
    for (const entry of Object.values(REGISTRY)) {
      const role = ROLES[entry.id];
      const indicator = { implemented: "✅", partial: "🔶", stub: "🔸", planned: "⬜" }[entry.status] ?? "❓";
      console.log(`  ${indicator}  ${entry.id.padEnd(28)} [${entry.status}]`);
      if (role) console.log(`       ${role.mission}`);
    }
    console.log("");
    process.exit(0);
  }

  if (args.includes("--list-jobs")) {
    const roleId = getArg("--list-jobs", null);
    if (!roleId) { console.error("--list-jobs requires a role ID"); process.exit(1); }
    const jobs = ROLE_JOB_TYPES[roleId];
    if (!jobs) { console.error(`Unknown role: ${roleId}`); process.exit(1); }
    console.log(`\nAllowed job types for role "${roleId}":\n`);
    for (const j of jobs) {
      const needsApproval = APPROVAL_REQUIRED_JOBS.has(j) ? "  ⚠️  requires human approval" : "";
      console.log(`  ${j}${needsApproval}`);
    }
    console.log("");
    process.exit(0);
  }

  // Dispatch mode
  const role = getArg("--role", null);
  const job  = getArg("--job",  null);

  if (!role || !job) {
    console.error("[dispatcher] --role and --job are required. Run with --help for usage.");
    process.exit(1);
  }

  const since   = getArg("--since", "30");
  const minScore = getArg("--min-score", null);
  const dryRun  = args.includes("--dry-run");
  const quiet   = args.includes("--quiet");
  const skipApproval = args.includes("--skip-approval");

  const payload = {
    since_days: since === "all" ? null : parseInt(since, 10),
    dry_run: dryRun,
    quiet,
  };
  if (minScore) payload.min_score = parseInt(minScore, 10);

  dispatch({ role, job, payload, skipApprovalGate: skipApproval, dryRun }).catch((err) => {
    console.error(`[dispatcher] Fatal: ${err.message}`);
    if (process.env.DEBUG) console.error(err.stack);
    process.exit(1);
  });
}
