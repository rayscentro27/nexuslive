/**
 * risk_runner.js
 * Risk Office orchestrator — reads AI proposals and makes risk decisions.
 *
 * Modes:
 *   node risk_runner.js --once    Process pending proposals then exit.
 *   node risk_runner.js --poll    Run continuously on POLL_INTERVAL_SECONDS.
 *   node risk_runner.js --status  Print current risk state and exit.
 *
 * Pipeline per proposal:
 *   1. Poll reviewed_signal_proposals where status = 'proposed'
 *   2. Apply risk rules (R:R, daily loss, positions, duplicates)
 *   3. Write decision to risk_decisions table
 *   4. Update proposal status (approved / blocked / needs_review)
 *   5. Send combined Telegram alert (AI proposal + risk decision)
 *
 * NO LIVE TRADING. NO BROKER EXECUTION. ANALYSIS ONLY.
 */

import "dotenv/config";
import { pollPendingProposals }             from "./risk_poll.js";
import { evaluateProposal, getRiskState, LIMITS } from "./risk_rules.js";
import { writeRiskDecision }               from "./risk_writer.js";
import { sendRiskAlert, sendRiskSystemAlert } from "./risk_alert.js";

const POLL_INTERVAL_MS = Number(process.env.POLL_INTERVAL_SECONDS ?? 60) * 1000;

// ── Single Proposal Runner ────────────────────────────────────────────────────

async function processProposal(proposal) {
  const label = `${(proposal.symbol ?? "").replace("_", "")} ${(proposal.side ?? "").toUpperCase()} [${proposal.id.slice(0, 8)}]`;
  console.log(`\n[risk] Evaluating: ${label}`);

  // 1. Apply risk rules
  const decision = evaluateProposal(proposal);
  console.log(`[risk] Decision: ${decision.status} | R:R: ${decision.rr_ratio.toFixed(2)} | Score: ${decision.risk_score}/100`);
  if (decision.rejection_reason) {
    console.log(`[risk] Reason: ${decision.rejection_reason}`);
  }

  // 2. Write to Supabase
  await writeRiskDecision(proposal.id, proposal, decision);

  // 3. Send Telegram alert
  await sendRiskAlert(proposal, decision);

  console.log(`[risk] ✅ Done: ${label} → ${decision.status.toUpperCase()}`);
  return decision;
}

// ── Batch Runner ──────────────────────────────────────────────────────────────

async function runOnce() {
  console.log(`[risk] Starting — mode: once`);
  const proposals = await pollPendingProposals();

  if (!proposals.length) {
    console.log("[risk] No pending proposals.");
    return;
  }

  let approved = 0, rejected = 0, held = 0, failed = 0;

  for (const proposal of proposals) {
    try {
      const decision = await processProposal(proposal);
      if (decision.status === "approved") approved++;
      else if (decision.status === "held")     held++;
      else                                     rejected++;
    } catch (err) {
      console.error(`[risk] ❌ Failed ${proposal.id}: ${err.message}`);
      failed++;
    }
  }

  console.log(`\n[risk] Batch complete — approved: ${approved}, rejected: ${rejected}, held: ${held}, failed: ${failed}`);
}

async function runPoll() {
  console.log(`[risk] Starting — mode: poll (every ${POLL_INTERVAL_MS / 1000}s)`);
  await sendRiskSystemAlert("Risk Office started — polling for proposals.");

  while (true) {
    try {
      await runOnce();
    } catch (err) {
      console.error(`[risk] Poll cycle error: ${err.message}`);
    }
    await new Promise((r) => setTimeout(r, POLL_INTERVAL_MS));
  }
}

function printStatus() {
  const state = getRiskState();
  console.log("\n╔══════════════════════════════════════╗");
  console.log("║      NEXUS RISK OFFICE — STATUS      ║");
  console.log("╠══════════════════════════════════════╣");
  console.log(`║ Date:           ${state.date.padEnd(20)}║`);
  console.log(`║ Daily P&L:      $${String(state.daily_pnl.toFixed(2)).padEnd(19)}║`);
  console.log(`║ Loss Limit:     -$${String(LIMITS.MAX_DAILY_LOSS_USD.toFixed(2)).padEnd(18)}║`);
  console.log(`║ Open Positions: ${String(state.open_positions.length).padEnd(20)}║`);
  console.log(`║ Max Positions:  ${String(LIMITS.MAX_OPEN_POSITIONS).padEnd(20)}║`);
  console.log(`║ Reviewed today: ${String(state.total_reviewed).padEnd(20)}║`);
  console.log(`║ Approved:       ${String(state.total_approved).padEnd(20)}║`);
  console.log(`║ Rejected:       ${String(state.total_rejected).padEnd(20)}║`);
  console.log("╠══════════════════════════════════════╣");
  if (state.open_positions.length) {
    console.log("║ Open Positions:                      ║");
    for (const p of state.open_positions) {
      const line = `  ${p.symbol} ${p.side} @ ${p.entry_price}`;
      console.log(`║ ${line.padEnd(37)}║`);
    }
  } else {
    console.log("║ No open positions.                   ║");
  }
  console.log("╚══════════════════════════════════════╝\n");
}

// ── Main ──────────────────────────────────────────────────────────────────────

const args = process.argv.slice(2);

if (args.includes("--status")) {
  printStatus();
  process.exit(0);
} else if (args.includes("--poll")) {
  runPoll().catch((err) => {
    console.error("[risk] Fatal:", err);
    process.exit(1);
  });
} else {
  runOnce()
    .then(() => process.exit(0))
    .catch((err) => {
      console.error("[risk] Fatal:", err);
      process.exit(1);
    });
}
