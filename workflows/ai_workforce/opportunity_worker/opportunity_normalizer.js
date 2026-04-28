// ── Opportunity Normalizer ────────────────────────────────────────────────────
// Transforms a research_artifact (topic = business_opportunities | crm_automation)
// into a normalized BusinessOpportunity object.
// ─────────────────────────────────────────────────────────────────────────────

// ── Opportunity type detection ────────────────────────────────────────────────
const TYPE_RULES = [
  {
    type: "saas",
    patterns: [/\bsaas\b/i, /software.as.a.service/i, /subscription\s+software/i, /\bmrr\b/i, /\barr\b/i, /recurring\s+software/i],
  },
  {
    type: "automation_agency",
    patterns: [/automation\s+agency/i, /gohighlevel|ghl\b/i, /make\.com|integromat/i, /\bn8n\b/i, /workflow\s+automation/i, /no.code\s+agency/i, /crm\s+automation/i],
  },
  {
    type: "ai_product",
    patterns: [/ai\s+(?:tool|product|platform|app|agent)/i, /llm\s+app/i, /gpt.wrapper/i, /claude.app/i, /ai-powered/i],
  },
  {
    type: "content_creator",
    patterns: [/youtube\s+channel/i, /content\s+creator/i, /newsletter\s+business/i, /podcast\s+monetiz/i, /creator\s+economy/i],
  },
  {
    type: "service_business",
    patterns: [/consulting\s+business/i, /coaching\s+business/i, /done.for.you/i, /dfy\b/i, /agency\s+model/i, /freelance\s+to\s+agency/i, /credit\s+consulting/i],
  },
  {
    type: "acquisition",
    patterns: [/buy\s+a\s+business/i, /acquiring\s+(?:a\s+)?business/i, /micro.?acqui/i, /search\s+fund/i, /business\s+acquisition/i],
  },
  {
    type: "ecommerce",
    patterns: [/dropshipping/i, /amazon\s+fba/i, /shopify\s+store/i, /e.?commerce\b/i, /print.on.demand/i],
  },
  {
    type: "local_business",
    patterns: [/local\s+business/i, /brick.and.mortar/i, /laundromat|car\s+wash|vending\s+machine/i, /boring\s+business/i, /main\s+street/i],
  },
];

function detectOpportunityType(text) {
  for (const { type, patterns } of TYPE_RULES) {
    if (patterns.some((p) => p.test(text))) return type;
  }
  return "other";
}

// ── Niche detection ───────────────────────────────────────────────────────────
const NICHE_PATTERNS = [
  [/real\s+estate/i, "Real Estate"],
  [/credit\s+(?:repair|consulting|building)/i, "Credit Services"],
  [/\bfintech\b/i, "FinTech"],
  [/e.?commerce|shopify|amazon\s+fba/i, "E-Commerce"],
  [/health(?:care|tech)?\b/i, "Healthcare"],
  [/ed.?tech|online\s+course|education\s+platform/i, "EdTech"],
  [/legal\s+tech|law\s+firm\s+automation/i, "LegalTech"],
  [/marketing\s+agency|lead\s+gen/i, "Marketing / Lead Gen"],
  [/recruiting|hr\s+tech|talent/i, "HR / Recruiting"],
  [/restaurant|food\s+(?:delivery|tech)/i, "Food & Restaurant"],
  [/home\s+services|cleaning|pest\s+control/i, "Home Services"],
  [/bookkeeping|accounting\s+automation/i, "Accounting / Finance"],
  [/crm\s+automation|gohighlevel|hubspot/i, "CRM Automation"],
  [/content\s+creat|social\s+media\s+management/i, "Content / Social Media"],
  [/ai\s+agent|ai\s+automation/i, "AI Automation"],
  [/saas\b/i, "SaaS"],
];

function detectNiche(text) {
  for (const [re, label] of NICHE_PATTERNS) {
    if (re.test(text)) return label;
  }
  return "General Business";
}

// ── Monetization hint extraction ──────────────────────────────────────────────
const MONETIZATION_PATTERNS = [
  [/\$[\d,]+(?:\s*(?:per\s+month|\/mo|mrr|arr|\/year))/i, "Recurring revenue"],
  [/recurring\s+(?:revenue|income|fees?)/i, "Recurring revenue"],
  [/retainer/i, "Monthly retainer"],
  [/commission|rev\.?\s*share|revenue\s+sharing/i, "Commission / revenue share"],
  [/one.time\s+(?:fee|payment|sale)/i, "One-time sale"],
  [/productiz/i, "Productized service"],
  [/subscription/i, "Subscription"],
  [/affiliate/i, "Affiliate income"],
  [/licensing/i, "Licensing"],
  [/done.for.you|dfy\b/i, "Done-for-you service"],
];

function extractMonetizationHint(text) {
  for (const [re, label] of MONETIZATION_PATTERNS) {
    if (re.test(text)) return label;
  }
  return "Service / consulting";
}

// ── Urgency scoring ───────────────────────────────────────────────────────────
const HIGH_URGENCY = [/trending\s+now/i, /2026\s+opportunity/i, /emerging\s+market/i, /early\s+mover/i, /window\s+is\s+closing/i];
const LOW_URGENCY  = [/evergreen/i, /always\s+in\s+demand/i, /timeless/i];

function detectUrgency(text) {
  if (HIGH_URGENCY.some((p) => p.test(text))) return "high";
  if (LOW_URGENCY.some((p) => p.test(text))) return "low";
  return "medium";
}

// ── Evidence summary ──────────────────────────────────────────────────────────
function buildEvidenceSummary(artifact) {
  const points = artifact.key_points ?? [];
  if (points.length) return points.slice(0, 3).join(" | ");
  return (artifact.summary ?? "").slice(0, 200);
}

// ── Public normalizer ─────────────────────────────────────────────────────────

/**
 * Normalize a research_artifact into a BusinessOpportunity object.
 * @param {Object} artifact - Row from research_artifacts
 * @returns {Object} Normalized opportunity
 */
export function normalizeOpportunity(artifact) {
  const text = [
    artifact.title ?? "",
    artifact.summary ?? "",
    artifact.content ?? "",
    ...(artifact.key_points ?? []),
    ...(artifact.opportunity_notes ?? []),
  ].join(" ");

  return {
    artifact_id: artifact.id,
    source: artifact.source ?? "Unknown",
    title: artifact.title ?? "Untitled Opportunity",
    opportunity_type: detectOpportunityType(text),
    niche: detectNiche(text),
    description: (artifact.summary ?? "").slice(0, 500),
    evidence_summary: buildEvidenceSummary(artifact),
    monetization_hint: extractMonetizationHint(text),
    urgency: detectUrgency(text),
    confidence: artifact.confidence ?? 0,
    score: 0, // filled in by opportunity_scoring.js
    status: "new",
    trace_id: artifact.trace_id ?? null,
  };
}
