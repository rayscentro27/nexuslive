/**
 * pipeline_runner.js
 * Runs the full Nexus AI analyst pipeline end-to-end:
 *
 *   Supabase (enriched signals)
 *     → AI Analyst (OpenAI-compatible review)
 *     → Risk Office (rule evaluation)
 *     → Telegram (combined alert)
 *     → Human Review
 *
 * Modes:
 *   node pipeline_runner.js --once   Run one batch then exit.
 *   node pipeline_runner.js --poll   Run continuously.
 *   node pipeline_runner.js --status Show risk state then exit.
 *
 * NO LIVE TRADING. NO BROKER EXECUTION. ANALYSIS ONLY.
 */

import "dotenv/config";
import { pollEnrichedSignals }              from "./trading_analyst/analyst_poll.js";
import { buildContextPack }                 from "./trading_analyst/analyst_context.js";
import { writeProposal, markSignalReviewed } from "./trading_analyst/supabase_proposal_writer.js";
import { pollPendingProposals }             from "./risk_office/risk_poll.js";
import { evaluateProposal, getRiskState, LIMITS } from "./risk_office/risk_rules.js";
import { writeRiskDecision }               from "./risk_office/risk_writer.js";
import { sendRiskAlert, sendRiskSystemAlert } from "./risk_office/risk_alert.js";
import { readFileSync }                    from "fs";
import { fileURLToPath }                   from "url";
import { dirname, join }                   from "path";

const __dirname      = dirname(fileURLToPath(import.meta.url));
const SYSTEM_PROMPT  = readFileSync(join(__dirname, "trading_analyst/analyst_prompt.md"), "utf8");
const POLL_MS        = Number(process.env.POLL_INTERVAL_SECONDS ?? 60) * 1000;

function trimSlash(value) {
  return String(value ?? "").replace(/\/+$/, "");
}

function resolveGatewayConfig() {
  const baseUrl =
    process.env.NEXUS_LLM_BASE_URL ??
    process.env.OPENROUTER_BASE_URL ??
    process.env.OPENAI_BASE_URL ??
    "https://openrouter.ai/api/v1";

  const apiKey =
    process.env.NEXUS_LLM_API_KEY ??
    process.env.OPENROUTER_API_KEY ??
    process.env.OPENAI_API_KEY ??
    "";

  const model =
    process.env.NEXUS_LLM_MODEL ??
    process.env.OPENROUTER_MODEL ??
    process.env.OPENAI_MODEL ??
    "meta-llama/llama-3.3-70b-instruct";

  const root = trimSlash(baseUrl);
  const chatUrl =
    root.endsWith("/v1") || root.endsWith("/api/v1")
      ? `${root}/chat/completions`
      : `${root}/v1/chat/completions`;

  return { chatUrl, apiKey, model };
}

// ── AI Call (inlined from analyst_runner for single-process execution) ────────

function buildUserMessage(ctx) {
  const { signal, market_snapshot, strategy_context, research_context } = ctx;
  const snap = market_snapshot
    ? `Bid: ${market_snapshot.bid} | Ask: ${market_snapshot.ask} | Mid: ${market_snapshot.mid} | Spread: ${market_snapshot.spread} | Captured: ${market_snapshot.created_at}`
    : "No market snapshot available.";

  return [
    `## Signal to Review`,
    `Symbol:      ${signal.symbol}`,
    `Side:        ${signal.side}`,
    `Timeframe:   ${signal.timeframe}m`,
    `Strategy ID: ${signal.strategy_id ?? "none"}`,
    `Entry:       ${signal.entry_price}`,
    `Stop Loss:   ${signal.stop_loss}`,
    `Take Profit: ${signal.take_profit}`,
    `Confidence:  ${signal.confidence}`,
    `Trace ID:    ${signal.trace_id}`,
    ``,
    `## Strategy Context`, strategy_context,
    `## Market Snapshot`, snap,
    `## Research Context`, research_context,
    ``,
    `Review this signal and respond with JSON only.`,
  ].join("\n");
}

