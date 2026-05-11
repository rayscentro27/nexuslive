// options_structure_optimizer.js — Options structure performance analyzer
// RESEARCH ONLY — no live trading, no broker execution, no order placement

import "dotenv/config";

const SUPABASE_URL = process.env.SUPABASE_URL;
const SUPABASE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || process.env.SUPABASE_KEY;

// ---------------------------------------------------------------------------
// Options structure benchmarks
// ---------------------------------------------------------------------------
const OPTIONS_BENCHMARKS = {
  covered_call: {
    optimal_strike_otm_pct: 0.02,
    optimal_dte: 30,
    target_premium_pct: 0.02,
    notes: "Sell 2% OTM call ~30 DTE, collect 2% premium",
  },
  cash_secured_put: {
    optimal_strike_otm_pct: 0.03,
    optimal_dte: 30,
    target_premium_pct: 0.025,
    notes: "Sell 3% OTM put ~30 DTE, collect 2.5% premium",
  },
  iron_condor: {
    optimal_wing_width_pct: 0.05,
    optimal_dte: 45,
    target_credit_pct: 0.03,
    notes: "5% wide wings, 45 DTE, collect 3% credit",
  },
  credit_spread: {
    optimal_width_pct: 0.03,
    optimal_dte: 21,
    target_credit_pct: 0.015,
    notes: "3% wide spread, 21 DTE, collect 1.5% credit",
  },
  zebra_strategy: {
    optimal_delta: 0.7,
    optimal_dte: 90,
    notes: "Deep ITM LEAPS + short calls — 70-delta long leg, 90 DTE minimum",
  },
  wheel_strategy: {
    optimal_strike_otm_pct: 0.05,
    optimal_dte: 30,
    target_premium_pct: 0.02,
    notes: "Sell 5% OTM put ~30 DTE, collect 2% premium, repeat after assignment",
  },
};

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
// analyzeOptionsStructures
// ---------------------------------------------------------------------------
/**
 * Analyzes options structure performance against benchmark parameters.
 *
 * @param {string|null} strategyType  Filter to a specific strategy type, or null for all.
 * @returns {Promise<Array>}
 *
 * Each result object:
 *   {
 *     strategy_type, sample_count,
 *     parameter_name, original_value, suggested_value,
 *     improvement_score,  // 0-100
 *     notes
 *   }
 */
export async function analyzeOptionsStructures(strategyType = null) {
  console.log("[options_optimizer] Fetching options proposals...");

  // Fetch reviewed options proposals
  const proposalParams = {
    select:
      "id,strategy_type,strategy_id,entry_price,stop_loss,take_profit,rr_ratio,asset_type,metadata",
    asset_type: "eq.options",
    order: "created_at.desc",
    limit: "500",
  };
  if (strategyType) proposalParams["strategy_type"] = `eq.${strategyType}`;

  let proposals = [];
  try {
    proposals = await supabaseQuery("reviewed_signal_proposals", proposalParams);
    console.log(`[options_optimizer] Fetched ${proposals.length} options proposals.`);
  } catch (err) {
    console.warn("[options_optimizer] Could not fetch proposals:", err.message);
  }

  // Fetch options performance data
  let perfData = [];
  try {
    const perfParams = {
      select: "*",
      order: "updated_at.desc",
    };
    if (strategyType) perfParams["strategy_type"] = `eq.${strategyType}`;
    perfData = await supabaseQuery("options_strategy_performance", perfParams);
    console.log(`[options_optimizer] Fetched ${perfData.length} performance records.`);
  } catch (err) {
    console.warn("[options_optimizer] Could not fetch options_strategy_performance:", err.message);
  }

  // Fetch replay results for options
  let replayResults = [];
  try {
    const replayParams = {
      select: "proposal_id,strategy_type,replay_outcome,pnl_pct,asset_type",
      asset_type: "eq.options",
      limit: "500",
    };
    if (strategyType) replayParams["strategy_type"] = `eq.${strategyType}`;
    replayResults = await supabaseQuery("replay_results", replayParams);
    console.log(`[options_optimizer] Fetched ${replayResults.length} replay results.`);
  } catch (err) {
    console.warn("[options_optimizer] Could not fetch replay_results:", err.message);
  }

  // Determine which strategy types to analyze
  const typesToAnalyze = strategyType
    ? [strategyType]
    : Object.keys(OPTIONS_BENCHMARKS);

  // Build performance index by strategy_type
  const perfIndex = {};
  for (const p of perfData) {
    perfIndex[p.strategy_type] = p;
  }

  // Build replay stats by strategy_type
  const replayByType = {};
  for (const r of replayResults) {
    const t = r.strategy_type || "unknown";
    if (!replayByType[t]) replayByType[t] = { wins: 0, total: 0, pnl_pcts: [] };
    replayByType[t].total++;
    if (r.replay_outcome === "tp_hit" || r.replay_outcome === "win") {
      replayByType[t].wins++;
    }
    if (r.pnl_pct != null) replayByType[t].pnl_pcts.push(r.pnl_pct);
  }

  const results = [];

  for (const stype of typesToAnalyze) {
    const benchmark = OPTIONS_BENCHMARKS[stype];
    if (!benchmark) {
      results.push({
        strategy_type: stype,
        sample_count: 0,
        parameter_name: "unknown",
        original_value: null,
        suggested_value: null,
        improvement_score: 0,
        notes: `No benchmark defined for strategy type: ${stype}`,
      });
      continue;
    }

    const perf = perfIndex[stype];
    const replay = replayByType[stype];
    const typeProposals = proposals.filter((p) => p.strategy_type === stype);
    const sampleCount =
      perf?.trades_count || replay?.total || typeProposals.length;

    // Generate parameter suggestions vs benchmark
    const suggestions = generateOptionsParameterSuggestions(
      stype,
      benchmark,
      perf,
      replay,
      typeProposals
    );

    for (const suggestion of suggestions) {
      results.push({
        strategy_type: stype,
        sample_count: sampleCount,
        ...suggestion,
      });
    }

    // If no suggestions generated, add a baseline entry
    if (suggestions.length === 0) {
      results.push({
        strategy_type: stype,
        sample_count: sampleCount,
        parameter_name: "general",
        original_value: null,
        suggested_value: null,
        improvement_score: sampleCount < 5 ? 0 : 10,
        notes:
          sampleCount < 5
            ? `Insufficient data (${sampleCount} samples) — need at least 5 for optimization.`
            : `Parameters appear aligned with benchmarks. ${benchmark.notes}`,
      });
    }
  }

  // Sort by improvement_score descending
  results.sort((a, b) => b.improvement_score - a.improvement_score);

  console.log(
    `[options_optimizer] Analysis complete — ${results.length} suggestions generated.`
  );
  return results;
}

