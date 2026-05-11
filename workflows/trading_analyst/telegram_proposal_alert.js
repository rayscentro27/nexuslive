/**
 * telegram_proposal_alert.js
 * Sends a structured Telegram message for each AI trade proposal.
 * Send-only. No command handling.
 */

import "dotenv/config";

const BOT_TOKEN = process.env.TELEGRAM_BOT_TOKEN;
const CHAT_ID   = process.env.TELEGRAM_CHAT_ID;

const STATUS_EMOJI = {
  proposed:     "🟢",
  blocked:      "🔴",
  needs_review: "🟡",
};

/**
 * Format a numeric price to 5 decimal places.
 */
function fmt(n) {
  if (n == null || n === 0) return "—";
  return Number(n).toFixed(5);
}

/**
 * Calculate R:R ratio string from signal fields.
 */
function calcRR(entry, sl, tp) {
  if (!entry || !sl || !tp) return "N/A";
  const risk   = Math.abs(entry - sl);
  const reward = Math.abs(tp - entry);
  if (risk === 0) return "N/A";
  return `1:${(reward / risk).toFixed(2)}`;
}

/**
 * Build the Telegram HTML message for a proposal.
 */
function buildMessage(proposal) {
  const emoji  = STATUS_EMOJI[proposal.status] ?? "⚪";
  const symbol = (proposal.symbol ?? "").replace("_", "");
  const side   = (proposal.side ?? "").toUpperCase();
  const conf   = proposal.ai_confidence != null
    ? `${Math.round(proposal.ai_confidence * 100)}%`
    : "—";
  const rr     = calcRR(proposal.entry_price, proposal.stop_loss, proposal.take_profit);
  const status = (proposal.status ?? "unknown").toUpperCase().replace("_", " ");

  return [
    `${emoji} <b>NEXUS AI TRADE PROPOSAL</b>`,
    ``,
    `<b>Symbol:</b> ${symbol}`,
    `<b>Side:</b>   ${side}`,
    `<b>Strategy:</b> ${proposal.strategy_id ?? "—"}`,
    `<b>Timeframe:</b> ${proposal.timeframe ?? "—"}m`,
    ``,
    `<b>Entry:</b>  ${fmt(proposal.entry_price)}`,
    `<b>SL:</b>     ${fmt(proposal.stop_loss)}`,
    `<b>TP:</b>     ${fmt(proposal.take_profit)}`,
    `<b>R:R:</b>    ${rr}`,
    ``,
    `<b>AI Confidence:</b> ${conf}`,
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
    `${emoji} <b>${status}</b>`,
    ``,
    `<i>trace: ${proposal.trace_id ?? "—"}</i>`,
  ].join("\n");
}

/**
 * Send a proposal alert to Telegram.
 *
 * @param {Object} proposal - row from reviewed_signal_proposals
 * @returns {Promise<void>}
 */
export async function sendProposalAlert(proposal) {
  if (!BOT_TOKEN || !CHAT_ID) {
    console.warn("[telegram] BOT_TOKEN or CHAT_ID missing — skipping alert.");
    return;
  }

  const text = buildMessage(proposal);

  const res = await fetch(
    `https://api.telegram.org/bot${BOT_TOKEN}/sendMessage`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        chat_id:    CHAT_ID,
        text,
        parse_mode: "HTML",
        disable_web_page_preview: true,
      }),
    }
  );

  if (!res.ok) {
    const body = await res.text();
    console.error(`[telegram] Send failed: ${res.status} ${body}`);
  } else {
    console.log(`[telegram] Alert sent for ${proposal.symbol} ${proposal.side?.toUpperCase()} — ${proposal.status}`);
  }
}

/**
 * Send a plain system notification (errors, startup, etc.)
 *
 * @param {string} text
 */
export async function sendSystemAlert(text) {
  if (!BOT_TOKEN || !CHAT_ID) return;

  await fetch(`https://api.telegram.org/bot${BOT_TOKEN}/sendMessage`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      chat_id:    CHAT_ID,
      text:       `⚙️ <b>Nexus Analyst</b>\n${text}`,
      parse_mode: "HTML",
      disable_web_page_preview: true,
    }),
  });
}
