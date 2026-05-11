// optimizer_writer.js — Writes optimization results to Supabase
// RESEARCH ONLY — no live trading, no broker execution, no order placement

import "dotenv/config";

const SUPABASE_URL = process.env.SUPABASE_URL;
const SUPABASE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || process.env.SUPABASE_KEY;

// ---------------------------------------------------------------------------
// Supabase helpers
// ---------------------------------------------------------------------------
async function supabaseInsert(table, record) {
  const res = await fetch(`${SUPABASE_URL}/rest/v1/${table}`, {
    method: "POST",
    headers: {
      apikey: SUPABASE_KEY,
      Authorization: `Bearer ${SUPABASE_KEY}`,
      "Content-Type": "application/json",
      Prefer: "return=representation",
    },
    body: JSON.stringify(record),
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Supabase insert failed [${res.status}] on ${table}: ${text}`);
  }
  return res.json();
}

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
// writeOptimization
// ---------------------------------------------------------------------------
/**
 * Inserts a single optimization suggestion into strategy_optimizations.
 *
 * @param {Object} optimization
 *   {
 *     strategy_id,        // string — strategy identifier
 *     asset_type,         // "forex" | "options" (default: "forex")
 *     optimization_type,  // e.g. "sl_tp" | "threshold" | "options_structure" | "confidence"
 *     parameter_name,     // e.g. "rr_ratio" | "approval_threshold"
 *     original_value,     // numeric — current value (null if unknown)
 *     suggested_value,    // numeric — recommended value
 *     improvement_score,  // 0-100
 *     notes               // text description
 *   }
 * @returns {Promise<Object>}  The inserted record
 */
export async function writeOptimization(optimization) {
  const record = {
    strategy_id: optimization.strategy_id ?? null,
    asset_type: optimization.asset_type ?? "forex",
    optimization_type: optimization.optimization_type ?? null,
    parameter_name: optimization.parameter_name ?? null,
    original_value: optimization.original_value ?? null,
    suggested_value: optimization.suggested_value ?? null,
    improvement_score: optimization.improvement_score ?? 0,
    notes: optimization.notes ?? null,
  };

  console.log(
    `[optimizer_writer] Writing optimization: ${record.strategy_id} / ${record.parameter_name} ` +
      `(score: ${record.improvement_score})`
  );

  const result = await supabaseInsert("strategy_optimizations", record);
  return Array.isArray(result) ? result[0] : result;
}

// ---------------------------------------------------------------------------
// writeOptimizationBatch
// ---------------------------------------------------------------------------
/**
 * Writes multiple optimization records in a single batch insert.
 *
 * @param {Array} optimizations  Array of optimization objects (same shape as writeOptimization)
 * @returns {Promise<Array>}  Array of inserted records
 */
export async function writeOptimizationBatch(optimizations) {
  if (!optimizations || optimizations.length === 0) {
    console.log("[optimizer_writer] No optimizations to write.");
    return [];
  }

  const records = optimizations.map((opt) => ({
    strategy_id: opt.strategy_id ?? null,
    asset_type: opt.asset_type ?? "forex",
    optimization_type: opt.optimization_type ?? null,
    parameter_name: opt.parameter_name ?? null,
    original_value: opt.original_value ?? null,
    suggested_value: opt.suggested_value ?? null,
    improvement_score: opt.improvement_score ?? 0,
    notes: opt.notes ?? null,
  }));

  console.log(`[optimizer_writer] Writing batch of ${records.length} optimizations...`);

  const res = await fetch(`${SUPABASE_URL}/rest/v1/strategy_optimizations`, {
    method: "POST",
    headers: {
      apikey: SUPABASE_KEY,
      Authorization: `Bearer ${SUPABASE_KEY}`,
      "Content-Type": "application/json",
      Prefer: "return=representation",
    },
    body: JSON.stringify(records),
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(
      `Supabase batch insert failed [${res.status}] on strategy_optimizations: ${text}`
    );
  }

  const inserted = await res.json();
  console.log(`[optimizer_writer] Batch write complete — ${inserted.length} records inserted.`);
  return inserted;
}

// ---------------------------------------------------------------------------
// writeVariant
// ---------------------------------------------------------------------------
/**
 * Inserts a strategy variant into strategy_variants.
 *
 * @param {Object} variant
 *   {
 *     strategy_id,    // string — parent strategy identifier
 *     variant_name,   // string — e.g. "conservative_rr_2.0" | "aggressive_rr_3.5"
 *     parameter_set,  // Object (JSONB) — the variant's parameter configuration
 *     backtest_score, // numeric — performance score from backtesting
 *     replay_score    // numeric — performance score from replay simulation
 *   }
 * @returns {Promise<Object>}  The inserted record
 */
export async function writeVariant(variant) {
  const record = {
    strategy_id: variant.strategy_id ?? null,
    variant_name: variant.variant_name ?? null,
    parameter_set: variant.parameter_set ?? {},
    backtest_score: variant.backtest_score ?? null,
    replay_score: variant.replay_score ?? null,
  };

  console.log(
    `[optimizer_writer] Writing variant: ${record.strategy_id} / ${record.variant_name} ` +
      `(replay_score: ${record.replay_score ?? "n/a"})`
  );

  const result = await supabaseInsert("strategy_variants", record);
  return Array.isArray(result) ? result[0] : result;
}

// ---------------------------------------------------------------------------
// getRecentOptimizations
// ---------------------------------------------------------------------------
/**
 * Reads recent strategy_optimizations ordered by improvement_score DESC.
 *
 * @param {number} limit  Max records to return (default: 10)
 * @returns {Promise<Array>}  Array of optimization records
 */
export async function getRecentOptimizations(limit = 10) {
  console.log(`[optimizer_writer] Fetching top ${limit} recent optimizations...`);

  const records = await supabaseQuery("strategy_optimizations", {
    select:
      "id,strategy_id,asset_type,optimization_type,parameter_name,original_value,suggested_value,improvement_score,notes,created_at",
    order: "improvement_score.desc",
    limit: String(limit),
  });

  console.log(`[optimizer_writer] Fetched ${records.length} optimization records.`);
  return records;
}

// ---------------------------------------------------------------------------
// getRecentVariants
// ---------------------------------------------------------------------------
/**
 * Reads recent strategy_variants ordered by replay_score DESC.
 *
 * @param {number} limit  Max records to return (default: 10)
 * @returns {Promise<Array>}  Array of variant records
 */
export async function getRecentVariants(limit = 10) {
  console.log(`[optimizer_writer] Fetching top ${limit} recent variants...`);

  const records = await supabaseQuery("strategy_variants", {
    select:
      "id,strategy_id,variant_name,parameter_set,backtest_score,replay_score,created_at",
    order: "replay_score.desc",
    limit: String(limit),
  });

  console.log(`[optimizer_writer] Fetched ${records.length} variant records.`);
  return records;
}