// ---------------------------------------------------------------------------
// Parameter suggestion logic
// ---------------------------------------------------------------------------
function generateOptionsParameterSuggestions(stype, benchmark, perf, replay, proposals) {
  const suggestions = [];
  const winRate = perf ? (perf.wins / Math.max(perf.trades_count, 1)) : null;
  const replayWinRate = replay ? (replay.wins / Math.max(replay.total, 1)) : null;

  // Evaluate win rate vs expected benchmark
  const expectedWinRate = getExpectedWinRate(stype);
  const effectiveWinRate = replayWinRate ?? winRate;

  if (effectiveWinRate != null && expectedWinRate != null) {
    const gap = expectedWinRate - effectiveWinRate;

    if (gap > 0.1) {
      // Win rate underperforming — suggest tightening parameters
      if (benchmark.optimal_strike_otm_pct != null) {
        suggestions.push({
          parameter_name: "strike_otm_pct",
          original_value: null,
          suggested_value: parseFloat(
            (benchmark.optimal_strike_otm_pct * 0.8).toFixed(4)
          ),
          improvement_score: Math.min(100, Math.round(gap * 200)),
          notes: `Win rate ${(effectiveWinRate * 100).toFixed(1)}% below expected ${(expectedWinRate * 100).toFixed(1)}%. Move strike closer to money (reduce OTM %) to improve hit rate. Benchmark: ${benchmark.notes}`,
        });
      }
      if (benchmark.optimal_dte != null) {
        suggestions.push({
          parameter_name: "dte",
          original_value: null,
          suggested_value: Math.round(benchmark.optimal_dte * 1.2),
          improvement_score: Math.min(80, Math.round(gap * 150)),
          notes: `Extend DTE by ~20% to give trades more time to resolve favorably. Benchmark DTE: ${benchmark.optimal_dte}.`,
        });
      }
    } else if (gap < -0.1) {
      // Win rate outperforming — may be leaving money on table
      if (benchmark.optimal_strike_otm_pct != null) {
        suggestions.push({
          parameter_name: "strike_otm_pct",
          original_value: null,
          suggested_value: parseFloat(
            (benchmark.optimal_strike_otm_pct * 1.2).toFixed(4)
          ),
          improvement_score: Math.min(60, Math.round(Math.abs(gap) * 100)),
          notes: `Win rate ${(effectiveWinRate * 100).toFixed(1)}% exceeds expected. Consider moving strike further OTM to collect more premium while maintaining edge. Benchmark: ${benchmark.notes}`,
        });
      }
    }
  }

  // Premium/credit analysis
  if (benchmark.target_premium_pct != null || benchmark.target_credit_pct != null) {
    const targetPct = benchmark.target_premium_pct ?? benchmark.target_credit_pct;
    const avgPnlPct = replay?.pnl_pcts?.length
      ? replay.pnl_pcts.reduce((a, b) => a + b, 0) / replay.pnl_pcts.length
      : perf?.avg_pnl_pct;

    if (avgPnlPct != null && Math.abs(avgPnlPct - targetPct * 100) > 0.5) {
      suggestions.push({
        parameter_name: "target_premium_pct",
        original_value: parseFloat((avgPnlPct / 100).toFixed(4)),
        suggested_value: parseFloat(targetPct.toFixed(4)),
        improvement_score: Math.min(
          70,
          Math.round(Math.abs(avgPnlPct - targetPct * 100) * 10)
        ),
        notes: `Current avg P&L ${(avgPnlPct).toFixed(2)}% vs benchmark target ${(targetPct * 100).toFixed(2)}%. ${benchmark.notes}`,
      });
    }
  }

  // ZEBRA-specific: delta analysis
  if (stype === "zebra_strategy" && benchmark.optimal_delta != null) {
    suggestions.push({
      parameter_name: "long_leg_delta",
      original_value: null,
      suggested_value: benchmark.optimal_delta,
      improvement_score: 40,
      notes: `Ensure long LEAPS leg is at ${benchmark.optimal_delta} delta (deep ITM). ${benchmark.notes}`,
    });
  }

  return suggestions;
}

function getExpectedWinRate(strategyType) {
  const benchmarkWinRates = {
    covered_call: 0.75,
    cash_secured_put: 0.70,
    iron_condor: 0.65,
    credit_spread: 0.60,
    zebra_strategy: 0.55,
    wheel_strategy: 0.72,
  };
  return benchmarkWinRates[strategyType] ?? null;
}
