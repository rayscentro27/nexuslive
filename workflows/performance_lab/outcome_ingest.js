import "dotenv/config";
import { readFile } from "fs/promises";

const SUPABASE_URL = process.env.SUPABASE_URL;
const SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;

const VALID_STATUSES = new Set(["win", "loss", "breakeven", "expired"]);

function serviceHeaders() {
  return {
    apikey: SUPABASE_SERVICE_ROLE_KEY,
    Authorization: `Bearer ${SUPABASE_SERVICE_ROLE_KEY}`,
    "Content-Type": "application/json",
    Prefer: "resolution=merge-duplicates",
  };
}

function validateOutcome(outcome) {
  const required = ["proposal_id", "symbol", "strategy_id", "outcome_status"];
  for (const field of required) {
    if (!outcome[field]) {
      throw new Error(`Missing required field: ${field}`);
    }
  }
  if (!VALID_STATUSES.has(outcome.outcome_status)) {
    throw new Error(
      `Invalid outcome_status "${outcome.outcome_status}". Must be one of: ${[...VALID_STATUSES].join(", ")}`
    );
  }
}

function buildRow(outcome) {
  return {
    proposal_id: outcome.proposal_id,
    symbol: outcome.symbol,
    strategy_id: outcome.strategy_id,
    asset_type: outcome.asset_type ?? null,
    outcome_status: outcome.outcome_status,
    pnl_r: outcome.pnl_r ?? null,
    pnl_pct: outcome.pnl_pct ?? null,
    mfe: outcome.mfe ?? null,
    mae: outcome.mae ?? null,
    notes: outcome.notes ?? null,
    trace_id: outcome.trace_id ?? null,
    recorded_at: new Date().toISOString(),
  };
}

async function upsertOutcome(row) {
  const url = `${SUPABASE_URL}/rest/v1/proposal_outcomes`;
  const res = await fetch(url, {
    method: "POST",
    headers: serviceHeaders(),
    body: JSON.stringify(row),
  });

  if (!res.ok) {
    const body = await res.text();
    throw new Error(`Upsert failed (${res.status}): ${body}`);
  }
}

/**
 * Reads a JSON file of outcomes and writes each to proposal_outcomes.
 * @param {string} filePath - Path to JSON array file
 * @returns {{ inserted: number, skipped: number, errors: string[] }}
 */
export async function ingestOutcomeFile(filePath) {
  console.log(`[ingest] Reading outcome file: ${filePath}`);

  let items;
  try {
    const raw = await readFile(filePath, "utf8");
    items = JSON.parse(raw);
  } catch (err) {
    throw new Error(`Failed to read/parse outcome file: ${err.message}`);
  }

  if (!Array.isArray(items)) {
    throw new Error("Outcome file must contain a JSON array.");
  }

  console.log(`[ingest] Found ${items.length} outcome(s) to process.`);

  const results = { inserted: 0, skipped: 0, errors: [] };

  for (const item of items) {
    try {
      validateOutcome(item);
      const row = buildRow(item);
      await upsertOutcome(row);
      results.inserted++;
      console.log(`[ingest] Upserted outcome for proposal_id=${item.proposal_id} (${item.outcome_status})`);
    } catch (err) {
      results.errors.push(`proposal_id=${item.proposal_id ?? "unknown"}: ${err.message}`);
      results.skipped++;
      console.warn(`[ingest] Skipped: ${err.message}`);
    }
  }

  console.log(`[ingest] Complete — inserted: ${results.inserted}, skipped: ${results.skipped}, errors: ${results.errors.length}`);
  return results;
}

/**
 * Ingests a single outcome object into proposal_outcomes.
 * @param {Object} outcome
 * @returns {{ inserted: number, skipped: number, errors: string[] }}
 */
export async function ingestSingleOutcome(outcome) {
  const results = { inserted: 0, skipped: 0, errors: [] };

  try {
    validateOutcome(outcome);
    const row = buildRow(outcome);
    await upsertOutcome(row);
    results.inserted = 1;
    console.log(`[ingest] Upserted outcome for proposal_id=${outcome.proposal_id} (${outcome.outcome_status})`);
  } catch (err) {
    results.errors.push(err.message);
    results.skipped = 1;
    console.warn(`[ingest] Failed: ${err.message}`);
  }

  return results;
}
