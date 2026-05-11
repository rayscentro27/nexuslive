// strategy_optimizer.js — Main optimizer coordinator
// RESEARCH ONLY — no live trading, no broker execution, no order placement

import "dotenv/config";
import { analyzeSlTpPlacement } from "./sl_tp_optimizer.js";
import { analyzeOptionsStructures } from "./options_structure_optimizer.js";
import { analyzeRiskThresholds, analyzeConfidenceThresholds } from "./threshold_optimizer.js";
import {
  analyzeConfidenceCalibration,
  generateCalibrationRecommendations,
} from "./confidence_optimizer.js";

// ---------------------------------------------------------------------------
// runFullOptimization
// ---------------------------------------------------------------------------
/**
 * Runs all sub-optimizers and produces a unified optimization report.
 *
 * @returns {Promise<Object>}
 *   {
 *     forex_optimizations,          // Array from analyzeSlTpPlacement()
 *     options_optimizations,        // Array from analyzeOptionsStructures()
 *     threshold_optimizations,      // { risk, confidence } from threshold analyzers
 *     confidence_optimizations,     // { calibration, recommendations }
 *     summary,                      // High-level text summary
 *     generated_at                  // ISO timestamp
 *   }
 */
export async function runFullOptimization() {
  console.log("[strategy_optimizer] Starting full optimization run...");
  const startTime = Date.now();

  const results = await Promise.allSettled([
    analyzeSlTpPlacement(),
    analyzeOptionsStructures(),
    analyzeRiskThresholds(),
    analyzeConfidenceThresholds(),
    analyzeConfidenceCalibration(),
  ]);

  const [
    forexResult,
    optionsResult,
    riskThresholdResult,
    confidenceThresholdResult,
    calibrationResult,
  ] = results;

  // Extract values, falling back to empty/default on error
  const forexOptimizations = extractResult(forexResult, [], "forexOptimizations");
  const optionsOptimizations = extractResult(optionsResult, [], "optionsOptimizations");
  const riskThresholds = extractResult(riskThresholdResult, null, "riskThresholds");
  const confidenceThresholds = extractResult(
    confidenceThresholdResult,
    null,
    "confidenceThresholds"
  );
  const calibrationAnalysis = extractResult(calibrationResult, null, "calibrationAnalysis");
  const calibrationRecommendations = calibrationAnalysis
    ? generateCalibrationRecommendations(calibrationAnalysis)
    : ["No calibration data available."];

  const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);

  // Build summary
  const summary = buildFullSummary(
    forexOptimizations,
    optionsOptimizations,
    riskThresholds,
    confidenceThresholds,
    calibrationAnalysis,
    elapsed
  );

  console.log(`[strategy_optimizer] Full optimization complete in ${elapsed}s.`);
  console.log("[strategy_optimizer]", summary);

  return {
    forex_optimizations: forexOptimizations,
    options_optimizations: optionsOptimizations,
    threshold_optimizations: {
      risk: riskThresholds,
      confidence: confidenceThresholds,
    },
    confidence_optimizations: {
      calibration: calibrationAnalysis,
      recommendations: calibrationRecommendations,
    },
    summary,
    generated_at: new Date().toISOString(),
  };
}

// ---------------------------------------------------------------------------
// runForexOptimization
// ---------------------------------------------------------------------------
/**
 * Runs only forex-focused optimizations: SL/TP placement + risk thresholds.
 *
 * @returns {Promise<Object>}
 *   {
 *     forex_optimizations, threshold_optimizations, summary, generated_at
 *   }
 */
export async function runForexOptimization() {
  console.log("[strategy_optimizer] Starting forex-only optimization run...");
  const startTime = Date.now();

  const results = await Promise.allSettled([
    analyzeSlTpPlacement(),
    analyzeRiskThresholds(),
    analyzeConfidenceThresholds(),
  ]);

  const [forexResult, riskResult, confidenceResult] = results;

  const forexOptimizations = extractResult(forexResult, [], "forexOptimizations");
  const riskThresholds = extractResult(riskResult, null, "riskThresholds");
  const confidenceThresholds = extractResult(confidenceResult, null, "confidenceThresholds");

  const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);

  const topForex = [...forexOptimizations]
    .sort((a, b) => b.improvement_score - a.improvement_score)
    .slice(0, 3);

  const summary =
    `Forex optimization complete in ${elapsed}s. ` +
    `Analyzed ${forexOptimizations.length} strategy(s). ` +
    `Top opportunity: ${topForex[0]?.strategy_id || "none"} ` +
    `(score: ${topForex[0]?.improvement_score ?? 0}).`;

  console.log(`[strategy_optimizer] ${summary}`);

  return {
    forex_optimizations: forexOptimizations,
    threshold_optimizations: {
      risk: riskThresholds,
      confidence: confidenceThresholds,
    },
    summary,
    generated_at: new Date().toISOString(),
  };
}

