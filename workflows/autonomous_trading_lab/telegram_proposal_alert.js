/**
 * telegram_proposal_alert.js
 * Sends the AI Analyst proposal alert to Telegram.
 * Send-only. No command handling.
 */

import "dotenv/config";

const BOT   = process.env.TELEGRAM_BOT_TOKEN;
const CHAT  = process.env.TELEGRAM_CHAT_ID;

const STATUS_EMOJI = { proposed: "🟢", blocked: "🔴", needs_review: "🟡" };

function fmt(n, d = 5)  { return n && Number(n) !== 0 ? Number(n).toFixed(d) : "—"; }
function pct(n)          { return n != null ? `${Math.round(Number(n) * 100)}%` : "—"; }
function sym(s)          { return (s ?? "").replace("_", ""); }

export async function sendProposalAlert(proposal) {
  if (!BOT || !CHAT) return;

  const e  = STATUS_EMOJI[proposal.status] ?? "⚪";
  const isOptions = proposal.asset_type === "options";

  const lines = [
    `${e} <b>NEXUS AI TRADE PROPOSAL</b>`,
    ``,
    `<b>Symbol:</b>    ${sym(proposal.symbol)}`,
    `<b>Type:</b>      ${(proposal.asset_type ?? "forex").toUpperCase()}`,
    `<b>Side:</b>      ${(proposal.side ?? "").toUpperCase()}`,
    `<b>Strategy:</b>  ${proposal.strategy_id ?? "—"}`,
    `<b>Timeframe:</b> ${proposal.timeframe ?? "—"}${isOptions ? "" : "m"}`,
    ``,
  ];

  if (isOptions) {
    lines.push(
      `<b>Underlying:</b>  ${proposal.underlying ?? sym(proposal.symbol)}`,
      `<b>Entry:</b>       ${fmt(proposal.entry_price)}`,
      `<b>Expiry note:</b> ${proposal.expiration_note ?? "—"}`,
      `<b>Strike note:</b> ${proposal.strike_note ?? "—"}`,
      `<b>Premium:</b>     ${proposal.premium_estimate ?? "—"}`,
      `<b>IV context:</b>  ${proposal.iv_context ?? "—"}`,
      ``,
    );
  } else {
    const e_  = Number(proposal.entry_price ?? 0);
    const sl_ = Number(proposal.stop_loss   ?? 0);
    const tp_ = Number(proposal.take_profit ?? 0);
    const rr  = e_ && sl_ && tp_
      ? `1:${(Math.abs(tp_ - e_) / Math.abs(e_ - sl_)).toFixed(2)}`
      : "—";
    lines.push(
      `<b>Entry:</b> ${fmt(proposal.entry_price)}`,
      `<b>SL:</b>    ${fmt(proposal.stop_loss)}`,
      `<b>TP:</b>    ${fmt(proposal.take_profit)}`,
      `<b>R:R:</b>   ${rr}`,
      ``,
    );
  }

  lines.push(
    `<b>AI Confidence:</b> ${pct(proposal.ai_confidence)}`,
    ``,
    `<b>Market Context:</b>`,
    proposal.market_context ?? "—",
    ``,
    `<b>Risk Notes:</b>`,
    proposal.risk_notes ?? "—",
    ``,
    `<b>Recommendation:</b>`,
    proposal.recommendation ?? "—",
    ``,
    `${e} <b>${(proposal.status ?? "").toUpperCase().replace("_", " ")}</b>`,
    `<i>trace: ${proposal.trace_id ?? "—"}</i>`,
  );

  await tgSend(lines.join("\n"));
  console.log(`[tg-proposal] Sent: ${sym(proposal.symbol)} ${(proposal.side ?? "").toUpperCase()} → ${proposal.status}`);
}

async function tgSend(text) {
  const res = await fetch(`https://api.telegram.org/bot${BOT}/sendMessage`, {
    method:  "POST",
    headers: { "Content-Type": "application/json" },
    body:    JSON.stringify({ chat_id: CHAT, text, parse_mode: "HTML", disable_web_page_preview: true }),
  });
  if (!res.ok) console.error(`[tg] ${res.status} ${await res.text()}`);
}
