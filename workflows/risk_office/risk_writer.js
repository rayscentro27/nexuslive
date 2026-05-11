/**
 * risk_writer.js
 * Writes risk decisions to Supabase and updates proposal status.
 * Uses service_role key to bypass RLS.
 */

import "dotenv/config";

const SUPABASE_URL         = process.env.SUPABASE_URL;
const SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;

function headers(extra = {}) {
  return {
    "Content-Type": "application/json",
    "apikey": SUPABASE_SERVICE_ROLE_KEY,
    "Authorization": `Bearer ${SUPABASE_SERVICE_ROLE_KEY}`,
    "Prefer": "return=representation",
    ...extra,
  };
}

/**
 * Write a risk decision row and update the proposal status.
 *
 * @param {string}  proposalId  - UUID of reviewed_signal_proposals row
 * @param {Object}  proposal    - full proposal row
 * @param {Object}  decision    - result from evaluateProposal()
 * @returns {Promise<Object>}   - inserted risk_decisions row
 */
export async function writeRiskDecision(proposalId, proposal, decision) {
  if (!SUPABASE_URL || !SUPABASE_SERVICE_ROLE_KEY) {
    throw new Error("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required");
  }

  // 1. Insert risk_decisions row
  const row = {
    proposal_id:          proposalId,
    signal_id:            proposal.signal_id,
    symbol:               proposal.symbol,
    side:                 proposal.side,
    status:               decision.status,                   // approved | rejected | held
    rejection_reason:     decision.rejection_reason ?? null,
    risk_score:           decision.risk_score,
    rr_ratio:             decision.rr_ratio,
    daily_pnl_used:       decision.daily_pnl_used,
    open_positions_count: decision.open_positions_count,
    rr_ok:                decision.checks?.rr_ok ?? null,
    prices_ok:            decision.checks?.prices_ok ?? null,
    daily_pnl_ok:         decision.checks?.daily_pnl_ok ?? null,
    positions_ok:         decision.checks?.positions_ok ?? null,
    no_duplicate:         decision.checks?.no_duplicate ?? null,
    trace_id:             proposal.trace_id,
  };

  const insertRes = await fetch(`${SUPABASE_URL}/rest/v1/risk_decisions`, {
    method: "POST",
    headers: headers(),
    body: JSON.stringify(row),
  });

  if (!insertRes.ok) {
    const body = await insertRes.text();
    throw new Error(`Failed to write risk decision: ${insertRes.status} ${body}`);
  }

  const inserted = await insertRes.json();
  const record = Array.isArray(inserted) ? inserted[0] : inserted;
  console.log(`[risk-writer] Decision written: ${record?.id} — ${decision.status}`);

  // 2. Update proposal status to reflect risk outcome
  //    proposed → approved / rejected / held
  const proposalStatus =
    decision.status === "approved" ? "approved" :
    decision.status === "held"     ? "needs_review" :
    "blocked";

  const patchRes = await fetch(
    `${SUPABASE_URL}/rest/v1/reviewed_signal_proposals?id=eq.${proposalId}`,
    {
      method: "PATCH",
      headers: { ...headers(), "Prefer": "return=minimal" },
      body: JSON.stringify({ status: proposalStatus }),
    }
  );

  if (!patchRes.ok) {
    console.warn(`[risk-writer] Could not update proposal ${proposalId} status`);
  }

  return record;
}
