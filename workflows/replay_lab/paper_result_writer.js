import "dotenv/config";
import { randomUUID } from "crypto";

const SUPABASE_URL = process.env.SUPABASE_URL;
const SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;

function serviceHeaders() {
  return {
    "Content-Type": "application/json",
    "apikey": SUPABASE_SERVICE_ROLE_KEY,
    "Authorization": `Bearer ${SUPABASE_SERVICE_ROLE_KEY}`,
    "Prefer": "return=representation",
  };
}

/**
 * Inserts a new paper_trade_runs row with status "running".
 *
 * @param {Object} proposal
 * @param {string} mode  - e.g. "forex_static_rr" or "options_historical_profile"
 * @returns {Promise<Object>} saved run object
 */
export async function writePaperTradeRun(proposal, mode) {
  const payload = {
    run_key: `${proposal.id ?? randomUUID()}_${mode}_${Date.now()}`,
    proposal_id: proposal.id,
    signal_id: proposal.signal_id ?? null,
    asset_type: proposal.asset_type ?? null,
    symbol: proposal.symbol ?? null,
    strategy_id: proposal.strategy_id ?? null,
    replay_mode: mode,
    status: "running",
    trace_id: proposal.trace_id ?? randomUUID(),
  };

  const res = await fetch(`${SUPABASE_URL}/rest/v1/paper_trade_runs`, {
    method: "POST",
    headers: serviceHeaders(),
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const err = await res.text();
    throw new Error(`writePaperTradeRun: Supabase insert error: ${err}`);
  }

  const rows = await res.json();
  return Array.isArray(rows) ? rows[0] : rows;
}

/**
 * Inserts a replay_results row and updates paper_trade_runs to "finished".
 *
 * @param {string} runId       - paper_trade_runs.id (UUID from Supabase)
 * @param {Object} proposal
 * @param {Object} replayOutcome - result from simulateForexTrade or simulateOptionsStrategy
 * @returns {Promise<Object>} saved result row
 */
export async function writeReplayResult(runId, proposal, replayOutcome) {
  const payload = {
    run_id: runId,
    proposal_id: proposal.id,
    signal_id: proposal.signal_id ?? null,
    asset_type: proposal.asset_type ?? null,
    symbol: proposal.symbol ?? null,
    strategy_id: proposal.strategy_id ?? null,
    strategy_type: replayOutcome.strategy_type ?? proposal.strategy_id ?? null,
    replay_outcome: replayOutcome.replay_outcome,
    pnl_r: replayOutcome.pnl_r ?? null,
    pnl_pct: replayOutcome.pnl_pct ?? null,
    hit_take_profit: replayOutcome.hit_take_profit ?? false,
    hit_stop_loss: replayOutcome.hit_stop_loss ?? false,
    expired: replayOutcome.expired ?? false,
    bars_to_resolution: replayOutcome.bars_to_resolution ?? null,
    trace_id: proposal.trace_id ?? null,
  };

  const insertRes = await fetch(`${SUPABASE_URL}/rest/v1/replay_results`, {
    method: "POST",
    headers: serviceHeaders(),
    body: JSON.stringify(payload),
  });

  if (!insertRes.ok) {
    const err = await insertRes.text();
    throw new Error(`writeReplayResult: Supabase insert error: ${err}`);
  }

  const rows = await insertRes.json();
  const savedResult = Array.isArray(rows) ? rows[0] : rows;

  // Update paper_trade_runs status to "finished"
  const updateRes = await fetch(
    `${SUPABASE_URL}/rest/v1/paper_trade_runs?id=eq.${runId}`,
    {
      method: "PATCH",
      headers: {
        ...serviceHeaders(),
        "Prefer": "return=minimal",
      },
      body: JSON.stringify({ status: "finished", finished_at: new Date().toISOString() }),
    }
  );

  if (!updateRes.ok) {
    const err = await updateRes.text();
    throw new Error(`writeReplayResult: Supabase update error: ${err}`);
  }

  return savedResult;
}

/**
 * Returns aggregate replay stats across all replay_results.
 *
 * @returns {Promise<{total_runs: number, wins: number, losses: number, breakevens: number, avg_pnl_r: number}>}
 */
export async function getReplayStats() {
  const SUPABASE_KEY = process.env.SUPABASE_KEY;
  const headers = {
    "Content-Type": "application/json",
    "apikey": SUPABASE_KEY,
    "Authorization": `Bearer ${SUPABASE_KEY}`,
  };

  const res = await fetch(
    `${SUPABASE_URL}/rest/v1/replay_results?select=replay_outcome,pnl_r`,
    { headers }
  );

  if (!res.ok) {
    const err = await res.text();
    throw new Error(`getReplayStats: Supabase error: ${err}`);
  }

  const rows = await res.json();

  const total_runs = rows.length;
  const wins = rows.filter((r) => r.replay_outcome === "tp_hit" || r.replay_outcome === "win").length;
  const losses = rows.filter((r) => r.replay_outcome === "sl_hit" || r.replay_outcome === "loss").length;
  const breakevens = rows.filter(
    (r) => r.replay_outcome === "breakeven" || r.replay_outcome === "expired"
  ).length;

  const pnl_r_values = rows.map((r) => r.pnl_r).filter((v) => v != null);
  const avg_pnl_r =
    pnl_r_values.length > 0
      ? parseFloat((pnl_r_values.reduce((a, b) => a + b, 0) / pnl_r_values.length).toFixed(4))
      : 0;

  return { total_runs, wins, losses, breakevens, avg_pnl_r };
}
