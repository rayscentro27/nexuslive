// -- Autonomous Opportunity Ranker -------------------------------------------
// Scores aggregated opportunities using practical heuristics.
// -----------------------------------------------------------------------------

function repetitionScore(opportunity) {
  const count = opportunity.signal_count ?? 1;
  if (count >= 8) return 25;
  if (count >= 5) return 20;
  if (count >= 3) return 15;
  if (count >= 2) return 10;
  return 4;
}

function sourceAuthorityScore(opportunity) {
  const joinedSources = (opportunity.sources ?? []).join(" ").toLowerCase();
  const kinds = new Set(opportunity.source_kinds ?? []);

  let score = 3;
  if (kinds.has("hypothesis") || kinds.has("cluster")) score += 3;
  if (kinds.has("artifact") && kinds.has("claim")) score += 3;
  if (/\.gov|federal|state program|foundation/i.test(joinedSources)) score += 4;
  if (/forbes|techcrunch|ycombinator|indie hackers|hubspot/i.test(joinedSources)) score += 2;

  return Math.min(score, 15);
}

function noveltyScore(opportunity) {
  const text = `${opportunity.description ?? ""} ${opportunity.evidence_summary ?? ""}`.toLowerCase();
  const noveltyHits = [
    /new market|emerging|untapped|whitespace|underserved/,
    /2026|2027|policy update|regulatory shift/,
    /first mover|rapid growth|trend acceleration/,
  ].filter((p) => p.test(text)).length;

  if (noveltyHits >= 3) return 15;
  if (noveltyHits === 2) return 11;
  if (noveltyHits === 1) return 7;
  return 4;
}

function actionabilityScore(opportunity) {
  const text = `${opportunity.description ?? ""} ${opportunity.evidence_summary ?? ""}`.toLowerCase();
  const actionableHits = [
    /launch|pilot|test|prototype|validate/,
    /deadline|application|submit|intake/,
    /automate|integrate|workflow|standardize/,
    /package|offer|service tier|pricing/,
  ].filter((p) => p.test(text)).length;

  const base = actionableHits * 5;
  return Math.min(base || 6, 20);
}

function monetizationScore(opportunity) {
  const hint = (opportunity.monetization_hint ?? "").toLowerCase();
  const text = `${opportunity.description ?? ""} ${opportunity.evidence_summary ?? ""}`.toLowerCase();

  let score = 4;
  if (/recurring|subscription|retainer/.test(hint)) score = 15;
  else if (/grant funding/.test(hint)) score = 13;
  else if (/revenue share|commission/.test(hint)) score = 10;
  else if (/one-time/.test(hint)) score = 8;

  if (/high margin|low overhead|cash flow/.test(text)) score += 2;
  return Math.min(score, 15);
}

function urgencyScore(opportunity) {
  if (opportunity.urgency === "high") return 10;
  if (opportunity.urgency === "medium") return 6;
  return 3;
}

function confidenceAdjustment(opportunity) {
  const c = Number(opportunity.confidence ?? 0.5);
  return Math.round(Math.max(0, Math.min(1, c)) * 10);
}

function classifyPriority(score) {
  if (score >= 78) return "critical";
  if (score >= 62) return "high";
  if (score >= 45) return "medium";
  return "low";
}

export function scoreOpportunity(opportunity) {
  const score = Math.min(
    100,
    repetitionScore(opportunity) +
      sourceAuthorityScore(opportunity) +
      noveltyScore(opportunity) +
      actionabilityScore(opportunity) +
      monetizationScore(opportunity) +
      urgencyScore(opportunity) +
      confidenceAdjustment(opportunity)
  );

  return {
    ...opportunity,
    score,
    priority: classifyPriority(score),
  };
}

export function rankOpportunities(opportunities, { min_score = 40, limit = 20 } = {}) {
  return opportunities
    .map(scoreOpportunity)
    .filter((o) => o.score >= min_score)
    .sort((a, b) => {
      if (b.score !== a.score) return b.score - a.score;
      return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
    })
    .slice(0, limit);
}
