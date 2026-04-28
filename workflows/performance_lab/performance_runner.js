import "dotenv/config";
import { generateAllScorecards } from "./scorecard_generator.js";
import { rankForexStrategies, rankOptionsStrategies } from "./ranking_engine.js";
import { ingestOutcomeFile } from "./outcome_ingest.js";
import { computeAnalystMetrics } from "./analyst_metrics.js";
import { computeRiskMetrics } from "./risk_metrics.js";
import {
  sendPerformanceSummary,
  sendSystemAlert,
} from "./telegram_performance_alert.js";

// ── SAFETY GUARD ─────────────────────────────────────────────────────────────
// This system is RESEARCH ONLY. It reads from Supabase and computes metrics.
// It does NOT place trades, connect to brokers, or execute orders.
// ─────────────────────────────────────────────────────────────────────────────
console.log("[runner] Nexus Performance Lab — RESEARCH ONLY MODE");

function parseArgs(argv) {
  const args = argv.slice(2);
  const mode = args[0];
  const extra = args[1] ?? null;
  return { mode, extra };
}

async function runScorecards() {
  console.log("\n[runner] Mode: GENERATE ALL AGENT SCORECARDS");
  console.log("[runner] ─────────────────────────────────────");

  try {
    const result = await generateAllScorecards();
    console.log(`[runner] Scorecard generation complete: ${JSON.stringify(result)}`);

    // Fetch fresh metrics for Telegram summary
    const [analystMetrics, riskMetrics] = await Promise.all([
      computeAnalystMetrics(),
      computeRiskMetrics(),
    ]);

    await sendSystemAlert(
      `Scorecard generation complete.\nAnalyst reviewed: ${analystMetrics.total_reviewed}\nRisk decisions: ${riskMetrics.total_decisions}`
    );
  } catch (err) {
    console.error("[runner] Scorecard generation failed:", err.message);
    await sendSystemAlert(`Scorecard generation FAILED: ${err.message}`).catch(() => {});
    process.exit(1);
  }
}

async function runRank() {
  console.log("\n[runner] Mode: RANK ALL STRATEGIES + SEND TELEGRAM SUMMARY");
  console.log("[runner] ────────────────────────────────────────────────────");

  try {
    // Run forex and options ranking in parallel
    const [forexRankings, optionsRankings] = await Promise.all([
      rankForexStrategies(),
      rankOptionsStrategies(),
    ]);

    // Fetch agent metrics for Telegram summary
    const [analystMetrics, riskMetrics] = await Promise.all([
      computeAnalystMetrics(),
      computeRiskMetrics(),
    ]);

    console.log(
      `[runner] Rankings complete: forex=${forexRankings.length}, options=${optionsRankings.length}`
    );

    await sendPerformanceSummary(forexRankings, optionsRankings, {
      analystMetrics,
      riskMetrics,
    });

    console.log("[runner] Rank run complete.");
  } catch (err) {
    console.error("[runner] Rank run failed:", err.message);
    await sendSystemAlert(`Ranking run FAILED: ${err.message}`).catch(() => {});
    process.exit(1);
  }
}

async function runIngest(filePath) {
  if (!filePath) {
    console.error(
      "[runner] ERROR: --ingest requires a file path.\n  Usage: node performance_runner.js --ingest outcome.json"
    );
    process.exit(1);
  }

  console.log(`\n[runner] Mode: INGEST OUTCOMES from ${filePath}`);
  console.log("[runner] ────────────────────────────────────────────");

  try {
    const result = await ingestOutcomeFile(filePath);
    console.log(`[runner] Ingest complete: ${JSON.stringify(result)}`);

    const summary = [
      `Outcome ingest complete.`,
      `File: ${filePath}`,
      `Inserted: ${result.inserted}`,
      `Skipped: ${result.skipped}`,
      `Errors: ${result.errors.length}`,
    ];

    if (result.errors.length) {
      summary.push(`\nErrors:\n${result.errors.map((e) => `  - ${e}`).join("\n")}`);
    }

    await sendSystemAlert(summary.join("\n"));
  } catch (err) {
    console.error("[runner] Ingest failed:", err.message);
    await sendSystemAlert(`Outcome ingest FAILED: ${err.message}`).catch(() => {});
    process.exit(1);
  }
}

function printHelp() {
  console.log(`
Nexus Performance Lab — Runner

Usage:
  node performance_runner.js --scorecards
      Generate all agent scorecards and save to Supabase agent_scorecards table.

  node performance_runner.js --rank
      Rank all forex and options strategies. Write to strategy_performance and
      options_strategy_performance. Send Telegram summary.

  node performance_runner.js --ingest <file.json>
      Ingest an outcome JSON file into proposal_outcomes table.

  node performance_runner.js --help
      Show this help message.

SAFETY: This system is RESEARCH ONLY. No live trading. No broker connections.
`);
}

// ── MAIN ─────────────────────────────────────────────────────────────────────
const { mode, extra } = parseArgs(process.argv);

switch (mode) {
  case "--scorecards":
    await runScorecards();
    break;
  case "--rank":
    await runRank();
    break;
  case "--ingest":
    await runIngest(extra);
    break;
  case "--help":
  case "-h":
    printHelp();
    break;
  default:
    console.error(
      `[runner] Unknown mode: "${mode ?? "(none)"}". Run with --help for usage.`
    );
    printHelp();
    process.exit(1);
}
