// ── Copilot Request Router ─────────────────────────────────────────────────────
// Routes incoming copilot requests to the correct handler based on audience
// (staff vs client) and applies the knowledge-first resolution policy.
//
// This router is called from the Oracle VM backend (nexus-oracle-api) after
// authentication and tenant validation are confirmed. The backend passes the
// validated request here — this module never receives raw client HTTP calls.
//
// Request types:
//   "staff"   → Staff CRM Copilot Worker
//   "portal"  → Client Portal Assistant
//
// Knowledge-First Policy (applied by this router):
//   1. CRM / Supabase structured data lookup
//   2. research_briefs / grant_opportunities / business_opportunities
//   3. (future) ai_cache lookup
//   4. AI model (OpenClaw) as last resort — not yet wired in
//
// ─────────────────────────────────────────────────────────────────────────────

import "./env.js";
import { resolvePortalQuery } from "./client_portal_assistant/client_portal_assistant.js";

// ── Audience routing ──────────────────────────────────────────────────────────

const VALID_AUDIENCES = new Set(["staff", "portal"]);

/**
 * Route a copilot request to the appropriate handler.
 *
 * @param {Object} opts
 * @param {"staff"|"portal"} opts.audience  - Who is asking
 * @param {string} opts.query               - The question / prompt (max 500 chars)
 * @param {string} [opts.tenant_id]         - Tenant ID (validated by Oracle backend)
 * @param {string} [opts.staff_id]          - Staff user ID (for staff requests)
 * @param {string} [opts.job_type]          - Optional job type override
 * @param {boolean} [opts.dry_run=false]    - Validate + lookup only, no writes
 * @returns {Promise<Object>}               - Copilot response payload
 */
export async function routeCopilotRequest({
  audience,
  query,
  tenant_id,
  staff_id,
  job_type,
  dry_run = false,
} = {}) {
  // ── Validation ──────────────────────────────────────────────────────────────
  if (!VALID_AUDIENCES.has(audience)) {
    throw new Error(`[copilot-router] Invalid audience: "${audience}". Must be "staff" or "portal".`);
  }
  if (!query || typeof query !== "string" || !query.trim()) {
    throw new Error("[copilot-router] query must be a non-empty string.");
  }
  if (audience === "portal" && !tenant_id) {
    // Tenant ID is required for portal requests — enforce it
    throw new Error("[copilot-router] tenant_id is required for portal audience requests.");
  }

  const safeQuery = query.slice(0, 500).trim();

  console.log(`[copilot-router] Request — audience=${audience} tenant=${tenant_id ?? "staff"} query="${safeQuery.slice(0, 60)}..."`);

  // ── Route by audience ───────────────────────────────────────────────────────
  if (audience === "portal") {
    return resolvePortalQuery({ query: safeQuery, tenant_id, dry_run });
  }

  if (audience === "staff") {
    return resolveStaffQuery({ query: safeQuery, staff_id, job_type, dry_run });
  }
}

// ── Staff query resolver ──────────────────────────────────────────────────────
// Staff queries use a broader knowledge base than portal queries.
// Staff can see research_briefs, opportunities, grants, and CRM suggestions.

async function resolveStaffQuery({ query, staff_id, job_type, dry_run }) {
  // Knowledge-first policy for staff:
  // 1. Structured Supabase data lookup
  // 2. Research briefs
  // 3. Business / grant opportunities
  // 4. CRM suggestions (future)
  // 5. AI model last resort

  const intent = classifyStaffIntent(query);

  if (dry_run) {
    return {
      audience: "staff",
      intent,
      query,
      dry_run: true,
      response: null,
      knowledge_used: [],
    };
  }

  const knowledge = await loadStaffKnowledge(intent, query);

  return buildStaffResponse({ intent, query, knowledge, staff_id });
}

// Staff intent classification (broader than portal)
const STAFF_INTENT_PATTERNS = [
  { intent: "grant_summary",      patterns: [/grant/i, /funding/i, /sba\b/i] },
  { intent: "opportunity_summary", patterns: [/opportunity/i, /business\s+idea/i, /niche/i] },
  { intent: "crm_insight",        patterns: [/crm/i, /workflow/i, /gohighlevel/i, /automation/i, /pipeline/i, /follow.?up/i] },
  { intent: "credit_research",    patterns: [/credit/i, /dispute/i, /fcra/i, /tradeline/i] },
  { intent: "trading_research",   patterns: [/trading/i, /strategy/i, /signal/i, /market/i] },
];

function classifyStaffIntent(query) {
  const q = query.toLowerCase();
  for (const { intent, patterns } of STAFF_INTENT_PATTERNS) {
    if (patterns.some((p) => p.test(q))) return intent;
  }
  return "general_research";
}

async function loadStaffKnowledge(intent, query) {
  const SUPABASE_URL = process.env.SUPABASE_URL;
  const SUPABASE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY ?? process.env.SUPABASE_KEY;

  async function get(path) {
    const res = await fetch(`${SUPABASE_URL}/rest/v1/${path}`, {
      headers: { apikey: SUPABASE_KEY, Authorization: `Bearer ${SUPABASE_KEY}` },
    });
    if (!res.ok) return [];
    return res.json();
  }

  try {
    if (intent === "grant_summary") {
      return get("grant_opportunities?status=eq.new&order=score.desc&limit=5&select=title,funding_amount,deadline,geography,score");
    }
    if (intent === "opportunity_summary") {
      return get("business_opportunities?status=eq.new&order=score.desc&limit=5&select=title,opportunity_type,niche,score,monetization_hint");
    }
    // For all other intents, use research_briefs
    return get("research_briefs?order=created_at.desc&limit=5&select=title,summary,topic");
  } catch {
    return [];
  }
}

function buildStaffResponse({ intent, query, knowledge, staff_id }) {
  if (!knowledge.length) {
    return {
      audience: "staff",
      intent,
      query,
      response_type: "empty",
      response: "No knowledge found for this query. The research pipeline may need to run first.",
      knowledge_used: [],
    };
  }

  return {
    audience: "staff",
    intent,
    query,
    response_type: "knowledge",
    response: knowledge
      .map((k) => `• ${k.title ?? k.summary?.slice(0, 100) ?? "item"}${k.score ? ` [score: ${k.score}]` : ""}`)
      .join("\n"),
    knowledge_used: knowledge.map((k) => k.title ?? "item"),
    knowledge_count: knowledge.length,
  };
}
