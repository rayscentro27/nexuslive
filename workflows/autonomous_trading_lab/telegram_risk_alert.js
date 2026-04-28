/**
 * telegram_risk_alert.js
 * Sends the Risk Office decision alert to Telegram.
 */

import "dotenv/config";

const BOT  = process.env.TELEGRAM_BOT_TOKEN;
const CHAT = process.env.TELEGRAM_CHAT_ID;

const DECISION_EMOJI = { approved: "✅", manual_review: "🟡", blocked: "🚫" };
const FLAG_LABEL = {
  poor_rr:          "Poor R:R",
  low_confidence:   "Low Confidence",
  high_spread:      "High Spread",
  unknown_strategy: "Unknown Strategy",
  duplicate_signal: "Duplicate Signal",
  conflict:         "Position Conflict",
  missing_sl:       "Missing Stop Loss",
  low_rr_options:   "Options R:R Issue",
};

export async function sendRiskAlert(proposal, riskResult) {
  if (!BOT || !CHAT) return;

  const e     = DECISION_EMOJI[riskResult.decision] ?? "⚪";
  const score = riskResult.score ?? "—";
  const sym   = (proposal.symbol ?? "").replace("_", "");

  // Active flags
  const activeFlags = Object.entries(riskResult.flags ?? {})
    .filter(([, v]) => v)
    .map(([k]) => `  ✗ ${FLAG_LABEL[k] ?? k}`)
    .join("\n") || "  ✓ None";

  const lines = [
    `${e} <b>NEXUS RISK OFFICE</b>`,
    ``,
    `<b>Symbol:</b>    ${sym}`,
    `<b>Type:</b>      ${(proposal.asset_type ?? "forex").toUpperCase()}`,
    `<b>Side:</b>      ${(proposal.side ?? "").toUpperCase()}`,
    `<b>Strategy:</b>  ${proposal.strategy_id ?? "—"}`,
    ``,
    `<b>Risk Score:</b>  ${score}/100`,
    `<b>Decision:</b>    <b>${(riskResult.decision ?? "").toUpperCase().replace("_", " ")}</b>`,
    ``,
    `<b>Risk Flags:</b>`,
    activeFlags,
    ``,
    `<b>Risk Notes:</b>`,
    riskResult.riskNotes ?? "—",
    ``,
    `<i>trace: ${riskResult.trace_id ?? "—"}</i>`,
  ];

  await tgSend(lines.join("\n"));
  console.log(`[tg-risk] Sent: ${sym} → ${riskResult.decision?.toUpperCase()} (${score}/100)`);
}

async function tgSend(text) {
  const res = await fetch(`https://api.telegram.org/bot${BOT}/sendMessage`, {
    method:  "POST",
    headers: { "Content-Type": "application/json" },
    body:    JSON.stringify({ chat_id: CHAT, text, parse_mode: "HTML", disable_web_page_preview: true }),
  });
  if (!res.ok) console.error(`[tg] ${res.status} ${await res.text()}`);
}
