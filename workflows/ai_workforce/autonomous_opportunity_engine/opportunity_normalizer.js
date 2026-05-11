// -- Autonomous Opportunity Normalizer ---------------------------------------
// Converts heterogeneous research signals into normalized opportunity records.
// Research only. No trading execution, no broker calls.
// -----------------------------------------------------------------------------

const OPPORTUNITY_TYPE_RULES = [
  {
    type: "grant_opportunity",
    patterns: [
      /\bgrant\b/i,
      /\bfunding\b/i,
      /\bsbir\b/i,
      /\bsttr\b/i,
      /\bdeadline\b/i,
      /request for proposal|\brfp\b/i,
      /foundation|state program|federal program/i,
    ],
  },
  {
    type: "automation_idea",
    patterns: [
      /automation/i,
      /workflow/i,
      /manual process/i,
      /bottleneck/i,
      /zapier|make\.com|n8n/i,
      /crm automation|pipeline automation/i,
    ],
  },
  {
    type: "saas_idea",
    patterns: [
      /\bsaas\b/i,
      /subscription software/i,
      /dashboard/i,
      /api product|developer tool/i,
      /monthly recurring|\bmrr\b|\barr\b/i,
      /platform idea|software product/i,
    ],
  },
  {
    type: "product_improvement",
    patterns: [
      /feature request/i,
      /onboarding/i,
      /activation/i,
      /drop[- ]?off/i,
      /ux|ui friction|user friction/i,
      /missing feature|improve product/i,
    ],
  },
  {
    type: "service_gap",
    patterns: [
      /service gap|coverage gap/i,
      /underserved|unmet need/i,
      /pain point|pain-point/i,
      /missing support|missing service/i,
      /capacity gap|lack of providers/i,
    ],
  },
  {
    type: "niche_alert",
    patterns: [
      /emerging niche|new niche|micro[- ]niche/i,
      /niche demand|niche trend/i,
      /whitespace|untapped segment/i,
    ],
  },
  {
    type: "business_opportunity",
    patterns: [
      /opportunity/i,
      /market demand|demand signal/i,
      /monetization|revenue model/i,
      /business model/i,
    ],
  },
];

const NICHE_RULES = [
  [/credit repair|credit building|credit consulting/i, "Credit Services"],
  [/grant|sbir|sttr|foundation|nonprofit funding/i, "Grant Funding"],
  [/crm|pipeline|lead response|gohighlevel|hubspot/i, "CRM Automation"],
  [/legal|law firm/i, "Legal Services"],
  [/real estate|property/i, "Real Estate"],
  [/healthcare|medical/i, "Healthcare"],
  [/local business|main street/i, "Local Business"],
  [/accounting|bookkeeping|finance ops/i, "Finance Operations"],
  [/onboarding|retention|churn/i, "Customer Experience"],
  [/content|newsletter|youtube|creator/i, "Content Business"],
  [/automation agency|workflow automation/i, "Automation Agency"],
  [/\bsaas\b|software/i, "SaaS"],
  [/ai agent|ai workflow|llm/i, "AI Automation"],
];

const MONETIZATION_RULES = [
  [/subscription|mrr|arr|monthly recurring/i, "Recurring revenue"],
  [/retainer|managed service/i, "Monthly retainer"],
  [/one-time|one time|project fee/i, "One-time project"],
  [/commission|revenue share/i, "Revenue share"],
  [/grant|award|funding/i, "Grant funding"],
];

const URGENCY_RULES = {
  high: [/deadline|urgent|time-sensitive|closing soon|expiring/i, /severity\s*=\s*high/i],
  low: [/evergreen|long-term|backlog/i],
};

function pickOpportunityType(text, signal = {}) {
  const sourceKind = signal.source_kind ?? "";
  const sourceTopic = signal.source_topic ?? "";

  if (sourceKind === "coverage_gap") return "service_gap";
  if (sourceTopic === "grant_research") return "grant_opportunity";

  for (const rule of OPPORTUNITY_TYPE_RULES) {
    if (rule.patterns.some((p) => p.test(text))) return rule.type;
  }
  return "business_opportunity";
}

function pickNiche(text) {
  for (const [pattern, niche] of NICHE_RULES) {
    if (pattern.test(text)) return niche;
  }
  return "General Business";
}

function pickMonetizationHint(text, type) {
  if (type === "grant_opportunity") return "Grant funding";
  for (const [pattern, hint] of MONETIZATION_RULES) {
    if (pattern.test(text)) return hint;
  }
  return "Service / advisory";
}

function pickUrgency(text, signal = {}) {
  const severity = String(signal.severity ?? "").toLowerCase();
  if (severity === "high") return "high";

  if (URGENCY_RULES.high.some((p) => p.test(text))) return "high";
  if (URGENCY_RULES.low.some((p) => p.test(text))) return "low";
  return "medium";
}

function cleanSnippet(text, max = 220) {
  if (!text) return "";
  const cleaned = String(text).replace(/\s+/g, " ").trim();
  return cleaned.length > max ? `${cleaned.slice(0, max - 1)}...` : cleaned;
}

function titleFromSignal(signal, opportunityType, niche) {
  const signalTitle = signal.title ? String(signal.title).trim() : "";
  if (signalTitle) return signalTitle.slice(0, 140);

  const fallback = {
    grant_opportunity: `${niche} grant opportunity`,
    business_opportunity: `${niche} business opportunity`,
    service_gap: `${niche} service gap`,
    automation_idea: `${niche} automation idea`,
    saas_idea: `${niche} SaaS idea`,
    product_improvement: `${niche} product improvement`,
    niche_alert: `${niche} niche alert`,
  };
  return fallback[opportunityType] ?? `${niche} opportunity`;
}

function normalizeConfidence(raw) {
  const n = Number(raw);
  if (Number.isNaN(n)) return 0.5;
  return Math.max(0, Math.min(1, n));
}

function slugify(input) {
  return String(input ?? "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 80);
}

export function normalizeOpportunitySignal(signal) {
  const text = String(signal.text ?? "");
  const opportunity_type = pickOpportunityType(text, signal);
  const niche = pickNiche(text);
  const urgency = pickUrgency(text, signal);
  const monetization_hint = pickMonetizationHint(text, opportunity_type);
  const title = titleFromSignal(signal, opportunity_type, niche);

  return {
    id: signal.id ?? null,
    source: signal.source ?? "unknown",
    title,
    opportunity_type,
    niche,
    description: cleanSnippet(signal.description ?? text, 320),
    evidence_summary: cleanSnippet(signal.evidence ?? text, 260),
    monetization_hint,
    urgency,
    confidence: normalizeConfidence(signal.confidence),
    score: 0,
    recommended_owner: null,
    trace_id: signal.trace_id ?? null,
    created_at: signal.created_at ?? new Date().toISOString(),

    // Aggregation helpers
    title_key: slugify(title),
    source_kind: signal.source_kind ?? "unknown",
  };
}

export function toAggregationKey(normalized) {
  return [normalized.opportunity_type, normalized.niche, normalized.title_key].join("|");
}
