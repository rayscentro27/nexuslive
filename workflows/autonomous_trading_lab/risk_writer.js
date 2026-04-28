/**
 * risk_writer.js
 * Writes risk decisions to risk_decisions table.
 * Updates proposal status to reflect risk outcome.
 */

import "dotenv/config";

const SUPABASE_URL = process.env.SUPABASE_URL;
const SERVICE_KEY  = process.env.SUPABASE_SERVICE_ROLE_KEY;

function h(extra = {}) {
  return {
    "Content-Type": "application/json",
    "apikey":        SERVICE_KEY,
    "Authorization": `Bearer ${SERVICE_KEY}`,
    "Prefer":        "return=representation",
    ...extra,
  };
}

export async function writeRiskDecision(proposalId, proposal, riskResult) {
  if (!SUPABASE_URL || !SERVICE_KEY) throw new Error("service_role key required");

  const row = {
    proposal_id: proposalId,
    signal_id:   proposal.signal_id ?? null,
    symbol:      proposal.symbol,
    side:        proposal.side ?? null,
    asset_type:  proposal.asset_type ?? "forex",
    risk_score:  riskResult.score,
    risk_flags:  riskResult.flags,
    decision:    riskResult.decision,
    trace_id:    riskResult.trace_id ?? proposal.trace_id,
  };

  const res = await fetch(`${SUPABASE_URL}/rest/v1/risk_decisions`, {
    method:  "POST",
    headers: h(),
    body:    JSON.stringify(row),
  });

  if (!res.ok) throw new Error(`writeRiskDecision: ${res.status} ${await res.text()}`);
  const body = await res.json();
  const saved = Array.isArray(body) ? body[0] : body;
  console.log(`[risk-writer] Decision written: ${saved?.id} — ${row.decision}`);

  // Update proposal status
  const pStatus = riskResult.decision === "approved"      ? "approved"
                : riskResult.decision === "manual_review" ? "needs_review"
                : "blocked";

  await fetch(`${SUPABASE_URL}/rest/v1/reviewed_signal_proposals?id=eq.${proposalId}`, {
    method:  "PATCH",
    headers: { ...h(), "Prefer": "return=minimal" },
    body:    JSON.stringify({ status: pStatus }),
  });

  return saved;
}
