import "dotenv/config";

// ── SAFETY GUARD ──────────────────────────────────────────────────────────────
// This module is RESEARCH ONLY. Reads from Supabase. No trading, no execution.
// ─────────────────────────────────────────────────────────────────────────────

const SUPABASE_URL = process.env.SUPABASE_URL;
const SUPABASE_KEY = process.env.SUPABASE_KEY;

function readHeaders() {
  return {
    apikey: SUPABASE_KEY,
    Authorization: `Bearer ${SUPABASE_KEY}`,
  };
}

async function safeFetch(url, label) {
  try {
    const res = await fetch(url, { headers: readHeaders() });
    if (!res.ok) {
      const body = await res.text();
      console.warn(`[poll] ${label} fetch failed (${res.status}): ${body}`);
      return [];
    }
    return res.json();
  } catch (err) {
    console.warn(`[poll] ${label} fetch error: ${err.message}`);
    return [];
  }
}

/**
 * Polls all research input tables from Supabase.
 * @param {number} limit - Max artifacts/claims to fetch (default 20)
 * @returns {Promise<{artifacts, claims, optimizations, replayResults, scorecards, calibration}>}
 */
export async function pollResearchInputs(limit = 20) {
  if (!SUPABASE_URL || !SUPABASE_KEY) {
    console.warn("[poll] SUPABASE_URL or SUPABASE_KEY not set. Returning empty inputs.");
    return {
      artifacts: [],
      claims: [],
      optimizations: [],
      replayResults: [],
      scorecards: [],
      calibration: [],
    };
  }

  console.log(`[poll] Fetching research inputs (limit=${limit})...`);

  // research_artifacts
  const artifactsUrl =
    `${SUPABASE_URL}/rest/v1/research_artifacts` +
    `?select=id,title,summary,source_type,created_at` +
    `&order=created_at.desc` +
    `&limit=${limit}`;

  // research_claims — gracefully handle missing columns
  const claimsUrl =
    `${SUPABASE_URL}/rest/v1/research_claims` +
    `?select=id,artifact_id,claim_text,claim_type,created_at` +
    `&order=created_at.desc` +
    `&limit=${limit}`;

  // strategy_optimizations
  const optimizationsUrl =
    `${SUPABASE_URL}/rest/v1/strategy_optimizations` +
    `?select=strategy_id,optimization_type,parameter_name,improvement_score,notes` +
    `&order=improvement_score.desc` +
    `&limit=10`;

  // replay_results
  const replayUrl =
    `${SUPABASE_URL}/rest/v1/replay_results` +
    `?select=strategy_id,replay_outcome,pnl_r,asset_type` +
    `&order=created_at.desc` +
    `&limit=20`;

  // agent_scorecards
  const scorecardsUrl =
    `${SUPABASE_URL}/rest/v1/agent_scorecards` +
    `?select=agent_name,metric_type,metric_value,period`;

  // confidence_calibration
  const calibrationUrl =
    `${SUPABASE_URL}/rest/v1/confidence_calibration` +
    `?select=confidence_band,actual_win_rate,expected_win_rate,calibration_gap`;

  const [artifacts, rawClaims, optimizations, replayResults, scorecards, calibration] =
    await Promise.all([
      safeFetch(artifactsUrl, "research_artifacts"),
      safeFetch(claimsUrl, "research_claims"),
      safeFetch(optimizationsUrl, "strategy_optimizations"),
      safeFetch(replayUrl, "replay_results"),
      safeFetch(scorecardsUrl, "agent_scorecards"),
      safeFetch(calibrationUrl, "confidence_calibration"),
    ]);

  // Gracefully handle missing claim_text / claim_type columns
  let claims = [];
  if (Array.isArray(rawClaims)) {
    claims = rawClaims.filter(
      (c) => c && typeof c.claim_text !== "undefined" && typeof c.claim_type !== "undefined"
    );
    if (claims.length === 0 && rawClaims.length > 0) {
      console.warn("[poll] research_claims returned rows but claim_text/claim_type columns missing — treating as empty.");
    }
  }

  console.log(
    `[poll] Fetched: artifacts=${artifacts.length}, claims=${claims.length}, ` +
    `optimizations=${optimizations.length}, replayResults=${replayResults.length}, ` +
    `scorecards=${scorecards.length}, calibration=${calibration.length}`
  );

  return { artifacts, claims, optimizations, replayResults, scorecards, calibration };
}
