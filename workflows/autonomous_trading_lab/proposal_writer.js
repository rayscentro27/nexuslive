/**
 * proposal_writer.js
 * Writes AI proposals to reviewed_signal_proposals.
 * Marks the source signal as 'reviewed'.
 * Uses service_role key.
 */

import "dotenv/config";

const SUPABASE_URL  = process.env.SUPABASE_URL;
const SERVICE_KEY   = process.env.SUPABASE_SERVICE_ROLE_KEY;

function h(extra = {}) {
  return {
    "Content-Type": "application/json",
    "apikey":        SERVICE_KEY,
    "Authorization": `Bearer ${SERVICE_KEY}`,
    "Prefer":        "return=representation",
    ...extra,
  };
}

export async function writeProposal(signalId, proposal) {
  if (!SUPABASE_URL || !SERVICE_KEY) throw new Error("Supabase service_role key required");

  const row = {
    signal_id:        signalId,
    symbol:           proposal.symbol,
    asset_type:       proposal.asset_type ?? "forex",
    side:             proposal.side,
    timeframe:        proposal.timeframe,
    strategy_id:      proposal.strategy_id,
    entry_price:      proposal.entry_price,
    stop_loss:        proposal.stop_loss  ?? null,
    take_profit:      proposal.take_profit ?? null,
    ai_confidence:    proposal.ai_confidence,
    market_context:   proposal.market_context,
    research_context: proposal.research_context,
    risk_notes:       proposal.risk_notes,
    recommendation:   proposal.recommendation,
    status:           proposal.status,
    trace_id:         proposal.trace_id,
  };

  const res = await fetch(`${SUPABASE_URL}/rest/v1/reviewed_signal_proposals`, {
    method:  "POST",
    headers: h(),
    body:    JSON.stringify(row),
  });

  if (!res.ok) throw new Error(`writeProposal: ${res.status} ${await res.text()}`);
  const body = await res.json();
  const saved = Array.isArray(body) ? body[0] : body;
  console.log(`[proposal-writer] Written: ${saved?.id} — ${row.status}`);
  return saved;
}

export async function markSignalReviewed(signalId) {
  if (!SUPABASE_URL || !SERVICE_KEY) return;
  const res = await fetch(
    `${SUPABASE_URL}/rest/v1/tv_normalized_signals?id=eq.${signalId}`,
    {
      method:  "PATCH",
      headers: { ...h(), "Prefer": "return=minimal" },
      body:    JSON.stringify({ status: "reviewed" }),
    }
  );
  if (!res.ok) console.warn(`[proposal-writer] Could not mark signal ${signalId} reviewed`);
  else         console.log(`[proposal-writer] Signal ${signalId} → reviewed`);
}
