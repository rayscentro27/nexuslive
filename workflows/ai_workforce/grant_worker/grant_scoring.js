// ── Grant Scoring ─────────────────────────────────────────────────────────────
// Assigns a priority score 0–100 to a normalized GrantOpportunity.
// Uses practical heuristics — no AI calls required.
//
// Score breakdown (max 100):
//   Funding amount    : 30 pts
//   Deadline urgency  : 20 pts
//   Geography match   : 15 pts
//   Eligibility detail: 15 pts
//   Source authority  : 10 pts
//   Confidence bonus  :  10 pts
// ─────────────────────────────────────────────────────────────────────────────

import { parseDollarAmount } from "./grant_normalizer.js";

// ── Funding amount score (0–30) ───────────────────────────────────────────────
function fundingScore(grant) {
  if (!grant.funding_amount) return 5; // mentioned but unknown
  const amt = parseDollarAmount(grant.funding_amount);
  if (amt >= 500_000) return 30;
  if (amt >= 100_000) return 25;
  if (amt >= 50_000)  return 20;
  if (amt >= 10_000)  return 15;
  if (amt >= 2_500)   return 10;
  if (amt > 0)        return 5;
  return 3; // string present but unparseable
}

// ── Deadline urgency score (0–20) ─────────────────────────────────────────────
function deadlineScore(grant) {
  if (!grant.deadline) return 5; // unknown — keep in radar
  const dl = grant.deadline.toLowerCase();
  if (dl.includes("rolling") || dl.includes("ongoing")) return 12;
  if (dl.includes("quarterly") || dl.includes("annual")) return 10;
  // Try to parse a real date
  const parsed = new Date(grant.deadline);
  if (isNaN(parsed.getTime())) return 8; // date string but unparseable
  const daysUntil = (parsed.getTime() - Date.now()) / (1000 * 60 * 60 * 24);
  if (daysUntil < 0)   return 0;  // expired
  if (daysUntil <= 14) return 20; // very urgent
  if (daysUntil <= 30) return 18;
  if (daysUntil <= 60) return 15;
  if (daysUntil <= 90) return 12;
  if (daysUntil <= 180) return 8;
  return 5;
}

// ── Geography score (0–15) ────────────────────────────────────────────────────
function geographyScore(grant) {
  const geo = (grant.geography ?? "").toLowerCase();
  if (geo.includes("national") || geo.includes("federal")) return 15;
  if (geo.includes("arizona")) return 14;
  if (geo.includes("local") || geo.includes("regional")) return 10;
  if (geo.includes("unknown")) return 5;
  return 8; // named state other than AZ
}

// ── Eligibility clarity score (0–15) ─────────────────────────────────────────
function eligibilityScore(grant) {
  const notes = grant.eligibility_notes ?? "";
  if (!notes) return 3;
  if (notes.length > 150) return 15;
  if (notes.length > 80) return 12;
  if (notes.length > 30) return 8;
  return 5;
}

// ── Source authority score (0–10) ─────────────────────────────────────────────
const HIGH_AUTH_SOURCES = [
  "sbir.gov", "sbir", "sttr", "grants.gov", "sba.gov", "sba",
  "nsf", "nih", "doe", "usda", "arizona commerce", "aca",
];
const MED_AUTH_SOURCES = [
  "hello alice", "score", "cdfi", "economic development",
  "chamber of commerce",
];

function authorityScore(grant) {
  const src = (grant.source ?? "").toLowerCase();
  if (HIGH_AUTH_SOURCES.some((s) => src.includes(s))) return 10;
  if (MED_AUTH_SOURCES.some((s) => src.includes(s))) return 7;
  return 4;
}

// ── Confidence bonus (0–10) ───────────────────────────────────────────────────
function confidenceBonus(grant) {
  return Math.round((grant.confidence ?? 0) * 10);
}

// ── Public scorer ─────────────────────────────────────────────────────────────

/**
 * Score a normalized GrantOpportunity.
 * @param {Object} grant - Output from normalizeGrant()
 * @returns {number} Score 0–100
 */
export function scoreGrant(grant) {
  const score =
    fundingScore(grant) +
    deadlineScore(grant) +
    geographyScore(grant) +
    eligibilityScore(grant) +
    authorityScore(grant) +
    confidenceBonus(grant);

  return Math.min(Math.max(score, 0), 100);
}

/**
 * Filter and sort grants by score.
 * @param {Array} grants
 * @param {number} minScore - Minimum score to include (default 30)
 * @returns {Array} Filtered and sorted grants (highest score first)
 */
export function filterAndRankGrants(grants, minScore = 30) {
  return grants
    .filter((g) => g.score >= minScore)
    .sort((a, b) => b.score - a.score);
}
