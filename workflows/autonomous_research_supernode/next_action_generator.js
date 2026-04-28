import "dotenv/config";

// ── SAFETY GUARD ──────────────────────────────────────────────────────────────
// RESEARCH ONLY. No trading, no broker connections.
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Topic-specific next-action templates.
 * Each function takes a brief and returns an array of prioritized action strings.
 */
const ACTION_TEMPLATES = {
  grant_research: (brief) => {
    const items = [];
    const text = JSON.stringify(brief).toLowerCase();

    if (text.includes("sbir") || text.includes("sttr")) {
      items.push("Review SBIR/STTR solicitation dates at sbir.gov and set calendar reminders for open windows");
    }
    if (text.includes("deadline") || text.includes("cycle")) {
      items.push("Map all noted grant deadlines to a tracking spreadsheet with required documents list");
    }
    if (text.includes("eligib")) {
      items.push("Run eligibility self-assessment against top 3 programs identified");
    }
    items.push("Draft one-page executive summary of business concept for grant applications");
    items.push("Identify a grant writer or SBA SCORE mentor for application support");

    return items.slice(0, 4);
  },

  credit_repair: (brief) => {
    const items = [];
    const text = JSON.stringify(brief).toLowerCase();

    if (text.includes("dispute") || text.includes("fcra")) {
      items.push("Draft dispute letter templates based on updated FCRA procedures noted");
    }
    if (text.includes("medical debt") || text.includes("medical")) {
      items.push("Flag all medical debt items on credit report for removal under new 2025 CFPB rules");
    }
    if (text.includes("consumer statement")) {
      items.push("Add consumer statement to disputed accounts explaining any extenuating circumstances");
    }
    items.push("Pull free annual credit reports from all 3 bureaus at annualcreditreport.com");
    items.push("Set 30-day follow-up reminder to verify bureau responses to disputes");

    return items.slice(0, 4);
  },

  business_opportunities: (brief) => {
    const items = [];
    const text = JSON.stringify(brief).toLowerCase();

    if (text.includes("saas") || text.includes("software")) {
      items.push("Research validated SaaS niches using Indie Hackers and MicroAcquire for market proof");
    }
    if (text.includes("agency") || text.includes("automation")) {
      items.push("Map 3 potential agency service packages with pricing, deliverables, and target client profile");
    }
    if (text.includes("linkedin") || text.includes("acquisition")) {
      items.push("Set up LinkedIn content calendar targeting identified acquisition channels");
    }
    if (text.includes("retainer") || text.includes("recurring")) {
      items.push("Design a recurring-revenue service offering around highest-confidence opportunity");
    }
    items.push("Build a one-week validation sprint: landing page + 5 outreach conversations");

    return items.slice(0, 4);
  },

  crm_automation: (brief) => {
    const items = [];
    const text = JSON.stringify(brief).toLowerCase();

    if (text.includes("gohighlevel") || text.includes("ghl")) {
      items.push("Audit existing GoHighLevel pipeline for gaps identified in research and add missing automation stages");
    }
    if (text.includes("make.com") || text.includes("zapier") || text.includes("n8n")) {
      items.push("Prototype identified workflow automation in Make.com sandbox environment");
    }
    if (text.includes("lead response") || text.includes("5 min")) {
      items.push("Set up instant lead response sequence — SMS + email within 5 minutes of opt-in");
    }
    if (text.includes("conversion") || text.includes("funnel")) {
      items.push("A/B test top-of-funnel lead magnet offer based on conversion insights from research");
    }
    items.push("Document current client onboarding workflow and identify top 3 automation gaps");

    return items.slice(0, 4);
  },

  trading: (brief) => {
    const items = [];
    const text = JSON.stringify(brief).toLowerCase();

    if (text.includes("session") || text.includes("overlap")) {
      items.push("Review London/NY session overlap timing windows for strategy alignment");
    }
    if (text.includes("risk") || text.includes("position sizing")) {
      items.push("Verify current position sizing rules against 1-2% max risk per trade guideline");
    }
    if (text.includes("volatility")) {
      items.push("Check current volatility regime and adjust strategy selection accordingly");
    }
    items.push("Add research insights to trade journal for pattern reference");
    items.push("Backtest highlighted strategy on recent 30-day data");

    return items.slice(0, 4);
  },

  general_business_intelligence: (brief) => [
    "File research into knowledge base under relevant topic tag",
    "Extract any actionable frameworks or models for future reference",
    "Share high-confidence insights with relevant team channels",
    "Schedule follow-up deep-dive on highest-signal topics found",
  ],
};

/**
 * Generate prioritized next actions from a research brief.
 *
 * Combines:
 *   1. Topic-specific templated actions (based on content signals)
 *   2. Extracted action_items from the brief itself
 *   3. Opportunity-driven actions
 *
 * @param {Object} brief - ResearchBrief object
 * @returns {string[]} Prioritized list of next actions (max 6)
 */
export function generateNextActions(brief) {
  const topic = brief.topic ?? "general_business_intelligence";
  const templateFn = ACTION_TEMPLATES[topic] ?? ACTION_TEMPLATES.general_business_intelligence;

  const templateActions = templateFn(brief);
  const briefActions = (brief.action_items ?? []).filter(Boolean);
  const opportunityActions = (brief.opportunity_notes ?? [])
    .filter(Boolean)
    .slice(0, 1)
    .map((o) => `Explore opportunity: ${o}`);

  // Merge: brief's own action_items take priority, then template, then opportunities
  const merged = [
    ...briefActions,
    ...templateActions,
    ...opportunityActions,
  ];

  // Deduplicate (naive: by lowercased first 40 chars)
  const seen = new Set();
  const deduped = merged.filter((a) => {
    const key = a.toLowerCase().slice(0, 40);
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });

  return deduped.slice(0, 6);
}

/**
 * Format next actions for console display.
 * @param {string[]} actions
 * @param {string} topic
 */
export function formatNextActionsForLog(actions, topic) {
  if (!actions.length) return "";
  const lines = [
    ``,
    `┌─ NEXT ACTIONS [${topic}] ─────────────────────────────────────`,
  ];
  actions.forEach((a, i) => lines.push(`│  ${i + 1}. ${a}`));
  lines.push(`└──────────────────────────────────────────────────────────────`);
  return lines.join("\n");
}
