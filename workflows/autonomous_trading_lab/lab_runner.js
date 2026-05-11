/**
 * lab_runner.js
 * Autonomous Trading Lab — main orchestrator.
 *
 * Wires together:
 *   lab_poll        → Supabase enriched signals
 *   lab_context     → market snapshot + research context
 *   analyst_runner  → OpenAI-compatible AI analyst
 *   risk_engine     → 100-penalty risk scoring
 *   proposal_writer → reviewed_signal_proposals table
 *   risk_writer     → risk_decisions table
 *   approval_queue  → approval_queue table (approved signals only)
 *   Telegram alerts → proposal + risk + approval alerts
 *
 * Run modes:
 *   node lab_runner.js --once         Process one batch then exit.
 *   node lab_runner.js --limit 3      Process up to 3 signals then exit.
 *   node lab_runner.js --poll         Run continuously on POLL_INTERVAL_SECONDS.
 *   node lab_runner.js --status       Print lab state and exit.
 *
 * NO LIVE TRADING. NO AUTO EXECUTION. NO BROKER ORDERS. ANALYSIS ONLY.
 */

import "dotenv/config";
import { pollEnrichedSignals }          from "./lab_poll.js";
import { buildContextPack }             from "./lab_context.js";
import { runAnalyst }                   from "./analyst_runner.js";
import { scoreProposal }                from "./risk_engine.js";
import { writeProposal, markSignalReviewed } from "./proposal_writer.js";
import { writeRiskDecision }            from "./risk_writer.js";
import { enqueueApproval }             from "./approval_queue.js";
import { sendProposalAlert }            from "./telegram_proposal_alert.js";
import { sendRiskAlert }                from "./telegram_risk_alert.js";
import { sendApprovalAlert, sendSystemAlert } from "./telegram_approval_alert.js";

const POLL_MS = Number(process.env.POLL_INTERVAL_SECONDS ?? 60) * 1000;

// ── Lab State ─────────────────────────────────────────────────────────────────

const state = {
  processed:   0,
  approved:    0,
  manual:      0,
  blocked:     0,
  errors:      0,
  started_at:  new Date().toISOString(),
};

// ── Process One Signal ────────────────────────────────────────────────────────

async function processSignal(signal) {
  const label = `${(signal.symbol ?? "").replace("_", "")} ${(signal.side ?? "").toUpperCase()} [${signal.id.slice(0, 8)}] (${signal.asset_type ?? "forex"})`;
  console.log(`\n[lab] ── Signal: ${label}`);

  // 1. Build context pack (market snapshot + research + options Greeks)
  const ctx = await buildContextPack(signal);

  // 2. AI Analyst via the configured LLM gateway
  const proposal = await runAnalyst(ctx);
  proposal.trace_id  = proposal.trace_id  || signal.trace_id;
  proposal.asset_type = signal.asset_type ?? "forex";

  console.log(`[lab] AI → status: ${proposal.status} | confidence: ${proposal.ai_confidence}`);

  // 3. Write proposal to Supabase
  const savedProposal = await writeProposal(signal.id, proposal);
  await markSignalReviewed(signal.id);

  // 4. Send proposal Telegram alert (all statuses)
  await sendProposalAlert(proposal);

  // 5. If AI blocked it, stop here
  if (proposal.status === "blocked") {
    console.log(`[lab] ⛔ AI blocked — skipping risk engine.`);
    state.blocked++;
    state.processed++;
    return;
  }

  // 6. Risk scoring (100-penalty system)
  const snapshot  = ctx.snapshot ?? null;
  const riskResult = scoreProposal(proposal, snapshot);
  const activeFlags = Object.entries(riskResult.flags).filter(([,v])=>v).map(([k])=>k);
  console.log(`[lab] Risk → decision: ${riskResult.decision} | score: ${riskResult.score}/100 | flags: ${activeFlags.join(", ") || "none"}`);

  // 7. Write risk decision
  const proposalId = savedProposal?.id ?? signal.id;
  await writeRiskDecision(proposalId, { ...proposal, signal_id: signal.id }, riskResult);

  // 8. Send risk Telegram alert
  await sendRiskAlert(proposal, riskResult);

  // 9. If approved or manual_review → enqueue for human approval
  if (riskResult.decision === "approved" || riskResult.decision === "manual_review") {
    const queueItem = await enqueueApproval({
      proposal_id:  proposalId,
      signal_id:    signal.id,
      symbol:       proposal.symbol ?? signal.symbol,
      side:         proposal.side   ?? signal.side,
      asset_type:   signal.asset_type ?? "forex",
      strategy_id:  proposal.strategy_id ?? signal.strategy_id,
      risk_score:   riskResult.score,
      decision:     riskResult.decision,
      trace_id:     signal.trace_id,
    });

    await sendApprovalAlert(queueItem ?? {
      symbol:      proposal.symbol ?? signal.symbol,
      asset_type:  signal.asset_type ?? "forex",
      strategy_id: proposal.strategy_id ?? signal.strategy_id,
      risk_score:  riskResult.score,
      decision:    riskResult.decision,
      trace_id:    signal.trace_id,
      id:          proposalId,
    });

    if (riskResult.decision === "approved") state.approved++;
    else                                    state.manual++;
  } else {
    state.blocked++;
  }

  state.processed++;
  console.log(`[lab] ✅ Done: ${label} → AI:${proposal.status} → Risk:${riskResult.decision}`);
}

