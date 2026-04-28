// ── Grant Normalizer ──────────────────────────────────────────────────────────
// Transforms a research_artifact row into a normalized GrantOpportunity object.
// Uses regex + keyword heuristics — no AI calls required.
// ─────────────────────────────────────────────────────────────────────────────

// ── Funding amount extraction ─────────────────────────────────────────────────
const AMOUNT_RE = /\$[\d,]+(?:\.\d+)?(?:\s*(?:million|M|K|thousand|billion|B))?|\b\d[\d,]*(?:\.\d+)?\s*(?:million|M|K|thousand)\b/gi;

function extractFundingAmount(text) {
  const matches = text.match(AMOUNT_RE);
  if (!matches) return null;
  // Return the largest-looking match
  const sorted = matches.sort((a, b) => parseDollarAmount(b) - parseDollarAmount(a));
  return sorted[0] ?? null;
}

export function parseDollarAmount(str) {
  if (!str) return 0;
  const s = str.toLowerCase().replace(/[$,\s]/g, "");
  let n = parseFloat(s) || 0;
  if (s.includes("million") || s.endsWith("m")) n *= 1_000_000;
  else if (s.includes("thousand") || s.endsWith("k")) n *= 1_000;
  else if (s.includes("billion") || s.endsWith("b")) n *= 1_000_000_000;
  return n;
}

// ── Deadline extraction ───────────────────────────────────────────────────────
const DEADLINE_PATTERNS = [
  /deadline[:\s]+([A-Za-z]+\s+\d{1,2},?\s*\d{4})/i,
  /due\s+(?:by|date)[:\s]+([A-Za-z]+\s+\d{1,2},?\s*\d{4})/i,
  /applications?\s+(?:due|close[sd]?|open)\s+([A-Za-z]+\s+\d{1,2},?\s*\d{4})/i,
  /closes?\s+([A-Za-z]+\s+\d{1,2},?\s*\d{4})/i,
  /\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s*\d{4}\b/i,
  /\b(\d{1,2}\/\d{1,2}\/\d{2,4})\b/,
];

const ROLLING_RE = /rolling\s*basis|open\s*(?:enrollment|applications?)|no\s+deadline|ongoing/i;
const QUARTERLY_RE = /quarterly|semi.annual|annual\s+cycle/i;

function extractDeadline(text) {
  if (ROLLING_RE.test(text)) return "Rolling / ongoing";
  if (QUARTERLY_RE.test(text)) return "Quarterly / annual cycle";
  for (const re of DEADLINE_PATTERNS) {
    const m = text.match(re);
    if (m) return m[1] ?? m[0];
  }
  return null;
}

// ── Geography extraction ──────────────────────────────────────────────────────
const NATIONAL_RE = /\b(federal|national|nationwide|all\s+states?|us-wide|united\s+states)\b/i;
const AZ_RE = /\b(arizona|az|phoenix|tucson|scottsdale|tempe|mesa|chandler|gilbert)\b/i;
const STATE_RE = /\b([A-Z][a-z]+)\s+(?:state|department|commerce|economic)\b/;
const LOCAL_RE = /\b(local|city|county|municipal|region|metro|community)\b/i;

function extractGeography(text) {
  if (NATIONAL_RE.test(text)) return "National / Federal";
  if (AZ_RE.test(text)) return "Arizona";
  const stateMatch = text.match(STATE_RE);
  if (stateMatch) return stateMatch[1];
  if (LOCAL_RE.test(text)) return "Local / Regional";
  return "Unknown";
}

// ── Business type extraction ──────────────────────────────────────────────────
const BTYPE_PATTERNS = [
  [/small\s+business/i, "Small Business"],
  [/minority.owned|minority\s+business|mbe\b/i, "Minority-Owned Business"],
  [/women.owned|wbe\b|woman.owned/i, "Women-Owned Business"],
  [/veteran.owned|veteran\s+business|sdvosb|vosb\b/i, "Veteran-Owned Business"],
  [/startup|early.stage|pre.revenue/i, "Startup / Early-Stage"],
  [/technology|tech\s+company|software|saas\b/i, "Technology Company"],
  [/nonprofit|non.profit|501.?c/i, "Nonprofit"],
  [/manufacturing|manufacturer/i, "Manufacturing"],
  [/agricultural|farming|farm\b/i, "Agricultural"],
  [/research|r&d|innovation/i, "Research / Innovation"],
];

function extractBusinessType(text) {
  const matches = [];
  for (const [re, label] of BTYPE_PATTERNS) {
    if (re.test(text)) matches.push(label);
  }
  return matches.length ? matches.slice(0, 3).join(", ") : "General Small Business";
}

// ── Program name extraction ───────────────────────────────────────────────────
const KNOWN_PROGRAMS = [
  "SBIR", "STTR", "SBA", "SCORE", "USDA", "NSF", "NIH", "DOE", "DOD",
  "Hello Alice", "Grants.gov", "Arizona Commerce Authority", "ACA",
  "Economic Development", "Community Development", "CDFI",
];

function extractProgramName(artifact) {
  const text = `${artifact.title ?? ""} ${artifact.summary ?? ""}`;
  for (const name of KNOWN_PROGRAMS) {
    if (text.includes(name)) return name;
  }
  // Try to pull from title
  const titleMatch = artifact.title?.match(/^([^:–—-]+)/);
  return titleMatch ? titleMatch[1].trim() : artifact.source ?? "Unknown Program";
}

// ── Eligibility notes extraction ──────────────────────────────────────────────
function extractEligibility(artifact) {
  const candidates = [
    ...(artifact.action_items ?? []),
    ...(artifact.key_points ?? []),
  ];
  const eligNote = candidates.find((c) =>
    /eligib|qualif|require|must\s+(be|have)|criterion|criteria/i.test(c)
  );
  if (eligNote) return eligNote;
  // Fall back to first key point
  return artifact.key_points?.[0] ?? artifact.summary?.slice(0, 200) ?? null;
}

// ── Public normalizer ─────────────────────────────────────────────────────────

/**
 * Normalize a research_artifact row into a GrantOpportunity object.
 * @param {Object} artifact - Row from research_artifacts (topic = 'grant_research')
 * @returns {Object} Normalized grant opportunity
 */
export function normalizeGrant(artifact) {
  const text = [
    artifact.title ?? "",
    artifact.summary ?? "",
    artifact.content ?? "",
    ...(artifact.key_points ?? []),
    ...(artifact.opportunity_notes ?? []),
  ].join(" ");

  return {
    artifact_id: artifact.id,
    source: artifact.source ?? artifact.source_name ?? "Unknown",
    title: artifact.title ?? "Untitled Grant Source",
    program_name: extractProgramName(artifact),
    funding_amount: extractFundingAmount(text),
    geography: extractGeography(text),
    target_business_type: extractBusinessType(text),
    eligibility_notes: extractEligibility(artifact),
    deadline: extractDeadline(text),
    confidence: artifact.confidence ?? 0,
    score: 0, // filled in by grant_scoring.js
    status: "new",
    trace_id: artifact.trace_id ?? null,
  };
}
