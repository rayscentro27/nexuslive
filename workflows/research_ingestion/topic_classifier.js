// ── SAFETY GUARD ──────────────────────────────────────────────────────────────
// RESEARCH ONLY. No trading, no broker connections.
// ─────────────────────────────────────────────────────────────────────────────

const TOPIC_KEYWORDS = {
  trading: [
    "forex", "stock", "options", "futures", "entry", "stop loss", "take profit",
    "pip", "lot size", "spread", "bullish", "bearish", "candlestick", "breakout",
    "trend line", "resistance", "support level", "rsi", "macd", "moving average",
    "fibonacci", "oanda", "tradingview", "risk reward", "drawdown", "pnl",
    "position sizing", "hedge", "short sell", "long position", "technical analysis",
  ],
  credit_repair: [
    "credit score", "fico", "credit report", "dispute", "collection account",
    "charge off", "tradeline", "authorized user", "credit mix", "credit utilization",
    "cfpb", "equifax", "transunion", "experian", "derogatory", "goodwill letter",
    "credit bureau", "hard inquiry", "late payment", "credit limit", "secured card",
    "credit builder", "debt validation", "fcra", "fair credit",
  ],
  grant_research: [
    "grant", "funding", "sbir", "sttr", "minority owned", "small business grant",
    "sba", "government funding", "application deadline", "nonprofit funding",
    "community development", "grant program", "eligible", "award amount",
    "federal grant", "state grant", "local grant", "grant writing",
    "grant database", "grants.gov", "business grant", "startup grant",
  ],
  business_opportunities: [
    "business model", "passive income", "saas", "revenue stream", "roi", "startup",
    "agency model", "dropshipping", "ecommerce", "franchise", "automation agency",
    "service business", "niche market", "cash flow", "recurring revenue", "mrr",
    "side hustle", "digital product", "consulting", "monetize", "profit margin",
    "scale business", "client acquisition", "lead gen", "online business",
  ],
  crm_automation: [
    "crm", "workflow automation", "lead generation", "pipeline", "follow-up sequence",
    "customer journey", "onboarding", "zapier", "make.com", "gohighlevel",
    "hubspot", "salesforce", "drip campaign", "nurture sequence", "automation",
    "funnel", "conversion", "email sequence", "customer retention", "sms campaign",
    "autoresponder", "lead nurture", "customer lifecycle",
  ],
};

const SUBTHEME_KEYWORDS = {
  // Credit repair subthemes
  dispute_letters: [
    "dispute letter", "goodwill letter", "verification letter", "cfpb complaint",
    "send dispute", "written dispute", "certified mail dispute",
  ],
  authorized_user_tradelines: [
    "authorized user", "tradeline", "piggybacking", "add to account", "primary card holder",
  ],
  // Grant subthemes
  small_business_grants: [
    "small business grant", "sba grant", "business funding grant", "entrepreneur grant",
  ],
  local_grants: [
    "local grant", "city grant", "county grant", "state grant", "municipal grant",
  ],
  minority_grants: [
    "minority grant", "minority owned business", "women owned", "mwbe", "disadvantaged",
  ],
  // Business subthemes
  saas_opportunities: [
    "saas", "software as a service", "subscription model", "mrr", "arr", "b2b software",
  ],
  service_business_models: [
    "service business", "agency model", "consulting", "freelance", "done for you",
  ],
  lead_generation: [
    "lead generation", "lead gen", "warm leads", "cold outreach", "prospecting",
  ],
  ai_automation_agency: [
    "ai agency", "automation agency", "ai tools", "ai workflow", "ai business",
  ],
  // CRM subthemes
  underwriting_workflows: [
    "underwriting", "approval workflow", "loan workflow", "risk assessment workflow",
  ],
  // Trading subthemes
  forex_risk_management: [
    "forex risk", "position sizing", "drawdown", "risk reward", "stop loss placement",
  ],
  options_income_strategies: [
    "covered call", "cash secured put", "wheel strategy", "iron condor",
    "credit spread", "options income", "theta decay",
  ],
  london_breakout: [
    "london session", "london breakout", "london open", "asian range",
  ],
};

/**
 * Classify a text body into a topic and subthemes using keyword scoring.
 *
 * @param {string} text - transcript or content text
 * @returns {{ topic: string, subthemes: string[], confidence: number }}
 */
export function classifyTopic(text) {
  const lower = text.toLowerCase();

  // Score each topic by keyword hit count
  const scores = {};
  for (const [topic, keywords] of Object.entries(TOPIC_KEYWORDS)) {
    scores[topic] = keywords.filter(kw => lower.includes(kw)).length;
  }

  const sorted = Object.entries(scores).sort(([, a], [, b]) => b - a);
  const [bestTopic, bestScore] = sorted[0];

  // Confidence: normalize to 0–1 (5 hits = 1.0, 0 hits = 0)
  const confidence = parseFloat(Math.min(bestScore / 5, 1.0).toFixed(2));

  const topic = bestScore > 0 ? bestTopic : "general_business_intelligence";

  // Detect subthemes — check all, not just for winning topic
  const subthemes = [];
  for (const [subtheme, keywords] of Object.entries(SUBTHEME_KEYWORDS)) {
    if (keywords.some(kw => lower.includes(kw))) {
      subthemes.push(subtheme);
    }
  }

  return { topic, subthemes, confidence };
}