// ── Batch Runner ──────────────────────────────────────────────────────────────

async function runBatch(limit = Infinity) {
  console.log("\n[lab] ════════════════════════════════════════");
  console.log("[lab] Nexus Autonomous Trading Lab — batch");
  console.log("[lab] ════════════════════════════════════════");

  const signals = await pollEnrichedSignals();

  if (!signals.length) {
    console.log("[lab] No enriched signals to process.");
    return 0;
  }

  const batch = limit < Infinity ? signals.slice(0, limit) : signals;
  console.log(`[lab] Processing ${batch.length} signal(s)${limit < Infinity ? ` (limit: ${limit})` : ""}`);

  let ok = 0, failed = 0;
  for (const signal of batch) {
    try {
      await processSignal(signal);
      ok++;
    } catch (err) {
      console.error(`[lab] ❌ ${signal.id}: ${err.message}`);
      state.errors++;
      failed++;
    }
  }

  console.log(`\n[lab] Batch done — ok: ${ok}, failed: ${failed}`);
  return ok + failed;
}

// ── Status ────────────────────────────────────────────────────────────────────

function printStatus() {
  const uptime = Math.round((Date.now() - new Date(state.started_at).getTime()) / 1000);
  console.log("\n╔══════════════════════════════════════════════╗");
  console.log("║   NEXUS AUTONOMOUS TRADING LAB — STATUS     ║");
  console.log("╠══════════════════════════════════════════════╣");
  console.log(`║ Started:    ${state.started_at.slice(0, 19).padEnd(32)}║`);
  console.log(`║ Uptime:     ${String(uptime + "s").padEnd(32)}║`);
  console.log(`║ Processed:  ${String(state.processed).padEnd(32)}║`);
  console.log(`║ Approved:   ${String(state.approved).padEnd(32)}║`);
  console.log(`║ Manual:     ${String(state.manual).padEnd(32)}║`);
  console.log(`║ Blocked:    ${String(state.blocked).padEnd(32)}║`);
  console.log(`║ Errors:     ${String(state.errors).padEnd(32)}║`);
  console.log("╠══════════════════════════════════════════════╣");
  console.log("║ NO AUTO EXECUTION. HUMAN APPROVAL REQUIRED. ║");
  console.log("╚══════════════════════════════════════════════╝\n");
}

// ── Main ──────────────────────────────────────────────────────────────────────

const args = process.argv.slice(2);
const limitIdx = args.indexOf("--limit");
const limit = limitIdx !== -1 ? Number(args[limitIdx + 1] ?? 1) : Infinity;

if (args.includes("--status")) {
  printStatus();
  process.exit(0);

} else if (args.includes("--poll")) {
  await sendSystemAlert("Nexus Autonomous Trading Lab started — poll mode active.");
  console.log(`[lab] Poll mode — interval: ${POLL_MS / 1000}s`);

  while (true) {
    try { await runBatch(); } catch (err) { console.error("[lab] Cycle error:", err.message); }
    await new Promise((r) => setTimeout(r, POLL_MS));
  }

} else {
  // --once or --limit N
  await runBatch(limit);
  printStatus();
  process.exit(0);
}
