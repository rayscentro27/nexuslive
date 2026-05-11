import "dotenv/config";

const SUPABASE_URL = process.env.SUPABASE_URL;
const SUPABASE_KEY = process.env.SUPABASE_KEY;

function supabaseHeaders() {
  return {
    apikey: SUPABASE_KEY,
    Authorization: `Bearer ${SUPABASE_KEY}`,
    "Content-Type": "application/json",
  };
}

async function supabaseGet(table, params = "") {
  const url = `${SUPABASE_URL}/rest/v1/${table}${params ? "?" + params : ""}`;
  const res = await fetch(url, { headers: supabaseHeaders() });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`Supabase GET ${table} failed (${res.status}): ${body}`);
  }
  return res.json();
}

function mean(arr) {
  if (!arr.length) return 0;
  return arr.reduce((a, b) => a + b, 0) / arr.length;
}

function clamp(val, min, max) {
  return Math.max(min, Math.min(max, val));
}

function rankingLabel(score) {
  if (score >= 80) return "elite";
  if (score >= 65) return "strong";
  if (score >= 45) return "average";
  if (score >= 25) return "weak";
  return "poor";
}

/**
 * Computes per-strategy-type options performance metrics from proposal_outcomes.
 * @param {string|null} strategyType - Optional filter by strategy_id (used as strategy_type for options)
 * @returns {Promise<Array>} Array of options metric objects sorted by score desc
 */
export async function computeOptionsMetrics(strategyType = null) {
  console.log("[options-metrics] Fetching options outcomes from Supabase...");

  let params =
    "asset_type=eq.options&select=strategy_id,outcome_status,pnl_r,pnl_pct";
  if (strategyType) {
    params += `&strategy_id=eq.${encodeURIComponent(strategyType)}`;
  }

  const outcomes = await supabaseGet("proposal_outcomes", params).catch((err) => {
    console.warn("[options-metrics] proposal_outcomes fetch failed:", err.message);
    return [];
  });

  if (!outcomes.length) {
    console.log("[options-metrics] No options outcomes found. Returning empty metrics.");
    return [];
  }

  // Group by strategy_id (interpreted as strategy_type for options)
  const byType = new Map();
  for (const row of outcomes) {
    const sid = row.strategy_id ?? "unknown";
    if (!byType.has(sid)) byType.set(sid, []);
    byType.get(sid).push(row);
  }

  const maxTrades = Math.max(...[...byType.values()].map((arr) => arr.length));

  const metrics = [];

  for (const [sid, rows] of byType.entries()) {
    const wins = rows.filter((r) => r.outcome_status === "win");
    const losses = rows.filter((r) => r.outcome_status === "loss");

    const trades_count = rows.length;
    const win_rate = trades_count > 0 ? wins.length / trades_count : 0;

    const pnlPctValues = rows
      .map((r) => r.pnl_pct)
      .filter((v) => v !== null && v !== undefined);
    const avg_pnl_pct = mean(pnlPctValues);

    // Score: win_rate 50%, avg_pnl_pct normalized 30%, trade count 20%
    const winRateComponent = clamp(win_rate * 100, 0, 100);
    // Normalize avg_pnl_pct: clamp to [-50%, 50%] then map to 0-100
    const pnlNorm = clamp(((avg_pnl_pct + 50) / 100) * 100, 0, 100);
    const tradesNorm =
      maxTrades > 0 ? clamp((trades_count / maxTrades) * 100, 0, 100) : 0;

    const score = clamp(
      winRateComponent * 0.5 + pnlNorm * 0.3 + tradesNorm * 0.2,
      0,
      100
    );

    metrics.push({
      strategy_type: sid,
      asset_type: "options",
      trades_count,
      wins: wins.length,
      losses: losses.length,
      win_rate: parseFloat(win_rate.toFixed(4)),
      avg_pnl_pct: parseFloat(avg_pnl_pct.toFixed(4)),
      score: parseFloat(score.toFixed(2)),
      ranking_label: rankingLabel(score),
    });
  }

  metrics.sort((a, b) => b.score - a.score);
  console.log(`[options-metrics] Computed metrics for ${metrics.length} options strategy types.`);
  return metrics;
}
