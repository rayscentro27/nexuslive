/**
 * analyst_poll.js
 * Fetches enriched signals from Supabase that have not yet been reviewed.
 * Returns up to 5 signals per call.
 *
 * Signals are fetched where:
 *   status = 'enriched'
 *   AND no existing reviewed_signal_proposals row for this signal_id
 *
 * Uses the anon key (read-only).
 */

import "dotenv/config";

const SUPABASE_URL = process.env.SUPABASE_URL;
const SUPABASE_KEY = process.env.SUPABASE_KEY;
const LIMIT = 5;

function supabaseHeaders() {
  return {
    "Content-Type": "application/json",
    "apikey": SUPABASE_KEY,
    "Authorization": `Bearer ${SUPABASE_KEY}`,
  };
}

/**
 * Returns up to LIMIT enriched signals not yet reviewed.
 * @returns {Promise<Array>}
 */
export async function pollEnrichedSignals() {
  if (!SUPABASE_URL || !SUPABASE_KEY) {
    throw new Error("SUPABASE_URL and SUPABASE_KEY are required");
  }

  // 1. Fetch enriched signals
  const url = new URL(`${SUPABASE_URL}/rest/v1/tv_normalized_signals`);
  url.searchParams.set("status", "eq.enriched");
  url.searchParams.set("select", "id,symbol,side,timeframe,strategy_id,entry_price,stop_loss,take_profit,confidence,trace_id,meta,created_at");
  url.searchParams.set("order", "created_at.asc");
  url.searchParams.set("limit", String(LIMIT));

  const res = await fetch(url.toString(), { headers: supabaseHeaders() });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`Failed to fetch signals: ${res.status} ${body}`);
  }

  const signals = await res.json();
  if (!signals.length) return [];

  // 2. Filter out already-reviewed signal_ids
  const ids = signals.map((s) => s.id);
  const proposalUrl = new URL(`${SUPABASE_URL}/rest/v1/reviewed_signal_proposals`);
  proposalUrl.searchParams.set("signal_id", `in.(${ids.join(",")})`);
  proposalUrl.searchParams.set("select", "signal_id");

  const proposalRes = await fetch(proposalUrl.toString(), { headers: supabaseHeaders() });
  let alreadyReviewed = new Set();
  if (proposalRes.ok) {
    const existing = await proposalRes.json();
    alreadyReviewed = new Set(existing.map((p) => p.signal_id));
  }

  const unreviewed = signals.filter((s) => !alreadyReviewed.has(s.id));

  console.log(`[poll] Found ${signals.length} enriched signals, ${unreviewed.length} not yet reviewed.`);
  return unreviewed;
}
