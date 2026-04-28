/**
 * lab_poll.js
 * Polls tv_normalized_signals for enriched, unreviewed signals.
 * Detects asset_type (forex | options) from strategy_id.
 * Returns up to MAX_SIGNALS_PER_RUN signals per call.
 */

import "dotenv/config";

const SUPABASE_URL = process.env.SUPABASE_URL;
const SUPABASE_KEY = process.env.SUPABASE_KEY;
const MAX          = Number(process.env.MAX_SIGNALS_PER_RUN ?? 5);

// Options strategy patterns — signals matching these get asset_type = 'options'
const OPTIONS_STRATEGIES = new Set([
  "covered_call", "cash_secured_put", "iron_condor", "credit_spread",
  "debit_spread", "zebra_strategy", "stock_repair_strategy",
  "bull_call_spread", "bear_put_spread", "straddle", "strangle",
  "butterfly", "calendar_spread", "diagonal_spread", "wheel_strategy",
]);

export function detectAssetType(strategyId) {
  if (!strategyId) return "forex";
  const id = strategyId.toLowerCase().replace(/[^a-z_]/g, "_");
  return OPTIONS_STRATEGIES.has(id) ? "options" : "forex";
}

function headers() {
  return {
    "Content-Type": "application/json",
    "apikey":        SUPABASE_KEY,
    "Authorization": `Bearer ${SUPABASE_KEY}`,
  };
}

export async function pollEnrichedSignals() {
  if (!SUPABASE_URL || !SUPABASE_KEY) {
    throw new Error("SUPABASE_URL and SUPABASE_KEY required");
  }

  // 1. Fetch enriched signals
  const url = new URL(`${SUPABASE_URL}/rest/v1/tv_normalized_signals`);
  url.searchParams.set("status",  "eq.enriched");
  url.searchParams.set("select",  "id,symbol,side,timeframe,strategy_id,entry_price,stop_loss,take_profit,confidence,session_label,trace_id,meta,created_at");
  url.searchParams.set("order",   "created_at.asc");
  url.searchParams.set("limit",   String(MAX));

  const res = await fetch(url.toString(), { headers: headers() });
  if (!res.ok) throw new Error(`poll failed: ${res.status} ${await res.text()}`);

  const signals = await res.json();
  if (!signals.length) { console.log("[poll] No enriched signals."); return []; }

  // 2. Skip signals already in reviewed_signal_proposals
  const ids = signals.map((s) => s.id);
  const propUrl = new URL(`${SUPABASE_URL}/rest/v1/reviewed_signal_proposals`);
  propUrl.searchParams.set("signal_id", `in.(${ids.join(",")})`);
  propUrl.searchParams.set("select",    "signal_id");

  const propRes = await fetch(propUrl.toString(), { headers: headers() });
  const alreadyDone = new Set(
    propRes.ok ? (await propRes.json()).map((r) => r.signal_id) : []
  );

  const fresh = signals
    .filter((s) => !alreadyDone.has(s.id))
    .map((s) => ({ ...s, asset_type: detectAssetType(s.strategy_id) }));

  console.log(`[poll] ${signals.length} enriched, ${fresh.length} unreviewed (${fresh.filter(s=>s.asset_type==="options").length} options, ${fresh.filter(s=>s.asset_type==="forex").length} forex)`);
  return fresh;
}
