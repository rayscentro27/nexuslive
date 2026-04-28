// sl_tp_optimizer.js — Stop Loss / Take Profit placement optimizer
// RESEARCH ONLY — no live trading, no broker execution, no order placement

import "dotenv/config";

const SUPABASE_URL = process.env.SUPABASE_URL;
const SUPABASE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || process.env.SUPABASE_KEY;

// ---------------------------------------------------------------------------
// Supabase helper
// ---------------------------------------------------------------------------
async function supabaseQuery(path, params = {}) {
  const url = new URL(`${SUPABASE_URL}/rest/v1/${path}`);
  for (const [k, v] of Object.entries(params)) url.searchParams.set(k, v);

  const res = await fetch(url.toString(), {
    headers: {
      apikey: SUPABASE_KEY,
      Authorization: `Bearer ${SUPABASE_KEY}`,
      "Content-Type": "application/json",
    },
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Supabase query failed [${res.status}]: ${text}`);
  }
  return res.json();
}

// ---------------------------------------------------------------------------
// analyzeSlTpPlacement
// ---------------------------------------------------------------------------
/**
 * Analyzes stop loss and take profit placement from historical proposals.
 *
 * @param {string|null} strategyId  Filter to a specific strategy_id, or null for all.
 * @returns {Promise<Array>}  Array of optimization objects per strategy.
 *
 * Each object:
 *   {
 *     strategy_id, sample_count,
 *     avg_sl_distance, avg_tp_distance, avg_rr,
 *     optimal_rr,            // RR that correlates with best win_rate in replay data
 *     suggested_sl_pct,      // recommended SL as % of entry
 *     suggested_tp_pct,      // recommended TP as % of entry
 *     improvement_score,     // 0-100 (how much optimization could help)
 *     notes
 *   }
 */
export async function analyzeSlTpPlacement(strategyId = null) {
  console.log("[sl_tp_optimizer] Fetching reviewed_signal_proposals...");

  // Build query params for reviewed_signal_proposals
  const proposalParams = {
    select: "id,strategy_id,entry_price,stop_loss,take_profit,rr_ratio,asset_type",
    asset_type: "eq.forex",
    order: "created_at.desc",
    limit: "500",
  };
  if (strategyId) proposalParams["strategy_id"] = `eq.${strategyId}`;

  const proposals = await supabaseQuery("reviewed_signal_proposals", proposalParams);

  console.log(`[sl_tp_optimizer] Fetched ${proposals.length} forex proposals.`);

  if (proposals.length === 0) {
    return [
      {
        strategy_id: strategyId || "all",
        sample_count: 0,
        avg_sl_distance: null,
        avg_tp_distance: null,
        avg_rr: null,
        optimal_rr: null,
        suggested_sl_pct: null,
        suggested_tp_pct: null,
        improvement_score: 0,
        notes: "No forex proposals found — insufficient data for optimization.",
      },
    ];
  }

  // Fetch replay results to cross-reference win rates
  const replayParams = {
    select: "proposal_id,strategy_id,replay_outcome,pnl_r,asset_type",
    asset_type: "eq.forex",
    limit: "1000",
  };
  if (strategyId) replayParams["strategy_id"] = `eq.${strategyId}`;

  let replayResults = [];
  try {
    replayResults = await supabaseQuery("replay_results", replayParams);
    console.log(`[sl_tp_optimizer] Fetched ${replayResults.length} replay results.`);
  } catch (err) {
    console.warn("[sl_tp_optimizer] Could not fetch replay_results:", err.message);
  }

  // Build replay index: proposal_id → outcome
  const replayIndex = {};
  for (const r of replayResults) {
    if (r.proposal_id) {
      replayIndex[r.proposal_id] = r;
    }
  }

  // Group proposals by strategy_id
  const byStrategy = {};
  for (const p of proposals) {
    const sid = p.strategy_id || "unknown";
    if (!byStrategy[sid]) byStrategy[sid] = [];
    byStrategy[sid].push(p);
  }

  const results = [];

  for (const [sid, props] of Object.entries(byStrategy)) {
    const validProps = props.filter(
      (p) =>
        p.entry_price != null &&
        p.stop_loss != null &&
        p.take_profit != null &&
        p.entry_price > 0
    );

    if (validProps.length === 0) {
      results.push({
        strategy_id: sid,
        sample_count: props.length,
        avg_sl_distance: null,
        avg_tp_distance: null,
        avg_rr: null,
        optimal_rr: null,
        suggested_sl_pct: null,
        suggested_tp_pct: null,
        improvement_score: 0,
        notes: "Proposals missing price data — cannot compute SL/TP distances.",
      });
      continue;
    }

    // Compute average distances
    const slDistances = validProps.map((p) =>
      Math.abs(p.entry_price - p.stop_loss)
    );
    const tpDistances = validProps.map((p) =>
      Math.abs(p.take_profit - p.entry_price)
    );
    const rrRatios = validProps
      .map((p) => p.rr_ratio)
      .filter((r) => r != null && r > 0);

    const avg = (arr) =>
      arr.length ? arr.reduce((a, b) => a + b, 0) / arr.length : null;

    const avgSlDistance = avg(slDistances);
    const avgTpDistance = avg(tpDistances);
    const avgRr = avg(rrRatios);

    // Compute SL/TP as % of entry price
    const slPcts = validProps.map(
      (p) => Math.abs(p.entry_price - p.stop_loss) / p.entry_price
    );
    const tpPcts = validProps.map(
      (p) => Math.abs(p.take_profit - p.entry_price) / p.entry_price
    );
    const avgSlPct = avg(slPcts);
    const avgTpPct = avg(tpPcts);

    // Cross-reference replay results to find optimal RR
    // Group replay results by RR bucket and compute win rates
    const rrBuckets = {};
    for (const p of validProps) {
      const replay = replayIndex[p.id];
      if (!replay) continue;
      const rr = p.rr_ratio != null ? Math.round(p.rr_ratio * 2) / 2 : null; // bucket to nearest 0.5
      if (rr == null) continue;
      if (!rrBuckets[rr]) rrBuckets[rr] = { wins: 0, total: 0 };
      rrBuckets[rr].total++;
      if (
        replay.replay_outcome === "tp_hit" ||
        replay.replay_outcome === "win"
      ) {
        rrBuckets[rr].wins++;
      }
    }

    // Find RR bucket with highest win rate (min 2 samples)
    let optimalRr = null;
    let bestWinRate = 0;
    for (const [rr, bucket] of Object.entries(rrBuckets)) {
      if (bucket.total >= 2) {
        const wr = bucket.wins / bucket.total;
        if (wr > bestWinRate) {
          bestWinRate = wr;
          optimalRr = parseFloat(rr);
        }
      }
    }

    // Compute improvement score (0–100)
    // Higher score = more opportunity to improve
    let improvementScore = 0;
    if (avgRr != null && optimalRr != null) {
      const rrGap = Math.abs(optimalRr - avgRr);
      improvementScore = Math.min(100, Math.round(rrGap * 25)); // 4-point RR gap = 100
    } else if (avgRr != null) {
      // No replay data: score based on how far current avg is from ideal 2.0 RR
      const idealRr = 2.0;
      improvementScore = Math.min(
        100,
        Math.round(Math.abs(idealRr - avgRr) * 20)
      );
    }

    // Suggested SL/TP: nudge toward optimal RR if known, else use current averages
    let suggestedSlPct = avgSlPct;
    let suggestedTpPct = avgTpPct;

    if (optimalRr != null && avgSlPct != null) {
      suggestedTpPct = avgSlPct * optimalRr;
    } else if (avgRr != null && avgRr < 1.5 && avgSlPct != null) {
      // Current RR is low — suggest widening TP to 2:1
      suggestedTpPct = avgSlPct * 2.0;
    }

    const notes = buildSlTpNotes(avgRr, optimalRr, validProps.length);

    results.push({
      strategy_id: sid,
      sample_count: validProps.length,
      avg_sl_distance: avgSlDistance != null ? parseFloat(avgSlDistance.toFixed(6)) : null,
      avg_tp_distance: avgTpDistance != null ? parseFloat(avgTpDistance.toFixed(6)) : null,
      avg_rr: avgRr != null ? parseFloat(avgRr.toFixed(3)) : null,
      optimal_rr: optimalRr,
      suggested_sl_pct: suggestedSlPct != null ? parseFloat((suggestedSlPct * 100).toFixed(4)) : null,
      suggested_tp_pct: suggestedTpPct != null ? parseFloat((suggestedTpPct * 100).toFixed(4)) : null,
      improvement_score: improvementScore,
      notes,
    });
  }

  // Sort by improvement_score descending
  results.sort((a, b) => b.improvement_score - a.improvement_score);

  console.log(
    `[sl_tp_optimizer] Analysis complete — ${results.length} strategies analyzed.`
  );
  return results;
}

// ---------------------------------------------------------------------------
// Helper
// ---------------------------------------------------------------------------
function buildSlTpNotes(avgRr, optimalRr, sampleCount) {
  const parts = [];

  if (sampleCount < 10) {
    parts.push(`Low sample count (${sampleCount}) — results provisional.`);
  }

  if (avgRr != null) {
    if (avgRr < 1.5) {
      parts.push(
        `Current avg RR ${avgRr.toFixed(2)} is below 1.5 — consider tightening SL or widening TP.`
      );
    } else if (avgRr >= 2.5) {
      parts.push(
        `Current avg RR ${avgRr.toFixed(2)} is high — verify TP targets are realistic.`
      );
    } else {
      parts.push(`Current avg RR ${avgRr.toFixed(2)} is within acceptable range.`);
    }
  }

  if (optimalRr != null) {
    parts.push(
      `Replay data suggests optimal RR is ${optimalRr.toFixed(1)} — adjust TP accordingly.`
    );
  } else {
    parts.push("No replay data available — using heuristic benchmarks.");
  }

  return parts.join(" ");
}
