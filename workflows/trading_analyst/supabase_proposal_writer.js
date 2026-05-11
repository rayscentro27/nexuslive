/**
 * supabase_proposal_writer.js
 * Writes a validated AI proposal to reviewed_signal_proposals.
 * Uses service_role key to bypass RLS.
 */

import "dotenv/config";

const SUPABASE_URL = process.env.SUPABASE_URL;
const SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;

function headers() {
  return {
    "Content-Type": "application/json",
    "apikey": SUPABASE_SERVICE_ROLE_KEY,
    "Authorization": `Bearer ${SUPABASE_SERVICE_ROLE_KEY}`,
    "Prefer": "return=representation",
  };
}

/**
 * Write a proposal row. Returns the inserted row.
 *
 * @param {string} signalId   - UUID from tv_normalized_signals
 * @param {Object} proposal   - validated JSON from AI analyst
 * @returns {Promise<Object>}
 */
export async function writeProposal(signalId, proposal) {
  if (!SUPABASE_URL || !SUPABASE_SERVICE_ROLE_KEY) {
    throw new Error("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required");
  }

  const row = {
    signal_id:        signalId,
    symbol:           proposal.symbol,
    side:             proposal.side,
    timeframe:        proposal.timeframe,
    strategy_id:      proposal.strategy_id,
    entry_price:      proposal.entry_price,
    stop_loss:        proposal.stop_loss,
    take_profit:      proposal.take_profit,
    ai_confidence:    proposal.ai_confidence,
    market_context:   proposal.market_context,
    research_context: proposal.research_context,
    risk_notes:       proposal.risk_notes,
    recommendation:   proposal.recommendation,
    status:           proposal.status,
    trace_id:         proposal.trace_id,
  };

  const res = await fetch(`${SUPABASE_URL}/rest/v1/reviewed_signal_proposals`, {
    method: "POST",
    headers: headers(),
    body: JSON.stringify(row),
  });

  if (!res.ok) {
    const body = await res.text();
    throw new Error(`Failed to write proposal: ${res.status} ${body}`);
  }

  const inserted = await res.json();
  const record = Array.isArray(inserted) ? inserted[0] : inserted;
  console.log(`[writer] Proposal written: ${record?.id} — status=${row.status}`);
  return record;
}

/**
 * Mark a tv_normalized_signals row as 'reviewed' after proposal is written.
 * This prevents the signal from being picked up again on the next poll.
 *
 * @param {string} signalId
 */
export async function markSignalReviewed(signalId) {
  if (!SUPABASE_URL || !SUPABASE_SERVICE_ROLE_KEY) return;

  const res = await fetch(
    `${SUPABASE_URL}/rest/v1/tv_normalized_signals?id=eq.${signalId}`,
    {
      method: "PATCH",
      headers: {
        ...headers(),
        "Prefer": "return=minimal",
      },
      body: JSON.stringify({ status: "reviewed" }),
    }
  );

  if (!res.ok) {
    const body = await res.text();
    console.warn(`[writer] Could not mark signal ${signalId} as reviewed: ${res.status} ${body}`);
  } else {
    console.log(`[writer] Signal ${signalId} marked as reviewed.`);
  }
}