async function callAnalyst(ctx) {
  const gateway = resolveGatewayConfig();
  const headers = {
    "Content-Type":  "application/json",
  };
  if (gateway.apiKey) {
    headers["Authorization"] = `Bearer ${gateway.apiKey}`;
  }

  const res = await fetch(gateway.chatUrl, {
    method: "POST",
    headers,
    body: JSON.stringify({
      model: gateway.model,
      messages: [
        { role: "system", content: SYSTEM_PROMPT },
        { role: "user",   content: buildUserMessage(ctx) },
      ],
      temperature: 0.2,
      max_tokens:  1000,
    }),
    signal: AbortSignal.timeout(60_000),
  });

  if (!res.ok) throw new Error(`AI gateway: ${res.status} ${await res.text()}`);

  const data = await res.json();
  const raw  = (data?.choices?.[0]?.message?.content ?? "")
    .replace(/^```json\s*/i, "").replace(/^```\s*/i, "").replace(/```\s*$/i, "").trim();

  let proposal;
  try { proposal = JSON.parse(raw); }
  catch { throw new Error(`Non-JSON from AI:\n${raw.slice(0, 200)}`); }
  return proposal;
}

function enforceHardBlocks(proposal) {
  const entry = Number(proposal.entry_price);
  const sl    = Number(proposal.stop_loss);
  const tp    = Number(proposal.take_profit);
  if (!entry || !sl || !tp) {
    proposal.status    = "blocked";
    proposal.risk_notes = `[Auto-blocked] Missing entry/SL/TP. ${proposal.risk_notes ?? ""}`.trim();
    return;
  }
  const rr = Math.abs(tp - entry) / Math.abs(entry - sl);
  if (rr < 1.5) {
    proposal.status    = "blocked";
    proposal.risk_notes = `[Auto-blocked] R:R ${rr.toFixed(2)} below minimum 1.5. ${proposal.risk_notes ?? ""}`.trim();
  }
}

// ── Full Pipeline for One Signal ──────────────────────────────────────────────

async function processSignal(signal) {
  const label = `${(signal.symbol ?? "").replace("_","")} ${(signal.side ?? "").toUpperCase()} [${signal.id.slice(0,8)}]`;
  console.log(`\n[pipeline] ── Signal: ${label}`);

  // Step 1: AI Analyst
  const ctx      = await buildContextPack(signal);
  const proposal = await callAnalyst(ctx);
  proposal.trace_id = proposal.trace_id || signal.trace_id;
  enforceHardBlocks(proposal);

  const REQUIRED = ["symbol","side","entry_price","stop_loss","take_profit","ai_confidence","status","trace_id"];
  for (const f of REQUIRED) {
    if (proposal[f] == null || proposal[f] === "") throw new Error(`Proposal missing: ${f}`);
  }
  const VALID = ["proposed","blocked","needs_review"];
  if (!VALID.includes(proposal.status)) throw new Error(`Invalid proposal status: ${proposal.status}`);

  // Step 2: Write proposal
  const saved = await writeProposal(signal.id, proposal);
  await markSignalReviewed(signal.id);
  console.log(`[pipeline] AI → ${proposal.status}`);

  // Step 3: Risk Office (only if AI proposed)
  if (proposal.status !== "proposed") {
    // Blocked or needs_review — still send an analyst-only alert
    const { sendProposalAlert } = await import("./trading_analyst/telegram_proposal_alert.js");
    await sendProposalAlert(proposal);
    console.log(`[pipeline] Skipping risk office (AI status: ${proposal.status})`);
    return;
  }

  // The saved proposal is freshly written — evaluate it directly
  const decision = evaluateProposal({ ...proposal, id: saved?.id ?? signal.id });
  console.log(`[pipeline] Risk → ${decision.status} | R:R: ${decision.rr_ratio.toFixed(2)}`);

  await writeRiskDecision(saved?.id ?? signal.id, { ...proposal, signal_id: signal.id }, decision);
  await sendRiskAlert(proposal, decision);

  console.log(`[pipeline] ✅ Complete: ${label} → AI:${proposal.status} → Risk:${decision.status}`);
}

// ── Main ──────────────────────────────────────────────────────────────────────

async function runOnce() {
  console.log("\n[pipeline] ════════════════════════════════════");
  console.log("[pipeline] Nexus AI Pipeline — starting batch");
  console.log("[pipeline] ════════════════════════════════════");

  const signals = await pollEnrichedSignals();
  if (!signals.length) {
    console.log("[pipeline] No enriched signals to process.");
    return;
  }

  let ok = 0, failed = 0;
  for (const signal of signals) {
    try {
      await processSignal(signal);
      ok++;
    } catch (err) {
      console.error(`[pipeline] ❌ ${signal.id}: ${err.message}`);
      failed++;
    }
  }

  const state = getRiskState();
  console.log(`\n[pipeline] Batch done — signals: ${ok} ok, ${failed} failed`);
  console.log(`[pipeline] Risk state — P&L: $${state.daily_pnl.toFixed(2)} | Open positions: ${state.open_positions.length}/${LIMITS.MAX_OPEN_POSITIONS}`);
}

async function runPoll() {
  await sendRiskSystemAlert("Nexus AI Pipeline started — analyst + risk office active.");
  while (true) {
    try { await runOnce(); } catch (err) { console.error("[pipeline] Cycle error:", err.message); }
    await new Promise((r) => setTimeout(r, POLL_MS));
  }
}

const args = process.argv.slice(2);
if (args.includes("--status")) {
  const s = getRiskState();
  console.log("Daily P&L:", s.daily_pnl, "| Open:", s.open_positions.length, "| Reviewed:", s.total_reviewed);
  process.exit(0);
} else if (args.includes("--poll")) {
  runPoll().catch((e) => { console.error(e); process.exit(1); });
} else {
  runOnce().then(() => process.exit(0)).catch((e) => { console.error(e); process.exit(1); });
}
