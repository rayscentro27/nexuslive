/**
 * analyst_runner.js
 * Calls an OpenAI-compatible LLM gateway to review a signal and returns a
 * structured proposal. Handles both FOREX and OPTIONS signals.
 *
 * NO LIVE TRADING. NO BROKER EXECUTION. ANALYSIS ONLY.
 */

import "dotenv/config";
import { readFileSync }    from "fs";
import { fileURLToPath }   from "url";
import { dirname, join }   from "path";

const __dirname      = dirname(fileURLToPath(import.meta.url));
const SYSTEM_PROMPT  = readFileSync(join(__dirname, "analyst_prompt.md"), "utf8");

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

const DEFAULT_GATEWAY = resolveGatewayConfig();

const VALID_STATUSES = ["proposed", "blocked", "needs_review"];
const REQUIRED_BASE  = ["symbol", "asset_type", "side", "entry_price", "ai_confidence", "status", "trace_id"];

// ── User message builder ──────────────────────────────────────────────────────

function buildUserMessage(ctx) {
  const { signal, snapshot, researchContext, strategyContext, claimsContext, optionsContext } = ctx;

  const snapLine = snapshot
    ? `Bid: ${snapshot.bid} | Ask: ${snapshot.ask} | Mid: ${snapshot.mid} | Spread: ${snapshot.spread} | At: ${snapshot.created_at}`
    : "No market snapshot available.";

  const lines = [
    `## Signal`,
    `Asset type:  ${signal.asset_type}`,
    `Symbol:      ${signal.symbol}`,
    `Side:        ${signal.side}`,
    `Timeframe:   ${signal.timeframe}m`,
    `Strategy:    ${signal.strategy_id ?? "none"}`,
    `Entry:       ${signal.entry_price}`,
    `Stop Loss:   ${signal.stop_loss ?? 0}`,
    `Take Profit: ${signal.take_profit ?? 0}`,
    `Confidence:  ${signal.confidence ?? "—"}`,
    `Session:     ${signal.session_label ?? "—"}`,
    `Trace ID:    ${signal.trace_id}`,
    ``,
    `## Market Snapshot`,
    snapLine,
    ``,
    `## Strategy Context`,
    strategyContext,
    ``,
    `## Research Context`,
    researchContext,
    ``,
    `## Research Claims`,
    claimsContext,
  ];

  if (optionsContext) {
    lines.push(``, `## Options Context`);
    for (const [k, v] of Object.entries(optionsContext)) {
      lines.push(`${k}: ${v}`);
    }
  }

  lines.push(``, `Evaluate this signal and respond with JSON only.`);
  return lines.join("\n");
}

// ── AI Gateway Call ───────────────────────────────────────────────────────────

export async function runAnalyst(ctx) {
  const gateway = resolveGatewayConfig();
  const headers = {
    "Content-Type": "application/json",
  };
  if (gateway.apiKey) {
    headers["Authorization"] = `Bearer ${gateway.apiKey}`;
  }

  const res = await fetch(gateway.chatUrl, {
    method: "POST",
    headers,
    body: JSON.stringify({
      model:       gateway.model,
      messages: [
        { role: "system", content: SYSTEM_PROMPT },
        { role: "user",   content: buildUserMessage(ctx) },
      ],
      temperature: 0.2,
      max_tokens:  1200,
    }),
    signal: AbortSignal.timeout(90_000),
  });

  if (!res.ok) throw new Error(`AI gateway ${res.status}: ${await res.text()}`);

  const data = await res.json();
  const raw  = (data?.choices?.[0]?.message?.content ?? "")
    .replace(/^```json\s*/i, "")
    .replace(/^```\s*/i, "")
    .replace(/```\s*$/i, "")
    .trim();

  let proposal;
  try {
    proposal = JSON.parse(raw);
  } catch {
    throw new Error(`AI returned non-JSON:\n${raw.slice(0, 300)}`);
  }

  return proposal;
}

// ── Validation ────────────────────────────────────────────────────────────────

export function validateProposal(proposal, signal) {
  // Required fields
  for (const f of REQUIRED_BASE) {
    if (proposal[f] == null || proposal[f] === "") {
      throw new Error(`Proposal missing field: ${f}`);
    }
  }

  // Status must be valid
  if (!VALID_STATUSES.includes(proposal.status)) {
    throw new Error(`Invalid status: ${proposal.status}`);
  }

  // Ensure trace_id propagated
  if (!proposal.trace_id) proposal.trace_id = signal.trace_id;

  // Ensure asset_type set
  if (!proposal.asset_type) proposal.asset_type = signal.asset_type;

  // Hard block: forex with missing SL or bad R:R
  if (proposal.asset_type === "forex" && proposal.status === "proposed") {
    const e  = Number(proposal.entry_price ?? 0);
    const sl = Number(proposal.stop_loss   ?? 0);
    const tp = Number(proposal.take_profit ?? 0);

    if (!e || !sl || !tp) {
      proposal.status    = "blocked";
      proposal.risk_notes = `[Auto-blocked] Missing entry/SL/TP. ${proposal.risk_notes ?? ""}`.trim();
    } else {
      const rr = Math.abs(tp - e) / Math.abs(e - sl);
      if (rr < 1.5) {
        proposal.status    = "blocked";
        proposal.risk_notes = `[Auto-blocked] R:R ${rr.toFixed(2)} < 1.5 minimum. ${proposal.risk_notes ?? ""}`.trim();
      }
    }
  }

  return proposal;
}
