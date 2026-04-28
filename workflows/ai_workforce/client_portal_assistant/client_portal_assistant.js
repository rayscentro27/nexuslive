// ── Client Portal Assistant ───────────────────────────────────────────────────
// Answers client questions using the Nexus research knowledge base.
// Scoped to approved tables only — no raw artifact exposure to clients.
//
// This module runs on the Mac Mini and provides the AI-layer logic.
// The actual HTTP endpoint that serves clients lives on the Oracle VM
// (nexus-oracle-api) — managed from the Windows machine.
//
// Mac Mini scope:
//   - Research knowledge lookup from approved Supabase tables
//   - Response generation (heuristic matching, no raw data exposure)
//   - Knowledge-first resolution before escalating to AI model
//
// Oracle VM scope (Windows machine):
//   - HTTP endpoint /api/copilot/portal-query
//   - Auth / RBAC / tenant validation
//   - Rate limiting and abuse protection
//   - portal_responses table writes
//
// HARD LIMITS:
//   - No access to research_artifacts or research_claims (too raw for clients)
//   - No access to client account records, credit reports, or billing data
//   - No cross-tenant data access
//   - Account-specific advice escalated to human staff
//   - All outputs are DRAFT responses — require Oracle-side approval before delivery
//
// Usage (programmatic from Oracle VM backend):
//   import { resolvePortalQuery } from "./client_portal_assistant.js";
//   const response = await resolvePortalQuery({ query, context });
// ─────────────────────────────────────────────────────────────────────────────

import "../env.js";

const SUPABASE_URL = process.env.SUPABASE_URL;
const SUPABASE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY ?? process.env.SUPABASE_KEY;

// ── Approved tables for client portal access ──────────────────────────────────
// These are the ONLY tables this worker may query.
const APPROVED_READ_TABLES = Object.freeze([
  "research_briefs",
  "grant_opportunities",
  "business_opportunities",
]);

// ── Supabase helpers ──────────────────────────────────────────────────────────

async function supabaseGet(table, queryString) {
  if (!APPROVED_READ_TABLES.includes(table)) {
    throw new Error(`[portal-assistant] Access denied: table "${table}" is not in the approved read list.`);
  }
  const path = `${table}?${queryString}`;
  const res = await fetch(`${SUPABASE_URL}/rest/v1/${path}`, {
    headers: {
      apikey: SUPABASE_KEY,
      Authorization: `Bearer ${SUPABASE_KEY}`,
      "Content-Type": "application/json",
    },
  });
  if (!res.ok) throw new Error(`Supabase GET ${path}: ${res.status} ${await res.text()}`);
  return res.json();
}

// ── Query intent classification ───────────────────────────────────────────────

const INTENT_PATTERNS = [
  { intent: "grant_lookup",      patterns: [/grant/i, /funding/i, /apply\s+for/i, /sbir|sba\b/i, /small\s+business\s+fund/i] },
  { intent: "business_ideas",    patterns: [/business\s+idea/i, /opportunity/i, /start\s+a\s+business/i, /side\s+hustle/i, /make\s+money/i] },
  { intent: "credit_guidance",   patterns: [/credit/i, /dispute/i, /repair\s+my/i, /boost\s+my\s+score/i, /derogatory/i] },
  { intent: "crm_guidance",      patterns: [/crm/i, /gohighlevel/i, /workflow/i, /automation/i, /follow.?up/i] },
  { intent: "general_research",  patterns: [/research/i, /learn\s+about/i, /explain/i, /what\s+is/i, /how\s+to/i] },
];

function classifyIntent(query) {
  const q = query.toLowerCase();
  for (const { intent, patterns } of INTENT_PATTERNS) {
    if (patterns.some((p) => p.test(q))) return intent;
  }
  return "general_research";
}

// ── Escalation detection ──────────────────────────────────────────────────────

const ESCALATION_PATTERNS = [
  /my\s+account/i,
  /my\s+credit\s+report/i,
  /my\s+score/i,
  /dispute\s+my/i,
  /my\s+payment/i,
  /billing/i,
  /cancel\s+my/i,
  /refund/i,
  /login\s+issue/i,
  /my\s+case/i,
  /my\s+file/i,
];

function requiresEscalation(query) {
  return ESCALATION_PATTERNS.some((p) => p.test(query));
}

// ── Knowledge lookup functions ────────────────────────────────────────────────

async function lookupGrantBriefs(query) {
  try {
    const rows = await supabaseGet(
      "grant_opportunities",
      "status=eq.new&order=score.desc&limit=3&select=title,description,funding_amount,deadline,geography"
    );
    return rows;
  } catch { return []; }
}

