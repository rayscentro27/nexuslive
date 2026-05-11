// ── Opportunity Scoring ───────────────────────────────────────────────────────
// Assigns a priority score 0–100 to a normalized BusinessOpportunity.
//
// Score breakdown (max 100):
//   Recurring revenue potential : 25 pts
//   Low barrier to entry        : 20 pts
//   Proven demand / evidence    : 20 pts
//   Automation / AI leverage    : 15 pts
//   Source authority            : 10 pts
//   Novelty / timing            : 10 pts
// ─────────────────────────────────────────────────────────────────────────────

// ── Recurring revenue (0–25) ──────────────────────────────────────────────────
const RECURRING_KEYWORDS = [
  "recurring revenue", "subscription", "mrr", "arr", "retainer",
  "monthly fee", "recurring income", "saas", "membership",
];

function recurringRevenueScore(opp) {
  const text = `${opp.description} ${opp.evidence_summary} ${opp.monetization_hint}`.toLowerCase();
  const hits = RECURRING_KEYWORDS.filter((k) => text.includes(k)).length;
  if (hits >= 3) return 25;
  if (hits === 2) return 20;
  if (hits === 1) return 15;
  // Service / one-time still scores some points
  if (opp.opportunity_type === "service_business") return 8;
  return 5;
}

// ── Low barrier to entry (0–20) ───────────────────────────────────────────────
const LOW_BARRIER_KEYWORDS = [
  "no code", "low overhead", "bootstrap", "start with $0", "start for free",
  "no investment required", "part-time", "side hustle", "freelance first",
  "no inventory", "digital product", "productized",
];
const HIGH_BARRIER_KEYWORDS = [
  "requires funding", "venture capital", "hardware", "regulatory approval",
  "medical device", "pharmaceutical",
];

function barrierScore(opp) {
  const text = `${opp.description} ${opp.evidence_summary}`.toLowerCase();
  if (HIGH_BARRIER_KEYWORDS.some((k) => text.includes(k))) return 5;
  const hits = LOW_BARRIER_KEYWORDS.filter((k) => text.includes(k)).length;
  if (hits >= 2) return 20;
  if (hits === 1) return 15;
  if (["service_business", "automation_agency", "content_creator"].includes(opp.opportunity_type)) return 12;
  return 8;
}

// ── Proven demand / evidence (0–20) ──────────────────────────────────────────
const EVIDENCE_KEYWORDS = [
  "case study", "backtested", "real example", "x customers", "k customers",
  "revenue", "profit", "case", "example", "real-world", "data shows",
  "research shows", "study found", "proven", "validated",
];

function demandScore(opp) {
  const text = `${opp.evidence_summary} ${opp.description}`.toLowerCase();
  const hits = EVIDENCE_KEYWORDS.filter((k) => text.includes(k)).length;
  const confidenceBonus = Math.round((opp.confidence ?? 0) * 8);
  const base = Math.min(hits * 4, 12);
  return Math.min(base + confidenceBonus, 20);
}

// ── Automation / AI leverage (0–15) ──────────────────────────────────────────
const AI_KEYWORDS = [
  "automat", "ai ", "artificial intelligence", "no-code", "low-code",
  "make.com", "zapier", "n8n", "gohighlevel", "workflow", "chatgpt",
  "claude", "llm", "prompt", "agentic",
];

function automationScore(opp) {
  const text = `${opp.description} ${opp.evidence_summary}`.toLowerCase();
  const hits = AI_KEYWORDS.filter((k) => text.includes(k)).length;
  if (opp.opportunity_type === "automation_agency") return 15;
  if (opp.opportunity_type === "ai_product") return 15;
  if (hits >= 3) return 14;
  if (hits >= 2) return 10;
  if (hits >= 1) return 7;
  return 3;
}

// ── Source authority (0–10) ───────────────────────────────────────────────────
const HIGH_AUTH = [
  "indie hackers", "starter story", "acquire.com", "microacquire",
  "alex hormozi", "codie sanchez", "ycombinator", "y combinator",
  "first round", "a16z", "techcrunch",
];
const MED_AUTH = [
  "youtube", "podcast", "forbes", "entrepreneur", "inc.com",
  "hubspot", "zapier", "make.com",
];

function sourceAuthorityScore(opp) {
  const src = (opp.source ?? "").toLowerCase();
  if (HIGH_AUTH.some((s) => src.includes(s))) return 10;
  if (MED_AUTH.some((s) => src.includes(s))) return 6;
  return 3;
}

// ── Novelty / timing (0–10) ───────────────────────────────────────────────────
const NOVELTY_KEYWORDS = [
  "2026", "2025", "emerging", "new model", "shift", "disrupting",
  "underserved", "gap in the market", "whitespace", "untapped",
];
const COMMODITY_KEYWORDS = [
  "saturated", "highly competitive", "everyone is doing", "overcrowded",
];

function noveltyScore(opp) {
  const text = `${opp.description} ${opp.evidence_summary}`.toLowerCase();
  if (COMMODITY_KEYWORDS.some((k) => text.includes(k))) return 2;
  const hits = NOVELTY_KEYWORDS.filter((k) => text.includes(k)).length;
  if (opp.urgency === "high") return 10;
  if (hits >= 2) return 9;
  if (hits >= 1) return 6;
  return 4;
}

// ── Public scorer ─────────────────────────────────────────────────────────────

/**
 * Score a normalized BusinessOpportunity.
 * @param {Object} opp - Output from normalizeOpportunity()
 * @returns {number} Score 0–100
 */
export function scoreOpportunity(opp) {
  const score =
    recurringRevenueScore(opp) +
    barrierScore(opp) +
    demandScore(opp) +
    automationScore(opp) +
    sourceAuthorityScore(opp) +
    noveltyScore(opp);

  return Math.min(Math.max(score, 0), 100);
}

/**
 * Filter and sort opportunities by score.
 * @param {Array} opps
 * @param {number} minScore - Minimum score to include (default 35)
 * @returns {Array}
 */
export function filterAndRankOpportunities(opps, minScore = 35) {
  return opps
    .filter((o) => o.score >= minScore)
    .sort((a, b) => b.score - a.score);
}
