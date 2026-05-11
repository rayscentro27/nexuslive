/**
 * replay_runner.js — Nexus Replay Lab Orchestrator
 *
 * RESEARCH ONLY. No live trading. No broker execution. No order placement.
 *
 * Run modes:
 *   node replay_runner.js --once             Replay all pending proposals
 *   node replay_runner.js --limit 5          Replay up to 5 proposals
 *   node replay_runner.js --symbol EURUSD    Only proposals for that symbol
 *   node replay_runner.js --strategy trend_follow  Only that strategy
 *   node replay_runner.js --calibrate        Run calibration only, no new replays
 */

import "dotenv/config";
import { pollProposalsForReplay, pollOptionsProposalsForReplay } from "./replay_poll.js";
import { buildReplayContext } from "./replay_context.js";
import { simulateForexTrade } from "./forex_replay_engine.js";
import { simulateOptionsStrategy } from "./options_replay_engine.js";
import { writePaperTradeRun, writeReplayResult, getReplayStats } from "./paper_result_writer.js";
import { computeCalibration, interpretCalibration } from "./calibration_engine.js";
import { generateReplayScorecards } from "./replay_scorecards.js";
import { sendReplaySummary, sendSystemAlert } from "./telegram_replay_alert.js";

// ---------------------------------------------------------------------------
// CLI argument parsing
// ---------------------------------------------------------------------------

function parseArgs(argv) {
  const args = {
    once: false,
    calibrate: false,
    limit: 50,
    symbol: null,
    strategy: null,
  };

  for (let i = 2; i < argv.length; i++) {
    const flag = argv[i];
    if (flag === "--once") args.once = true;
    else if (flag === "--calibrate") args.calibrate = true;
    else if (flag === "--limit") args.limit = parseInt(argv[++i], 10) || 50;
    else if (flag === "--symbol") args.symbol = argv[++i] ?? null;
    else if (flag === "--strategy") args.strategy = argv[++i] ?? null;
  }

  // --once sets a very high limit (effectively "all pending")
  if (args.once) args.limit = 1000;

  return args;
}

// ---------------------------------------------------------------------------
// Filter helpers
// ---------------------------------------------------------------------------

function applyFilters(proposals, args) {
  let filtered = proposals;
  if (args.symbol) {
    const sym = args.symbol.toUpperCase();
    filtered = filtered.filter(
      (p) => (p.symbol ?? "").toUpperCase() === sym
    );
  }
  if (args.strategy) {
    filtered = filtered.filter((p) => p.strategy_id === args.strategy);
  }
  return filtered.slice(0, args.limit);
}

// ---------------------------------------------------------------------------
// Replay a single forex proposal
// ---------------------------------------------------------------------------

async function replayForexProposal(proposal) {
  const context = await buildReplayContext(proposal);
  console.log(
    `  [forex] Replaying proposal ${proposal.id} | ${proposal.symbol} | strategy=${proposal.strategy_id}`
  );

  const run = await writePaperTradeRun(proposal, "forex_static_rr");
  const replayOutcome = simulateForexTrade(context.proposal);

  console.log(
    `    outcome=${replayOutcome.replay_outcome} rr=${replayOutcome.rr_ratio} pnl_r=${replayOutcome.pnl_r}`
  );

  await writeReplayResult(run.id, proposal, replayOutcome);
}

// ---------------------------------------------------------------------------
// Replay a single options proposal
// ---------------------------------------------------------------------------

async function replayOptionsProposal(proposal) {
  const context = await buildReplayContext(proposal);
  console.log(
    `  [options] Replaying proposal ${proposal.id} | ${proposal.symbol} | strategy=${proposal.strategy_id}`
  );

  const run = await writePaperTradeRun(proposal, "options_historical_profile");
  const replayOutcome = simulateOptionsStrategy(context.proposal);

  console.log(
    `    outcome=${replayOutcome.replay_outcome} pnl_pct=${replayOutcome.pnl_pct}`
  );

  await writeReplayResult(run.id, proposal, replayOutcome);
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main() {
  const args = parseArgs(process.argv);

  console.log("\n========================================");
  console.log("  NEXUS REPLAY LAB — RESEARCH ONLY");
  console.log("  No live trading. No broker execution.");
  console.log("========================================\n");

  // --calibrate: calibration only, no new replays
  if (args.calibrate) {
    console.log("[runner] Running calibration analysis...");
    try {
      const calibration = await computeCalibration();
      const summary = interpretCalibration(calibration);
      console.log("\n" + summary);
      await sendSystemAlert("Calibration run complete:\n\n" + summary);
    } catch (err) {
      console.error("[runner] Calibration error:", err.message);
      await sendSystemAlert(`Calibration error: ${err.message}`).catch(() => {});
      process.exit(1);
    }
    return;
  }

  // --once / --limit / --symbol / --strategy: replay proposals
  let forexProposals = [];
  let optionsProposals = [];

  try {
    const rawForex = await pollProposalsForReplay(args.limit);
    const rawOptions = await pollOptionsProposalsForReplay(args.limit);
    forexProposals = applyFilters(rawForex, args);
    optionsProposals = applyFilters(rawOptions, args);
  } catch (err) {
    console.error("[runner] Poll error:", err.message);
    await sendSystemAlert(`Replay poll error: ${err.message}`).catch(() => {});
    process.exit(1);
  }

  const totalPending = forexProposals.length + optionsProposals.length;
  console.log(
    `[runner] Pending proposals: ${forexProposals.length} forex, ${optionsProposals.length} options`
  );

  if (totalPending === 0) {
    console.log("[runner] No pending proposals — nothing to replay.");
    return;
  }

  // Replay forex proposals
  if (forexProposals.length > 0) {
    console.log(`\n[runner] --- Forex Replay (${forexProposals.length} proposals) ---`);
    for (const proposal of forexProposals) {
      try {
        await replayForexProposal(proposal);
      } catch (err) {
        console.error(`  [forex] Error on proposal ${proposal.id}:`, err.message);
      }
    }
  }

  // Replay options proposals
  if (optionsProposals.length > 0) {
    console.log(`\n[runner] --- Options Replay (${optionsProposals.length} proposals) ---`);
    for (const proposal of optionsProposals) {
      try {
        await replayOptionsProposal(proposal);
      } catch (err) {
        console.error(`  [options] Error on proposal ${proposal.id}:`, err.message);
      }
    }
  }

  // Compute stats, scorecards, calibration, send Telegram summary
  console.log("\n[runner] Computing stats and scorecards...");
  try {
    const [stats, scorecards, calibration] = await Promise.all([
      getReplayStats(),
      generateReplayScorecards(),
      computeCalibration(),
    ]);

    console.log(
      `[runner] Stats: total=${stats.total_runs} wins=${stats.wins} losses=${stats.losses} avg_pnl_r=${stats.avg_pnl_r}`
    );

    const calibSummary = interpretCalibration(calibration);
    console.log("\n" + calibSummary);

    await sendReplaySummary(stats, scorecards, calibration);
    console.log("[runner] Telegram summary sent.");
  } catch (err) {
    console.error("[runner] Post-replay reporting error:", err.message);
    await sendSystemAlert(`Replay reporting error: ${err.message}`).catch(() => {});
  }

  console.log("\n[runner] Done.\n");
}

main().catch(async (err) => {
  console.error("[runner] Fatal error:", err);
  await sendSystemAlert(`Replay Lab fatal error: ${err.message}`).catch(() => {});
  process.exit(1);
});
