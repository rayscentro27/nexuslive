/**
 * analyst_runner.js
 * Main entry point for the Nexus AI Trading Analyst workflow.
 *
 * Modes:
 *   node analyst_runner.js --once    Run one batch of up to 5 signals then exit.
 *   node analyst_runner.js --poll    Run continuously on POLL_INTERVAL_SECONDS.
 *
 * Pipeline per signal:
 *   1. Load signal from tv_normalized_signals (status = enriched)
 *   2. Build context pack (market snapshot + research)
 *   3. Call an OpenAI-compatible AI gateway for structured analysis
 *   4. Validate JSON response
 *   5. Write proposal to reviewed_signal_proposals
 *   6. Mark signal as reviewed
 *   7. Send Telegram alert
 *
 * NO LIVE TRADING. NO BROKER EXECUTION. ANALYSIS ONLY.
 */

import "dotenv/config";
import { readFileSync } from "fs";
import { fileURLToPath } from "url";
import { dirname, join } from "path";

import { pollEnrichedSignals }              from "./analyst_poll.js";
import { buildContextPack }                 from "./analyst_context.js";
import { writeProposal, markSignalReviewed } from "./supabase_proposal_writer.js";
import { sendProposalAlert, sendSystemAlert } from "./telegram_proposal_alert.js";

const __dirname = dirname(fileURLToPath(import.meta.url));

// ── Config ────────────────────────────────────────────────────────────────────

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

  return { baseUrl: root, apiKey, model, chatUrl };
}

const POLL_INTERVAL_MS    = Number(process.env.POLL_INTERVAL_SECONDS ?? 60) * 1000;

// Load system prompt from analyst_prompt.md
const SYSTEM_PROMPT = readFileSync(join(__dirname, "analyst_prompt.md"), "utf8");

// ── AI Call ───────────────────────────────────────────────────────────────────

/**
 * Build the user message for the AI gateway from the context pack.
 */
function buildUserMessage(ctx) {
  const { signal, market_snapshot, strategy_context, research_context } = ctx;

  const snap = market_snapshot
    ? `Bid: ${market_snapshot.bid} | Ask: ${market_snapshot.ask} | Mid: ${market_snapshot.mid} | Spread: ${market_snapshot.spread} pips | Captured: ${market_snapshot.created_at}`
    : "No market snapshot available.";

  return [
    `## Signal to Review`,
    ``,
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
    `## Strategy Context`,
    strategy_context,
    ``,
    `## Market Snapshot`,
    snap,
    ``,
    `## Research Context`,
    research_context,
    ``,
    `Review this signal and respond with JSON only as specified in your instructions.`,
  ].join("\n");
}

/**
 * Call the configured OpenAI-compatible chat completions endpoint and return
 * parsed JSON proposal.
 * Returns null on failure (logged, not thrown — allows other signals to continue).
 */
