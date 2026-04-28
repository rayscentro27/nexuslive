import "dotenv/config";

const SUPABASE_URL = process.env.SUPABASE_URL;
const SUPABASE_KEY = process.env.SUPABASE_KEY;

/**
 * Generates replay-based performance scorecards per strategy.
 * Fetches all replay_results, groups by strategy_id, and computes
 * win_rate and avg_pnl_r for each strategy.
 *
 * Logs a formatted scorecard table to console and returns the array.
 *
 * @returns {Promise<Array<{strategy_id: string, replay_win_rate: number, replay_avg_pnl_r: number, replay_count: number}>>}
 */
export async function generateReplayScorecards() {
  const res = await fetch(
    `${SUPABASE_URL}/rest/v1/replay_results?select=strategy_id,replay_outcome,pnl_r`,
    {
      headers: {
        "Content-Type": "application/json",
        "apikey": SUPABASE_KEY,
        "Authorization": `Bearer ${SUPABASE_KEY}`,
      },
    }
  );

  if (!res.ok) {
    const err = await res.text();
    throw new Error(`generateReplayScorecards: Supabase error: ${err}`);
  }

  const rows = await res.json();

  if (!rows.length) {
    console.log("[scorecards] No replay results found.");
    return [];
  }

  // Group by strategy_id
  const strategyMap = {};
  for (const row of rows) {
    const key = row.strategy_id ?? "unknown";
    if (!strategyMap[key]) {
      strategyMap[key] = { wins: 0, total: 0, pnl_r_values: [] };
    }
    strategyMap[key].total += 1;

    const isWin = row.replay_outcome === "tp_hit" || row.replay_outcome === "win";
    if (isWin) strategyMap[key].wins += 1;

    if (row.pnl_r != null) strategyMap[key].pnl_r_values.push(row.pnl_r);
  }

  const scorecards = Object.entries(strategyMap)
    .map(([strategy_id, data]) => {
      const replay_win_rate = parseFloat((data.wins / data.total).toFixed(4));
      const avg_pnl_r =
        data.pnl_r_values.length > 0
          ? parseFloat(
              (
                data.pnl_r_values.reduce((a, b) => a + b, 0) /
                data.pnl_r_values.length
              ).toFixed(4)
            )
          : null;
      return {
        strategy_id,
        replay_win_rate,
        replay_avg_pnl_r: avg_pnl_r,
        replay_count: data.total,
      };
    })
    .sort((a, b) => b.replay_win_rate - a.replay_win_rate);

  // Print formatted table
  console.log("\n=== NEXUS REPLAY SCORECARDS ===");
  console.log(
    "Strategy".padEnd(22) +
      "Win Rate".padEnd(12) +
      "Avg PnL(R)".padEnd(14) +
      "Count"
  );
  console.log("-".repeat(56));
  for (const sc of scorecards) {
    const winPct = (sc.replay_win_rate * 100).toFixed(1) + "%";
    const pnlR =
      sc.replay_avg_pnl_r != null ? sc.replay_avg_pnl_r.toFixed(3) : "N/A";
    console.log(
      sc.strategy_id.padEnd(22) +
        winPct.padEnd(12) +
        pnlR.padEnd(14) +
        sc.replay_count
    );
  }
  console.log("=".repeat(56) + "\n");

  return scorecards;
}
