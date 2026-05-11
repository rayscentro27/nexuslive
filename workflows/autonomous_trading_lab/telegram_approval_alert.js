/**
 * telegram_approval_alert.js
 * Sends human approval request to Telegram.
 * The human reviews and executes manually (Webull / OANDA).
 * This system does NOT auto-execute. Send-only.
 */

import "dotenv/config";

const BOT  = process.env.TELEGRAM_BOT_TOKEN;
const CHAT = process.env.TELEGRAM_CHAT_ID;

const DECISION_EMOJI = { approved: "✅", manual_review: "⚠️" };

export async function sendApprovalAlert(queueItem) {
  if (!BOT || !CHAT) return;

  const e      = DECISION_EMOJI[queueItem.decision] ?? "📋";
  const sym    = (queueItem.symbol ?? "").replace("_", "");
  const type   = (queueItem.asset_type ?? "forex").toUpperCase();
  const strat  = queueItem.strategy_id ?? "—";
  const score  = queueItem.risk_score ?? "—";
  const dec    = (queueItem.decision ?? "").toUpperCase().replace("_", " ");

  const isOptions = (queueItem.asset_type ?? "forex") === "options";

  const lines = [
    `${e} <b>NEXUS APPROVAL REQUIRED</b>`,
    ``,
    `<b>Symbol:</b>      ${sym}`,
    `<b>Asset Type:</b>  ${type}`,
    `<b>Strategy:</b>    ${strat}`,
    `<b>Risk Score:</b>  ${score}/100`,
    `<b>Risk Decision:</b> ${dec}`,
    ``,
    isOptions
      ? `<b>Action:</b> Review options proposal in Webull.\nSelect expiry + strike manually.\nConfirm premium before entering.`
      : `<b>Action:</b> Review FOREX signal.\nEnter manually in Webull or OANDA if approved.`,
    ``,
    `<b>⚠️ NO AUTO-EXECUTION</b>`,
    `This is a proposal only. Human approval and manual execution required.`,
    ``,
    `<i>Queue ID: ${queueItem.id ?? "—"}</i>`,
    `<i>trace: ${queueItem.trace_id ?? queueItem.proposal_id ?? "—"}</i>`,
  ];

  await tgSend(lines.join("\n"));
}

export async function sendSystemAlert(text) {
  if (!BOT || !CHAT) return;
  await tgSend(`🏦 <b>Nexus Trading Lab</b>\n${text}`);
}

async function tgSend(text) {
  const res = await fetch(`https://api.telegram.org/bot${BOT}/sendMessage`, {
    method:  "POST",
    headers: { "Content-Type": "application/json" },
    body:    JSON.stringify({ chat_id: CHAT, text, parse_mode: "HTML", disable_web_page_preview: true }),
  });
  if (!res.ok) console.error(`[tg] ${res.status} ${await res.text()}`);
}
