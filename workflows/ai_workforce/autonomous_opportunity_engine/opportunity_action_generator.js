// -- Autonomous Opportunity Actions ------------------------------------------
// Assigns recommended owner routing and concrete next actions per opportunity.
// -----------------------------------------------------------------------------

export const OWNER_ROUTING = Object.freeze({
  grant_opportunity: "GrantWorker",
  business_opportunity: "OpportunityWorker",
  service_gap: "CRM/Product",
  automation_idea: "Ops/Automation",
  saas_idea: "OpportunityWorker",
  product_improvement: "CRM/Product",
  niche_alert: "OpportunityWorker",
});

function templateActions(opportunity) {
  const common = [
    "Validate evidence sources and remove low-confidence signals.",
    "Create an owner assignment and 7-day execution checkpoint.",
  ];

  switch (opportunity.opportunity_type) {
    case "grant_opportunity":
      return [
        "GrantWorker: verify eligibility, amount, and submission deadline.",
        "Build application checklist with required documents and owner.",
        ...common,
      ];
    case "service_gap":
      return [
        "CRM/Product: confirm this gap with at least 3 client-facing pain signals.",
        "Draft a minimal service package or SOP to close the gap.",
        ...common,
      ];
    case "automation_idea":
      return [
        "Ops/Automation: map current manual workflow and estimate hours saved.",
        "Prototype one automation flow (sandbox) before rollout.",
        ...common,
      ];
    case "saas_idea":
      return [
        "OpportunityWorker: define ICP, problem statement, and MVP scope.",
        "Run a demand test with landing page + outreach before build.",
        ...common,
      ];
    case "product_improvement":
      return [
        "CRM/Product: convert insight into a scoped backlog item.",
        "Measure baseline metric before implementation (activation/churn/time-to-value).",
        ...common,
      ];
    case "niche_alert":
      return [
        "OpportunityWorker: verify trend persistence across multiple sources.",
        "Define one monetization test for this niche in the next cycle.",
        ...common,
      ];
    default:
      return [
        "OpportunityWorker: perform rapid viability scoring and owner assignment.",
        "Create one concrete validation action in the next sprint.",
        ...common,
      ];
  }
}

export function attachRoutingAndActions(opportunities = []) {
  return opportunities.map((opportunity) => ({
    ...opportunity,
    recommended_owner: OWNER_ROUTING[opportunity.opportunity_type] ?? "OpportunityWorker",
    next_actions: templateActions(opportunity).slice(0, 4),
  }));
}
