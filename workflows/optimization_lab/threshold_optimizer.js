// threshold_optimizer.js — Risk and confidence threshold optimizer
// RESEARCH ONLY — no live trading, no broker execution, no order placement

import "dotenv/config";

const SUPABASE_URL = process.env.SUPABASE_URL;
const SUPABASE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || process.env.SUPABASE_KEY;

// Current threshold configuration (production defaults)
const CURRENT_APPROVAL_THRESHOLD = 70;
const CURRENT_REVIEW_THRESHOLD = 40;
const CURRENT_MIN_CONFIDENCE = 0.60;

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
// analyzeRiskThresholds
// ---------------------------------------------------------------------------
/**
 * Analyzes which risk_score thresholds correlate with best outcomes.
 *
 * Reads risk_decisions cross-referenced with replay_results.
 *
 * @returns {Promise<Object>}
 *   {
 *     current_approval_threshold, suggested_approval_threshold,
 *     current_review_threshold,   suggested_review_threshold,
 *     sample_count,
 *     improvement_note
 *   }
 */
export async function analyzeRiskThresholds() {
  console.log("[threshold_optimizer] Fetching risk_decisions...");

  let riskDecisions = [];
  try {
    riskDecisions = await supabaseQuery("risk_decisions", {
      select: "id,proposal_id,risk_score,decision,created_at",
      order: "created_at.desc",
      limit: "500",
    });
    console.log(`[threshold_optimizer] Fetched ${riskDecisions.length} risk decisions.`);
  } catch (err) {
    console.warn("[threshold_optimizer] Could not fetch risk_decisions:", err.message);
    return buildDefaultRiskThresholdResult(0);
  }

  if (riskDecisions.length === 0) {
    return buildDefaultRiskThresholdResult(0);
  }

  // Fetch replay results for cross-reference
  let replayResults = [];
  try {
    replayResults = await supabaseQuery("replay_results", {
      select: "proposal_id,replay_outcome,pnl_r",
      limit: "1000",
    });
    console.log(`[threshold_optimizer] Fetched ${replayResults.length} replay results.`);
  } catch (err) {
    console.warn("[threshold_optimizer] Could not fetch replay_results:", err.message);
  }

  // Build replay index: proposal_id → outcome
  const replayIndex = {};
  for (const r of replayResults) {
    if (r.proposal_id) replayIndex[r.proposal_id] = r;
  }

  // Only analyze decisions that have replay outcomes
  const linked = riskDecisions.filter(
    (d) => d.proposal_id && replayIndex[d.proposal_id]
  );

  console.log(
    `[threshold_optimizer] ${linked.length} risk decisions linked to replay outcomes.`
  );

  if (linked.length < 5) {
    return buildDefaultRiskThresholdResult(riskDecisions.length);
  }

  // Bucket risk scores into 10-point bands and compute win rates
  const buckets = {};
  for (const d of linked) {
    if (d.risk_score == null) continue;
    const band = Math.floor(d.risk_score / 10) * 10;
    if (!buckets[band]) buckets[band] = { wins: 0, total: 0 };
    buckets[band].total++;
    const replay = replayIndex[d.proposal_id];
    if (replay.replay_outcome === "tp_hit" || replay.replay_outcome === "win") {
      buckets[band].wins++;
    }
  }

  // Find the threshold that maximizes expected value
  // Strategy: find the lowest risk_score band with win_rate >= 0.55
  let suggestedApprovalThreshold = CURRENT_APPROVAL_THRESHOLD;
  let suggestedReviewThreshold = CURRENT_REVIEW_THRESHOLD;

  const sortedBands = Object.keys(buckets)
    .map(Number)
    .sort((a, b) => a - b);

  // Find optimal approval threshold: lowest band where win_rate >= 0.55
  let approvalBandFound = false;
  for (const band of sortedBands) {
    const bucket = buckets[band];
    if (bucket.total < 2) continue;
    const wr = bucket.wins / bucket.total;
    if (wr >= 0.55 && !approvalBandFound) {
      suggestedApprovalThreshold = band;
      approvalBandFound = true;
    }
  }

  // Review threshold: half of approval threshold
  suggestedReviewThreshold = Math.round(suggestedApprovalThreshold * 0.5);

  // Build summary
  const bucketSummary = sortedBands
    .filter((b) => buckets[b].total >= 2)
    .map((b) => {
      const { wins, total } = buckets[b];
      return `${b}-${b + 9}: ${(wins / total * 100).toFixed(0)}% win (n=${total})`;
    })
    .join(", ");

  const thresholdChanged =
    suggestedApprovalThreshold !== CURRENT_APPROVAL_THRESHOLD ||
    suggestedReviewThreshold !== CURRENT_REVIEW_THRESHOLD;

  const improvementNote = thresholdChanged
    ? `Data suggests adjusting approval threshold from ${CURRENT_APPROVAL_THRESHOLD} → ${suggestedApprovalThreshold} ` +
      `and review threshold from ${CURRENT_REVIEW_THRESHOLD} → ${suggestedReviewThreshold}. ` +
      `Win rate by band: ${bucketSummary || "insufficient data"}.`
    : `Current thresholds (approval: ${CURRENT_APPROVAL_THRESHOLD}, review: ${CURRENT_REVIEW_THRESHOLD}) ` +
      `appear well-calibrated. Win rate by band: ${bucketSummary || "insufficient data"}.`;

  return {
    current_approval_threshold: CURRENT_APPROVAL_THRESHOLD,
    suggested_approval_threshold: suggestedApprovalThreshold,
    current_review_threshold: CURRENT_REVIEW_THRESHOLD,
    suggested_review_threshold: suggestedReviewThreshold,
    sample_count: linked.length,
    improvement_note: improvementNote,
  };
}

