import "dotenv/config";
import { computeForexMetrics } from "./strategy_metrics.js";
import { computeOptionsMetrics } from "./options_metrics.js";

const SUPABASE_URL = process.env.SUPABASE_URL;
const SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;

function serviceHeaders() {
  return {
    apikey: SUPABASE_SERVICE_ROLE_KEY,
    Authorization: `Bearer ${SUPABASE_SERVICE_ROLE_KEY}`,
    "Content-Type": "application/json",
    Prefer: "resolution=merge-duplicates",
  };
}

async function upsertRows(table, rows) {
  if (!rows.length) return;
  const url = `${SUPABASE_URL}/rest/v1/${table}`;
  const res = await fetch(url, {
    method: "POST",
    headers: serviceHeaders(),
    body: JSON.stringify(rows),
  });

  if (!res.ok) {
    const body = await res.text();
    throw new Error(`Upsert to ${table} failed (${res.status}): ${body}`);
  }
}

function printForexTable(rankings) {
  console.log("\n╔══════════════════════════════════════════════════════════════╗");
  console.log("║           FOREX STRATEGY RANKINGS                           ║");
  console.log("╠══════════════════════════════════════════════════════════════╣");
  console.log(
    `║ ${"Rank".padEnd(5)} ${"Strategy".padEnd(20)} ${"WinRate".padEnd(8)} ${"Expcy".padEnd(7)} ${"Score".padEnd(7)} ${"Label".padEnd(8)} ║`
  );
  console.log("╠══════════════════════════════════════════════════════════════╣");

  rankings.forEach((r, i) => {
    const rank = String(i + 1).padEnd(5);
    const strategy = (r.strategy_id ?? "unknown").slice(0, 19).padEnd(20);
    const winRate = `${(r.win_rate * 100).toFixed(1)}%`.padEnd(8);
    const expcy = r.expectancy.toFixed(3).padEnd(7);
    const score = r.score.toFixed(1).padEnd(7);
    const label = (r.ranking_label ?? "").padEnd(8);
    console.log(`║ ${rank} ${strategy} ${winRate} ${expcy} ${score} ${label} ║`);
  });

  console.log("╚══════════════════════════════════════════════════════════════╝\n");
}

function printOptionsTable(rankings) {
  console.log("\n╔══════════════════════════════════════════════════════════════╗");
  console.log("║           OPTIONS STRATEGY RANKINGS                         ║");
  console.log("╠══════════════════════════════════════════════════════════════╣");
  console.log(
    `║ ${"Rank".padEnd(5)} ${"Strategy".padEnd(20)} ${"WinRate".padEnd(8)} ${"AvgPnl%".padEnd(8)} ${"Score".padEnd(7)} ${"Label".padEnd(8)} ║`
  );
  console.log("╠══════════════════════════════════════════════════════════════╣");

  rankings.forEach((r, i) => {
    const rank = String(i + 1).padEnd(5);
    const strategy = (r.strategy_type ?? "unknown").slice(0, 19).padEnd(20);
    const winRate = `${(r.win_rate * 100).toFixed(1)}%`.padEnd(8);
    const avgPnl = `${r.avg_pnl_pct.toFixed(1)}%`.padEnd(8);
    const score = r.score.toFixed(1).padEnd(7);
    const label = (r.ranking_label ?? "").padEnd(8);
    console.log(`║ ${rank} ${strategy} ${winRate} ${avgPnl} ${score} ${label} ║`);
  });

  console.log("╚══════════════════════════════════════════════════════════════╝\n");
}

/**
 * Ranks forex strategies, upserts to strategy_performance, logs ranking table.
 * @returns {Promise<Array>} Sorted array of forex strategy metrics
 */
export async function rankForexStrategies() {
  console.log("[ranking] Computing forex strategy rankings...");

  const metrics = await computeForexMetrics();

  if (!metrics.length) {
    console.log("[ranking] No forex metrics to rank.");
    return [];
  }

  // Add ranked_at timestamp
  const rows = metrics.map((m, i) => ({
    ...m,
    rank: i + 1,
    ranked_at: new Date().toISOString(),
  }));

  try {
    await upsertRows("strategy_performance", rows);
    console.log(`[ranking] Upserted ${rows.length} forex strategy rows to strategy_performance.`);
  } catch (err) {
    console.warn(`[ranking] Failed to upsert forex rankings: ${err.message}`);
  }

  printForexTable(metrics);
  return metrics;
}

/**
 * Ranks options strategies, upserts to options_strategy_performance, logs ranking table.
 * @returns {Promise<Array>} Sorted array of options strategy metrics
 */
export async function rankOptionsStrategies() {
  console.log("[ranking] Computing options strategy rankings...");

  const metrics = await computeOptionsMetrics();

  if (!metrics.length) {
    console.log("[ranking] No options metrics to rank.");
    return [];
  }

  const rows = metrics.map((m, i) => ({
    ...m,
    rank: i + 1,
    ranked_at: new Date().toISOString(),
  }));

  try {
    await upsertRows("options_strategy_performance", rows);
    console.log(`[ranking] Upserted ${rows.length} options strategy rows to options_strategy_performance.`);
  } catch (err) {
    console.warn(`[ranking] Failed to upsert options rankings: ${err.message}`);
  }

  printOptionsTable(metrics);
  return metrics;
}
