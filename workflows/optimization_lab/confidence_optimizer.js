// confidence_optimizer.js — AI confidence calibration analyzer
// RESEARCH ONLY — no live trading, no broker execution, no order placement

import "dotenv/config";

const SUPABASE_URL = process.env.SUPABASE_URL;
const SUPABASE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || process.env.SUPABASE_KEY;

// Calibration quality thresholds
const CALIBRATION_THRESHOLDS = {
  EXCELLENT: 0.05,  // gap <= 5% → excellent
  GOOD: 0.10,       // gap <= 10% → good
  FAIR: 0.15,       // gap <= 15% → fair
  POOR: Infinity,   // gap > 15% → poor
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
// analyzeConfidenceCalibration
// ---------------------------------------------------------------------------
/**
 * Reads the confidence_calibration table and identifies bands where the AI
 * is systematically overconfident or underconfident.
 *
 * @returns {Promise<Object>}
 *   {
 *     overconfident_bands,    // Array of band objects where AI overestimates
 *     underconfident_bands,   // Array of band objects where AI underestimates
 *     max_gap,                // Largest absolute calibration gap found
 *     calibration_quality,    // "excellent"|"good"|"fair"|"poor"
 *     recommendation,
 *     sample_count
 *   }
 */
export async function analyzeConfidenceCalibration() {
  console.log("[confidence_optimizer] Fetching confidence_calibration data...");

  let calibrationData = [];
  try {
    calibrationData = await supabaseQuery("confidence_calibration", {
      select: "*",
      order: "confidence_band.asc",
    });
    console.log(
      `[confidence_optimizer] Fetched ${calibrationData.length} calibration records.`
    );
  } catch (err) {
    console.warn(
      "[confidence_optimizer] Could not fetch confidence_calibration:",
      err.message
    );
    return buildDefaultCalibrationResult();
  }

  if (calibrationData.length === 0) {
    return buildDefaultCalibrationResult();
  }

  // Filter to records with enough samples for meaningful analysis
  const MIN_SAMPLES = 5;
  const usable = calibrationData.filter((r) => r.samples >= MIN_SAMPLES);

  if (usable.length === 0) {
    return {
      overconfident_bands: [],
      underconfident_bands: [],
      max_gap: null,
      calibration_quality: "poor",
      recommendation:
        `All calibration bands have fewer than ${MIN_SAMPLES} samples. ` +
        "Run more signal reviews and replay simulations to build calibration data.",
      sample_count: calibrationData.reduce((s, r) => s + (r.samples || 0), 0),
    };
  }

  const overconfidentBands = [];
  const underconfidentBands = [];
  let maxGap = 0;

  for (const record of usable) {
    // calibration_gap: positive = overconfident, negative = underconfident
    const gap = record.calibration_gap;
    if (gap == null) continue;

    const absGap = Math.abs(gap);
    if (absGap > maxGap) maxGap = absGap;

    const bandInfo = {
      agent_name: record.agent_name,
      confidence_band: record.confidence_band,
      samples: record.samples,
      actual_win_rate: record.actual_win_rate,
      expected_win_rate: record.expected_win_rate,
      calibration_gap: gap,
      abs_gap: absGap,
    };

    if (gap > 0.05) {
      // AI expects higher win rate than actual
      overconfidentBands.push(bandInfo);
    } else if (gap < -0.05) {
      // AI expects lower win rate than actual
      underconfidentBands.push(bandInfo);
    }
  }

  // Sort by magnitude of gap
  overconfidentBands.sort((a, b) => b.abs_gap - a.abs_gap);
  underconfidentBands.sort((a, b) => b.abs_gap - a.abs_gap);

  // Determine overall calibration quality from max gap
  let calibrationQuality;
  if (maxGap <= CALIBRATION_THRESHOLDS.EXCELLENT) {
    calibrationQuality = "excellent";
  } else if (maxGap <= CALIBRATION_THRESHOLDS.GOOD) {
    calibrationQuality = "good";
  } else if (maxGap <= CALIBRATION_THRESHOLDS.FAIR) {
    calibrationQuality = "fair";
  } else {
    calibrationQuality = "poor";
  }

  // Build recommendation
  const recommendation = buildCalibrationRecommendation(
    calibrationQuality,
    overconfidentBands,
    underconfidentBands,
    maxGap
  );

  return {
    overconfident_bands: overconfidentBands,
    underconfident_bands: underconfidentBands,
    max_gap: parseFloat(maxGap.toFixed(4)),
    calibration_quality: calibrationQuality,
    recommendation,
    sample_count: usable.reduce((s, r) => s + (r.samples || 0), 0),
  };
}

// ---------------------------------------------------------------------------
// generateCalibrationRecommendations
// ---------------------------------------------------------------------------
/**
 * Returns an array of human-readable calibration recommendation strings.
 *
 * @param {Object} calibrationAnalysis  Result from analyzeConfidenceCalibration()
 * @returns {string[]}  Array of recommendation strings
 */
export function generateCalibrationRecommendations(calibrationAnalysis) {
  const recommendations = [];

  if (!calibrationAnalysis || calibrationAnalysis.calibration_quality === undefined) {
    return ["No calibration analysis available — run analyzeConfidenceCalibration() first."];
  }

  const { overconfident_bands, underconfident_bands, calibration_quality, max_gap } =
    calibrationAnalysis;

  // Overall quality assessment
  switch (calibration_quality) {
    case "excellent":
      recommendations.push(
        "AI confidence calibration is excellent — no systematic over/under-confidence detected."
      );
      break;
    case "good":
      recommendations.push(
        "AI confidence calibration is good — minor adjustments may improve accuracy."
      );
      break;
    case "fair":
      recommendations.push(
        `AI confidence calibration is fair (max gap: ${(max_gap * 100).toFixed(1)}%) — review flagged bands below.`
      );
      break;
    case "poor":
      recommendations.push(
        `AI confidence calibration is poor (max gap: ${(max_gap * 100).toFixed(1)}%) — significant recalibration needed.`
      );
      break;
  }

  // Overconfident band recommendations
  for (const band of overconfident_bands.slice(0, 3)) {
    const strategyHint = getStrategyHint(band.confidence_band);
    recommendations.push(
      `Reduce confidence for ${band.agent_name} at band ${band.confidence_band} — ` +
      `AI predicts ${(band.expected_win_rate * 100).toFixed(0)}% win but actual is ` +
      `${(band.actual_win_rate * 100).toFixed(0)}% (gap: ${(band.calibration_gap * 100).toFixed(1)}%).` +
      (strategyHint ? ` ${strategyHint}` : "")
    );
  }

  // Underconfident band recommendations
  for (const band of underconfident_bands.slice(0, 3)) {
    recommendations.push(
      `Consider lowering confidence threshold for ${band.agent_name} at band ${band.confidence_band} — ` +
      `AI underestimates win rate: predicts ${(band.expected_win_rate * 100).toFixed(0)}% but actual is ` +
      `${(band.actual_win_rate * 100).toFixed(0)}% (gap: ${(Math.abs(band.calibration_gap) * 100).toFixed(1)}%).`
    );
  }

  // Calibration quality action items
  if (calibration_quality === "poor" || calibration_quality === "fair") {
    recommendations.push(
      "Action: Review AI prompt instructions for confidence scoring — consider adding explicit calibration examples."
    );
    recommendations.push(
      "Action: Increase replay sample count — need 20+ outcomes per confidence band for reliable calibration."
    );
  }

  if (recommendations.length === 1 && calibration_quality === "excellent") {
    recommendations.push("No action required — maintain current confidence scoring approach.");
  }

  return recommendations;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function buildCalibrationRecommendation(quality, overBands, underBands, maxGap) {
  const parts = [];

  if (quality === "excellent") {
    return "Confidence calibration is excellent. No systematic bias detected.";
  }

  parts.push(
    `Calibration quality: ${quality} (max gap: ${(maxGap * 100).toFixed(1)}%).`
  );

  if (overBands.length > 0) {
    parts.push(
      `${overBands.length} overconfident band(s): ` +
        overBands
          .slice(0, 3)
          .map(
            (b) =>
              `${b.confidence_band} [+${(b.calibration_gap * 100).toFixed(1)}%]`
          )
          .join(", ") +
        "."
    );
  }

  if (underBands.length > 0) {
    parts.push(
      `${underBands.length} underconfident band(s): ` +
        underBands
          .slice(0, 3)
          .map(
            (b) =>
              `${b.confidence_band} [${(b.calibration_gap * 100).toFixed(1)}%]`
          )
          .join(", ") +
        "."
    );
  }

  if (quality === "poor" || quality === "fair") {
    parts.push(
      "Consider revising AI confidence scoring prompts and building more replay data."
    );
  }

  return parts.join(" ");
}

function getStrategyHint(confidenceBand) {
  // confidence_band is typically a string like "0.60-0.65" or a strategy label
  if (!confidenceBand) return null;
  if (confidenceBand.toLowerCase().includes("trend")) {
    return "Trend-following signals often overestimate confidence in sideways markets.";
  }
  if (confidenceBand.toLowerCase().includes("iron_condor")) {
    return "Iron condor confidence may be high due to high theoretical probability, but market gaps can cause losses.";
  }
  return null;
}

function buildDefaultCalibrationResult() {
  return {
    overconfident_bands: [],
    underconfident_bands: [],
    max_gap: null,
    calibration_quality: "poor",
    recommendation:
      "No confidence_calibration data found. " +
      "The table needs to be populated from replay and signal review results. " +
      "Run the replay lab and performance tracker to generate calibration data.",
    sample_count: 0,
  };
}
