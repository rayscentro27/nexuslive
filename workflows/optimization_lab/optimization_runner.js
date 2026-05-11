// optimization_runner.js — Main orchestrator for the Nexus Optimization Lab
// RESEARCH ONLY — no live trading, no broker execution, no order placement
//
// Usage:
//   node optimization_runner.js --analyze     Full analysis, all types, write + Telegram
//   node optimization_runner.js --forex       Forex optimizations only
//   node optimization_runner.js --options     Options optimizations only
//   node optimization_runner.js --thresholds  Threshold + confidence analysis only

import "dotenv/config";
import {
  runFullOptimization,
  runForexOptimization,
  runOptionsOptimization,
} from "./strategy_optimizer.js";
import {
  writeOptimizationBatch,
  getRecentOptimizations,
} from "./optimizer_writer.js";
import { analyzeRiskThresholds, analyzeConfidenceThresholds } from "./threshold_optimizer.js";
import {
  analyzeConfidenceCalibration,
  generateCalibrationRecommendations,
} from "./confidence_optimizer.js";
import {
  sendOptimizationReport,
  sendSystemAlert,
} from "./telegram_optimizer_alert.js";

// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------
const WRITE_TO_SUPABASE =
  process.env.WRITE_TO_SUPABASE !== "false"; // default true
const SEND_TELEGRAM =
  process.env.SEND_TELEGRAM !== "false"; // default true

// ---------------------------------------------------------------------------
// Argument parsing
// ---------------------------------------------------------------------------
const args = process.argv.slice(2);
const MODE = args.find((a) =>
  ["--analyze", "--forex", "--options", "--thresholds"].includes(a)
);

