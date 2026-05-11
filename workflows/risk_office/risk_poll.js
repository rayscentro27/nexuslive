/**
 * risk_poll.js
 * Fetches AI proposals from reviewed_signal_proposals that are
 * ready for risk office evaluation (status = 'proposed').
 *
 * Skips any proposal that already has a risk_decision row.
 */

import "dotenv/config";

const SUPABASE_URL = process.env.SUPABASE_URL;
const SUPABASE_KEY = process.env.SUPABASE_KEY;
const LIMIT = 5;

function headers() {
  return {
    "Content-Type": "application/json",
    "apikey": SUPABASE_KEY,
    "Authorization": `Bearer ${SUPABASE_KEY}`,
  };
}

export async function pollPendingProposals() {
  if (!SUPABASE_URL || !SUPABASE_KEY) {
    throw new Error("SUPABASE_URL and SUPABASE_KEY are required");
  }

  // 1. Fetch proposed (AI-approved) proposals not yet risk-evaluated
  const url = new URL(`${SUPABASE_URL}/rest/v1/reviewed_signal_proposals`);
  url.searchParams.set("status", "eq.proposed");
  url.searchParams.set(
    "select",
    "id,signal_id,symbol,side,timeframe,strategy_id,entry_price,stop_loss,take_profit,ai_confidence,market_context,research_context,risk_notes,recommendation,trace_id,created_at"
  );
  url.searchParams.set("order", "created_at.asc");
  url.searchParams.set("limit", String(LIMIT));

  const res = await fetch(url.toString(), { headers: headers() });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`Failed to fetch proposals: ${res.status} ${body}`);
  }

  const proposals = await res.json();
  if (!proposals.length) {
    console.log("[risk-poll] No pending proposals.");
    return [];
  }

  // 2. Filter out proposals that already have a risk decision
  const ids = proposals.map((p) => p.id);
  const decisionUrl = new URL(`${SUPABASE_URL}/rest/v1/risk_decisions`);
  decisionUrl.searchParams.set("proposal_id", `in.(${ids.join(",")})`);
  decisionUrl.searchParams.set("select", "proposal_id");

  const decRes = await fetch(decisionUrl.toString(), { headers: headers() });
  let alreadyDecided = new Set();
  if (decRes.ok) {
    const existing = await decRes.json();
    alreadyDecided = new Set(existing.map((d) => d.proposal_id));
  }

  const pending = proposals.filter((p) => !alreadyDecided.has(p.id));
  console.log(`[risk-poll] ${proposals.length} proposed, ${pending.length} need risk evaluation.`);
  return pending;
}
