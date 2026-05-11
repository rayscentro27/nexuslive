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

/**
 * Returns a ranking label based on a 0-100 score.
 */
function rankingLabel(score) {
  if (score >= 80) return "elite";
  if (score >= 65) return "strong";
  if (score >= 45) return "average";
  if (score >= 25) return "weak";
  return "poor";
}

/**
 * Computes per-strategy forex performance metrics from proposal_outcomes.
 * @param {string|null} strategyId - Optional filter by strategy_id
 * @returns {Promise<Array>} Array of strategy metric objects sorted by score desc
 */
export async function computeForexMetrics(strategyId = null) {
  console.log("[forex-metrics] Fetching forex outcomes from Supabase...");

  let params =
    "asset_type=eq.forex&select=strategy_id,outcome_status,pnl_r,pnl_pct";
  if (strategyId) {
    params += `&strategy_id=eq.${encodeURIComponent(strategyId)}`;
  }

  const outcomes = await supabaseGet("proposal_outcomes", params).catch((err) => {
    console.warn("[forex-metrics] proposal_outcomes fetch failed:", err.message);
    return [];
  });

  if (!outcomes.length) {
    console.log("[forex-metrics] No forex outcomes found. Returning empty metrics.");
    return [];
  }

  // Group by strategy_id
  const byStrategy = new Map();
  for (const row of outcomes) {
    const sid = row.strategy_id ?? "unknown";
    if (!byStrategy.has(sid)) byStrategy.set(sid, []);
    byStrategy.get(sid).push(row);
  }

  const maxTrades = Math.max(...[...byStrategy.values()].map((arr) => arr.length));

  const metrics = [];

  for (const [sid, rows] of byStrategy.entries()) {
    const wins = rows.filter((r) => r.outcome_status === "win");
    const losses = rows.filter((r) => r.outcome_status === "loss");
    const breakevens = rows.filter((r) => r.outcome_status === "breakeven");

    const trades_count = rows.length;
    const win_rate = trades_count > 0 ? wins.length / trades_count : 0;

    const pnlRValues = rows
      .map((r) => r.pnl_r)
      .filter((v) => v !== null && v !== undefined);
    const avgPnlR = mean(pnlRValues);

    const winPnlR = wins
      .map((r) => r.pnl_r)
      .filter((v) => v !== null && v !== undefined);
    const lossPnlR = losses
      .map((r) => r.pnl_r)
      .filter((v) => v !== null && v !== undefined);

    const avg_win_r = mean(winPnlR);
    const avg_loss_r = mean(lossPnlR.map(Math.abs)); // abs so loss is positive magnitude

    // Expectancy = (win_rate * avg_win_r) - (loss_rate * avg_loss_r)
    const loss_rate = 1 - win_rate;
    const expectancy = win_rate * avg_win_r - loss_rate * avg_loss_r;

    // Score components (0-100 each, then weighted)
    const winRateComponent = clamp(win_rate * 100, 0, 100); // 0-100
    // Normalize expectancy: clamp to [-2, 2] range then map to 0-100
    const expectancyNorm = clamp(((expectancy + 2) / 4) * 100, 0, 100);
    // Trade count normalization: up to maxTrades gets full points, minimum 5 trades for any credit
    const tradesNorm =
      maxTrades > 0 ? clamp((trades_count / maxTrades) * 100, 0, 100) : 0;

    const score = clamp(
      winRateComponent * 0.4 + expectancyNorm * 0.4 + tradesNorm * 0.2,
      0,
      100
    );

    metrics.push({
      strategy_id: sid,
      asset_type: "forex",
      trades_count,
      wins: wins.length,
      losses: losses.length,
      breakevens: breakevens.length,
      win_rate: parseFloat(win_rate.toFixed(4)),
      avg_pnl_r: parseFloat(avgPnlR.toFixed(4)),
      avg_win_r: parseFloat(avg_win_r.toFixed(4)),
      avg_loss_r: parseFloat(avg_loss_r.toFixed(4)),
      expectancy: parseFloat(expectancy.toFixed(4)),
      score: parseFloat(score.toFixed(2)),
      ranking_label: rankingLabel(score),
    });
  }

  metrics.sort((a, b) => b.score - a.score);
  console.log(`[forex-metrics] Computed metrics for ${metrics.length} forex strategies.`);
  return metrics;
}