if (!MODE) {
  console.error(
    "Usage: node optimization_runner.js [--analyze|--forex|--options|--thresholds]"
  );
  process.exit(1);
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------
async function main() {
  console.log("=".repeat(60));
  console.log(`NEXUS OPTIMIZATION LAB — Mode: ${MODE}`);
  console.log(`Write to Supabase: ${WRITE_TO_SUPABASE}`);
  console.log(`Send Telegram: ${SEND_TELEGRAM}`);
  console.log("RESEARCH ONLY — no live trading, no order placement");
  console.log("=".repeat(60));

  let report = null;
  let optimizationsToWrite = [];

  try {
    switch (MODE) {
      // -----------------------------------------------------------------------
      case "--analyze": {
        console.log("\n[runner] Running FULL optimization analysis...\n");
        report = await runFullOptimization();

        // Collect all optimization suggestions
        if (report.forex_optimizations?.length) {
          for (const opt of report.forex_optimizations) {
            if (opt.improvement_score > 0) {
              optimizationsToWrite.push({
                strategy_id: opt.strategy_id,
                asset_type: "forex",
                optimization_type: "sl_tp",
                parameter_name: "rr_ratio",
                original_value: opt.avg_rr,
                suggested_value: opt.optimal_rr ?? opt.avg_rr,
                improvement_score: opt.improvement_score,
                notes: opt.notes,
              });
            }
          }
        }

        if (report.options_optimizations?.length) {
          for (const opt of report.options_optimizations) {
            if (opt.improvement_score > 0) {
              optimizationsToWrite.push({
                strategy_id: opt.strategy_type,
                asset_type: "options",
                optimization_type: "options_structure",
                parameter_name: opt.parameter_name,
                original_value: opt.original_value,
                suggested_value: opt.suggested_value,
                improvement_score: opt.improvement_score,
                notes: opt.notes,
              });
            }
          }
        }

        if (report.threshold_optimizations?.risk) {
          const risk = report.threshold_optimizations.risk;
          if (risk.suggested_approval_threshold !== risk.current_approval_threshold) {
            optimizationsToWrite.push({
              strategy_id: "system",
              asset_type: "forex",
              optimization_type: "threshold",
              parameter_name: "approval_threshold",
              original_value: risk.current_approval_threshold,
              suggested_value: risk.suggested_approval_threshold,
              improvement_score: 75,
              notes: risk.improvement_note,
            });
          }
        }

        break;
      }

      // -----------------------------------------------------------------------
      case "--forex": {
        console.log("\n[runner] Running FOREX optimization...\n");
        report = await runForexOptimization();

        if (report.forex_optimizations?.length) {
          for (const opt of report.forex_optimizations) {
            if (opt.improvement_score > 0) {
              optimizationsToWrite.push({
                strategy_id: opt.strategy_id,
                asset_type: "forex",
                optimization_type: "sl_tp",
                parameter_name: "rr_ratio",
                original_value: opt.avg_rr,
                suggested_value: opt.optimal_rr ?? opt.avg_rr,
                improvement_score: opt.improvement_score,
                notes: opt.notes,
              });
            }
          }
        }

        break;
      }

      // -----------------------------------------------------------------------
      case "--options": {
        console.log("\n[runner] Running OPTIONS optimization...\n");
        report = await runOptionsOptimization();

        if (report.options_optimizations?.length) {
          for (const opt of report.options_optimizations) {
            if (opt.improvement_score > 0) {
              optimizationsToWrite.push({
                strategy_id: opt.strategy_type,
                asset_type: "options",
                optimization_type: "options_structure",
                parameter_name: opt.parameter_name,
                original_value: opt.original_value,
                suggested_value: opt.suggested_value,
                improvement_score: opt.improvement_score,
                notes: opt.notes,
              });
            }
          }
        }

        break;
      }

      // -----------------------------------------------------------------------
      case "--thresholds": {
        console.log("\n[runner] Running THRESHOLD + CONFIDENCE analysis...\n");

        const [riskResult, confThreshResult, calibrationResult] = await Promise.allSettled([
          analyzeRiskThresholds(),
          analyzeConfidenceThresholds(),
          analyzeConfidenceCalibration(),
        ]);

        const riskThresholds =
          riskResult.status === "fulfilled" ? riskResult.value : null;
        const confThresholds =
          confThreshResult.status === "fulfilled" ? confThreshResult.value : null;
        const calibration =
          calibrationResult.status === "fulfilled" ? calibrationResult.value : null;
        const calibRecs = calibration
          ? generateCalibrationRecommendations(calibration)
          : [];

        report = {
          forex_optimizations: [],
          options_optimizations: [],
          threshold_optimizations: {
            risk: riskThresholds,
            confidence: confThresholds,
          },
          confidence_optimizations: {
            calibration,
            recommendations: calibRecs,
          },
          summary:
            `Threshold analysis complete. ` +
            `Risk approval: ${riskThresholds?.current_approval_threshold} → ` +
            `${riskThresholds?.suggested_approval_threshold}. ` +
            `Min confidence: ${confThresholds?.current_min_confidence?.toFixed(2)} → ` +
            `${confThresholds?.suggested_min_confidence?.toFixed(2)}. ` +
            `Calibration: ${calibration?.calibration_quality || "unknown"}.`,
          generated_at: new Date().toISOString(),
        };

        // Write threshold suggestions if they changed
        if (
          riskThresholds &&
          riskThresholds.suggested_approval_threshold !==
            riskThresholds.current_approval_threshold
        ) {
          optimizationsToWrite.push({
            strategy_id: "system",
            asset_type: "forex",
            optimization_type: "threshold",
            parameter_name: "approval_threshold",
            original_value: riskThresholds.current_approval_threshold,
            suggested_value: riskThresholds.suggested_approval_threshold,
            improvement_score: 70,
            notes: riskThresholds.improvement_note,
          });
        }

        if (
          confThresholds &&
          Math.abs(
            confThresholds.suggested_min_confidence -
              confThresholds.current_min_confidence
          ) > 0.02
        ) {
          optimizationsToWrite.push({
            strategy_id: "system",
            asset_type: "forex",
            optimization_type: "confidence",
            parameter_name: "min_confidence",
            original_value: confThresholds.current_min_confidence,
            suggested_value: confThresholds.suggested_min_confidence,
            improvement_score: 60,
            notes: confThresholds.improvement_note,
          });
        }

        break;
      }
    }

    // -----------------------------------------------------------------------
    // Write results to Supabase
    // -----------------------------------------------------------------------
    if (WRITE_TO_SUPABASE && optimizationsToWrite.length > 0) {
      console.log(
        `\n[runner] Writing ${optimizationsToWrite.length} optimization(s) to Supabase...`
      );
      try {
        await writeOptimizationBatch(optimizationsToWrite);
        console.log("[runner] Write complete.");
      } catch (err) {
        console.error("[runner] Failed to write to Supabase:", err.message);
      }
    } else if (WRITE_TO_SUPABASE) {
      console.log("\n[runner] No optimization suggestions to write.");
    }

    // -----------------------------------------------------------------------
    // Send Telegram report
    // -----------------------------------------------------------------------
    if (SEND_TELEGRAM && report) {
      console.log("\n[runner] Sending Telegram report...");
      try {
        await sendOptimizationReport(report);
      } catch (err) {
        console.error("[runner] Failed to send Telegram report:", err.message);
      }
    }

    // -----------------------------------------------------------------------
    // Console summary
    // -----------------------------------------------------------------------
    console.log("\n" + "=".repeat(60));
    console.log("OPTIMIZATION COMPLETE");
    console.log("=".repeat(60));
    if (report?.summary) {
      console.log("\nSummary:", report.summary);
    }

    if (WRITE_TO_SUPABASE && optimizationsToWrite.length > 0) {
      console.log("\nRecent top optimizations:");
      try {
        const recent = await getRecentOptimizations(5);
        for (const r of recent) {
          console.log(
            `  ${r.strategy_id || "system"} / ${r.parameter_name}: ` +
              `${r.original_value ?? "n/a"} → ${r.suggested_value ?? "n/a"} ` +
              `(score: ${r.improvement_score})`
          );
        }
      } catch (err) {
        console.warn("[runner] Could not fetch recent optimizations:", err.message);
      }
    }

    console.log(
      "\nNOTE: All suggestions are research-only. No changes applied automatically."
    );
    console.log("=".repeat(60));
  } catch (err) {
    console.error("\n[runner] Fatal error:", err.message);
    if (SEND_TELEGRAM) {
      try {
        await sendSystemAlert(`Optimization Lab error (${MODE}): ${err.message}`);
      } catch (_) {
        // ignore Telegram errors during error handling
      }
    }
    process.exit(1);
  }
}

main();