async function callAnalyst(ctx) {
  const userMessage = buildUserMessage(ctx);
  const gateway = resolveGatewayConfig();

  const body = {
    model: gateway.model,
    messages: [
      { role: "system",  content: SYSTEM_PROMPT },
      { role: "user",    content: userMessage },
    ],
    temperature: 0.2,
    max_tokens: 1000,
  };

  const headers = {
    "Content-Type":  "application/json",
  };
  if (gateway.apiKey) {
    headers["Authorization"] = `Bearer ${gateway.apiKey}`;
  }

  const res = await fetch(gateway.chatUrl, {
    method: "POST",
    headers,
    body: JSON.stringify(body),
    signal: AbortSignal.timeout(60_000),
  });

  if (!res.ok) {
    const errBody = await res.text();
    throw new Error(`AI gateway request failed: ${res.status} ${errBody}`);
  }

  const data = await res.json();
  const raw  = data?.choices?.[0]?.message?.content ?? "";

  // Strip markdown fences if model wraps output anyway
  const cleaned = raw
    .replace(/^```json\s*/i, "")
    .replace(/^```\s*/i, "")
    .replace(/```\s*$/i, "")
    .trim();

  let proposal;
  try {
    proposal = JSON.parse(cleaned);
  } catch {
    throw new Error(`AI returned non-JSON:\n${cleaned.slice(0, 300)}`);
  }

  return proposal;
}

// ── Validation ────────────────────────────────────────────────────────────────

const REQUIRED_FIELDS = [
  "symbol", "side", "entry_price", "stop_loss", "take_profit",
  "ai_confidence", "status", "trace_id",
];

const VALID_STATUSES = ["proposed", "blocked", "needs_review"];

function validateProposal(proposal) {
  for (const field of REQUIRED_FIELDS) {
    if (proposal[field] == null || proposal[field] === "") {
      throw new Error(`Proposal missing required field: ${field}`);
    }
  }
  if (!VALID_STATUSES.includes(proposal.status)) {
    throw new Error(`Invalid proposal status: ${proposal.status}`);
  }
}

/**
 * Enforce hard-block rules even if AI missed them.
 * Mutates proposal.status to 'blocked' if criteria are met.
 */
function enforceHardBlocks(proposal) {
  const entry = Number(proposal.entry_price);
  const sl    = Number(proposal.stop_loss);
  const tp    = Number(proposal.take_profit);

  if (!entry || !sl || !tp) {
    proposal.status   = "blocked";
    proposal.risk_notes = `[Auto-blocked] Missing entry/SL/TP. ${proposal.risk_notes ?? ""}`.trim();
    return;
  }

  const risk   = Math.abs(entry - sl);
  const reward = Math.abs(tp - entry);
  const rr     = risk > 0 ? reward / risk : 0;

  if (rr < 1.5) {
    proposal.status    = "blocked";
    proposal.risk_notes = `[Auto-blocked] R:R ${rr.toFixed(2)} below minimum 1.5. ${proposal.risk_notes ?? ""}`.trim();
  }
}

// ── Single Signal Runner ──────────────────────────────────────────────────────

async function processSignal(signal) {
  const label = `${signal.symbol} ${signal.side?.toUpperCase()} [${signal.id.slice(0, 8)}]`;
  console.log(`\n[runner] Processing: ${label}`);

  // 1. Build context
  const ctx = await buildContextPack(signal);
  console.log(`[runner] Context ready — snapshot: ${ctx.market_snapshot ? "✓" : "none"}`);

  // 2. Call AI
  const proposal = await callAnalyst(ctx);
  console.log(`[runner] AI responded — status: ${proposal.status}`);

  // 3. Validate
  validateProposal(proposal);
  enforceHardBlocks(proposal);

  // Ensure trace_id is propagated
  proposal.trace_id = proposal.trace_id || signal.trace_id;

  // 4. Write to Supabase
  const saved = await writeProposal(signal.id, proposal);

  // 5. Mark signal as reviewed
  await markSignalReviewed(signal.id);

  // 6. Send Telegram alert
  await sendProposalAlert(proposal);

  console.log(`[runner] ✅ Done: ${label} → ${proposal.status}`);
  return saved;
}

// ── Main ──────────────────────────────────────────────────────────────────────

async function runOnce() {
  console.log(`[runner] Starting — mode: once`);
  const signals = await pollEnrichedSignals();

  if (!signals.length) {
    console.log("[runner] No enriched signals to process.");
    return;
  }

  let ok = 0, failed = 0;
  for (const signal of signals) {
    try {
      await processSignal(signal);
      ok++;
    } catch (err) {
      console.error(`[runner] ❌ Failed ${signal.id}: ${err.message}`);
      failed++;
    }
  }

  console.log(`\n[runner] Batch complete — processed: ${ok}, failed: ${failed}`);
}

async function runPoll() {
  console.log(`[runner] Starting — mode: poll (every ${POLL_INTERVAL_MS / 1000}s)`);
  await sendSystemAlert("Nexus AI Trading Analyst started — polling mode active.");

  while (true) {
    try {
      await runOnce();
    } catch (err) {
      console.error(`[runner] Poll cycle error: ${err.message}`);
    }
    await new Promise((r) => setTimeout(r, POLL_INTERVAL_MS));
  }
}

// Parse args
const args = process.argv.slice(2);

if (args.includes("--poll")) {
  runPoll().catch((err) => {
    console.error("[runner] Fatal:", err);
    process.exit(1);
  });
} else {
  // Default: --once
  runOnce()
    .then(() => process.exit(0))
    .catch((err) => {
      console.error("[runner] Fatal:", err);
      process.exit(1);
    });
}