// ---------------------------------------------------------------------------
// runOptionsOptimization
// ---------------------------------------------------------------------------
/**
 * Runs only options-focused optimizations: structure analysis + confidence calibration.
 *
 * @returns {Promise<Object>}
 *   {
 *     options_optimizations, confidence_optimizations, summary, generated_at
 *   }
 */
export async function runOptionsOptimization() {
  console.log("[strategy_optimizer] Starting options-only optimization run...");
  const startTime = Date.now();

  const results = await Promise.allSettled([
    analyzeOptionsStructures(),
    analyzeConfidenceCalibration(),
  ]);

  const [optionsResult, calibrationResult] = results;

  const optionsOptimizations = extractResult(optionsResult, [], "optionsOptimizations");
  const calibrationAnalysis = extractResult(calibrationResult, null, "calibrationAnalysis");
  const calibrationRecommendations = calibrationAnalysis
    ? generateCalibrationRecommendations(calibrationAnalysis)
    : ["No calibration data available."];

  const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);

  const topOptions = [...optionsOptimizations]
    .sort((a, b) => b.improvement_score - a.improvement_score)
    .slice(0, 3);

  const summary =
    `Options optimization complete in ${elapsed}s. ` +
    `Generated ${optionsOptimizations.length} suggestion(s). ` +
    `Top opportunity: ${topOptions[0]?.strategy_type || "none"} ` +
    `(score: ${topOptions[0]?.improvement_score ?? 0}). ` +
    `Calibration: ${calibrationAnalysis?.calibration_quality || "unknown"}.`;

  console.log(`[strategy_optimizer] ${summary}`);

  return {
    options_optimizations: optionsOptimizations,
    confidence_optimizations: {
      calibration: calibrationAnalysis,
      recommendations: calibrationRecommendations,
    },
    summary,
    generated_at: new Date().toISOString(),
  };
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function extractResult(settledResult, fallback, label) {
  if (settledResult.status === "fulfilled") {
    return settledResult.value;
  }
  console.error(
    `[strategy_optimizer] ${label} failed: ${settledResult.reason?.message || settledResult.reason}`
  );
  return fallback;
}

function buildFullSummary(
  forexOpts,
  optionsOpts,
  riskThresholds,
  confidenceThresholds,
  calibration,
  elapsed
) {
  const topForex = [...(forexOpts || [])]
    .sort((a, b) => b.improvement_score - a.improvement_score)
    .slice(0, 1)[0];

  const topOptions = [...(optionsOpts || [])]
    .sort((a, b) => b.improvement_score - a.improvement_score)
    .slice(0, 1)[0];

  const parts = [`Full optimization complete in ${elapsed}s.`];

  if (forexOpts?.length) {
    parts.push(
      `Forex: ${forexOpts.length} strategy(s) analyzed. ` +
        `Top: ${topForex?.strategy_id || "n/a"} (score: ${topForex?.improvement_score ?? 0}).`
    );
  } else {
    parts.push("Forex: No data available.");
  }

  if (optionsOpts?.length) {
    parts.push(
      `Options: ${optionsOpts.length} suggestion(s). ` +
        `Top: ${topOptions?.strategy_type || "n/a"} (score: ${topOptions?.improvement_score ?? 0}).`
    );
  } else {
    parts.push("Options: No data available.");
  }

  if (riskThresholds) {
    const riskChanged =
      riskThresholds.suggested_approval_threshold !==
      riskThresholds.current_approval_threshold;
    parts.push(
      `Risk thresholds: approval ${riskThresholds.current_approval_threshold} → ${riskThresholds.suggested_approval_threshold}` +
        (riskChanged ? " [CHANGE SUGGESTED]" : " [no change]") +
        "."
    );
  }

  if (calibration) {
    parts.push(`Confidence calibration: ${calibration.calibration_quality}.`);
  }

  parts.push("ALL SUGGESTIONS REQUIRE HUMAN REVIEW — no changes applied automatically.");

  return parts.join(" ");
}