// ---------------------------------------------------------------------------
// analyzeConfidenceThresholds
// ---------------------------------------------------------------------------
/**
 * Analyzes which ai_confidence levels correlate with winning outcomes.
 *
 * Reads reviewed_signal_proposals cross-referenced with replay_results.
 *
 * @returns {Promise<Object>}
 *   {
 *     current_min_confidence, suggested_min_confidence,
 *     sample_count,
 *     improvement_note
 *   }
 */
export async function analyzeConfidenceThresholds() {
  console.log("[threshold_optimizer] Fetching proposals for confidence analysis...");

  let proposals = [];
  try {
    proposals = await supabaseQuery("reviewed_signal_proposals", {
      select: "id,ai_confidence,strategy_id,asset_type",
      order: "created_at.desc",
      limit: "500",
    });
    console.log(`[threshold_optimizer] Fetched ${proposals.length} proposals.`);
  } catch (err) {
    console.warn("[threshold_optimizer] Could not fetch proposals:", err.message);
    return buildDefaultConfidenceResult(0);
  }

  if (proposals.length === 0) {
    return buildDefaultConfidenceResult(0);
  }

  // Fetch replay results
  let replayResults = [];
  try {
    replayResults = await supabaseQuery("replay_results", {
      select: "proposal_id,replay_outcome",
      limit: "1000",
    });
  } catch (err) {
    console.warn("[threshold_optimizer] Could not fetch replay_results:", err.message);
  }

  const replayIndex = {};
  for (const r of replayResults) {
    if (r.proposal_id) replayIndex[r.proposal_id] = r;
  }

  // Link proposals to replay outcomes
  const linked = proposals.filter(
    (p) => p.ai_confidence != null && replayIndex[p.id]
  );

  if (linked.length < 5) {
    return buildDefaultConfidenceResult(proposals.length);
  }

  // Bucket confidence into 0.05 bands and compute win rates
  const buckets = {};
  for (const p of linked) {
    const band = Math.floor(p.ai_confidence / 0.05) * 0.05;
    const bandKey = band.toFixed(2);
    if (!buckets[bandKey]) buckets[bandKey] = { wins: 0, total: 0 };
    buckets[bandKey].total++;
    const replay = replayIndex[p.id];
    if (replay.replay_outcome === "tp_hit" || replay.replay_outcome === "win") {
      buckets[bandKey].wins++;
    }
  }

  // Find lowest confidence band with win_rate >= 0.55 (consistent edge)
  const sortedBands = Object.keys(buckets)
    .map(Number)
    .sort((a, b) => a - b);

  let suggestedMinConfidence = CURRENT_MIN_CONFIDENCE;

  for (const band of sortedBands) {
    const bandKey = band.toFixed(2);
    const bucket = buckets[bandKey];
    if (bucket.total < 2) continue;
    const wr = bucket.wins / bucket.total;
    if (wr >= 0.55) {
      suggestedMinConfidence = parseFloat(band.toFixed(2));
      break;
    }
  }

  const bandSummary = sortedBands
    .filter((b) => {
      const k = b.toFixed(2);
      return buckets[k]?.total >= 2;
    })
    .map((b) => {
      const k = b.toFixed(2);
      const { wins, total } = buckets[k];
      return `${k}: ${(wins / total * 100).toFixed(0)}% win (n=${total})`;
    })
    .join(", ");

  const changed = Math.abs(suggestedMinConfidence - CURRENT_MIN_CONFIDENCE) > 0.02;
  const improvementNote = changed
    ? `Data suggests adjusting min confidence from ${CURRENT_MIN_CONFIDENCE} → ${suggestedMinConfidence}. ` +
      `Win rate by confidence band: ${bandSummary || "insufficient data"}.`
    : `Current min confidence ${CURRENT_MIN_CONFIDENCE} appears well-calibrated. ` +
      `Win rate by confidence band: ${bandSummary || "insufficient data"}.`;

  return {
    current_min_confidence: CURRENT_MIN_CONFIDENCE,
    suggested_min_confidence: suggestedMinConfidence,
    sample_count: linked.length,
    improvement_note: improvementNote,
  };
}

// ---------------------------------------------------------------------------
// Default result builders (when data is insufficient)
// ---------------------------------------------------------------------------
function buildDefaultRiskThresholdResult(sampleCount) {
  return {
    current_approval_threshold: CURRENT_APPROVAL_THRESHOLD,
    suggested_approval_threshold: CURRENT_APPROVAL_THRESHOLD,
    current_review_threshold: CURRENT_REVIEW_THRESHOLD,
    suggested_review_threshold: CURRENT_REVIEW_THRESHOLD,
    sample_count: sampleCount,
    improvement_note:
      sampleCount === 0
        ? "No risk decision data found — run replay lab to generate outcome data."
        : `Only ${sampleCount} decisions found — need at least 5 with replay outcomes for threshold analysis.`,
  };
}

function buildDefaultConfidenceResult(sampleCount) {
  return {
    current_min_confidence: CURRENT_MIN_CONFIDENCE,
    suggested_min_confidence: CURRENT_MIN_CONFIDENCE,
    sample_count: sampleCount,
    improvement_note:
      sampleCount === 0
        ? "No proposal data found — run signal review and replay lab first."
        : `Only ${sampleCount} proposals found — need at least 5 with replay outcomes for confidence analysis.`,
  };
}