async function lookupBusinessOpportunities(query) {
  try {
    const rows = await supabaseGet(
      "business_opportunities",
      "status=eq.new&order=score.desc&limit=3&select=title,description,opportunity_type,niche,monetization_hint"
    );
    return rows;
  } catch { return []; }
}

async function lookupResearchBriefs(query) {
  try {
    const rows = await supabaseGet(
      "research_briefs",
      "order=created_at.desc&limit=5&select=title,summary,topic"
    );
    return rows;
  } catch { return []; }
}

// ── Response builder ──────────────────────────────────────────────────────────

function buildPortalResponse({ intent, query, knowledge, escalate }) {
  if (escalate) {
    return {
      intent,
      query,
      response_type: "escalation",
      response: "This question relates to your personal account details. A Nexus team member will follow up with you directly.",
      knowledge_used: [],
      requires_human_review: true,
      escalated: true,
    };
  }

  if (!knowledge.length) {
    return {
      intent,
      query,
      response_type: "empty",
      response: "I don't have specific information on this topic yet. Our research team is continuously adding new content — please check back soon or contact our team directly.",
      knowledge_used: [],
      requires_human_review: true,
      escalated: false,
    };
  }

  // Build a safe summary from knowledge (no raw data exposure)
  const summaryLines = knowledge.slice(0, 3).map((item) => {
    if (item.funding_amount) return `${item.title} — ${item.funding_amount}${item.deadline ? ` (Deadline: ${item.deadline})` : ""}`;
    if (item.opportunity_type) return `${item.title} (${item.niche ?? item.opportunity_type})`;
    return item.title ?? item.summary?.slice(0, 100) ?? "Research item";
  });

  return {
    intent,
    query,
    response_type: "knowledge",
    response: `Here's what we found related to your question:\n\n${summaryLines.map((l) => `• ${l}`).join("\n")}\n\nFor personalized guidance, please contact our team.`,
    knowledge_used: knowledge.map((k) => k.title ?? "item"),
    requires_human_review: true,
    escalated: false,
  };
}

// ── Public resolver ───────────────────────────────────────────────────────────

/**
 * Resolve a client portal query using the Nexus knowledge base.
 *
 * This function:
 * 1. Classifies the query intent
 * 2. Checks if escalation to human staff is required
 * 3. Looks up approved knowledge tables (NO raw artifacts)
 * 4. Returns a safe draft response for Oracle-side review and delivery
 *
 * @param {Object} opts
 * @param {string} opts.query - The client's question (max 500 chars)
 * @param {string} [opts.tenant_id] - Tenant ID (from Oracle auth layer — not used here)
 * @param {boolean} [opts.dry_run=false] - Return result without external calls
 * @returns {Promise<Object>} Draft response object
 */
export async function resolvePortalQuery({ query, tenant_id, dry_run = false } = {}) {
  if (!query || typeof query !== "string") {
    throw new Error("[portal-assistant] query must be a non-empty string.");
  }

  // Sanitize: truncate oversized queries
  const safeQuery = query.slice(0, 500);

  const intent = classifyIntent(safeQuery);
  const escalate = requiresEscalation(safeQuery);

  if (dry_run) {
    return {
      intent,
      escalate,
      query: safeQuery,
      dry_run: true,
      response: null,
      knowledge_used: [],
    };
  }

  // Escalation short-circuit — no knowledge lookup needed
  if (escalate) {
    return buildPortalResponse({ intent, query: safeQuery, knowledge: [], escalate: true });
  }

  // Knowledge-first lookup by intent
  let knowledge = [];
  if (intent === "grant_lookup") {
    knowledge = await lookupGrantBriefs(safeQuery);
  } else if (intent === "business_ideas") {
    knowledge = await lookupBusinessOpportunities(safeQuery);
  } else {
    knowledge = await lookupResearchBriefs(safeQuery);
  }

  return buildPortalResponse({ intent, query: safeQuery, knowledge, escalate: false });
}

// ── CLI test mode ─────────────────────────────────────────────────────────────

const isDirect = process.argv[1]?.endsWith("client_portal_assistant.js");
if (isDirect) {
  const query = process.argv.slice(2).join(" ") || "What grants are available for small businesses?";
  console.log(`\n[portal-assistant] Test query: "${query}"\n`);

  resolvePortalQuery({ query, dry_run: process.argv.includes("--dry-run") })
    .then((result) => {
      console.log(JSON.stringify(result, null, 2));
    })
    .catch((err) => {
      console.error(`[portal-assistant] Error: ${err.message}`);
      process.exit(1);
    });
}
