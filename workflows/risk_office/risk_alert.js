/**
 * risk_alert.js
 * Sends a combined AI proposal + risk office decision to Telegram.
 * One message per signal. Send-only.
 */

import "dotenv/config";

const BOT_TOKEN = process.env.TELEGRAM_BOT_TOKEN;
const CHAT_ID   = process.env.TELEGRAM_CHAT_ID;

const DECISION_EMOJI = {
  approved: "✅",
  rejected: "❌",
  held:     "⏸",
};

const AI_EMOJI = {
  proposed:     "🟢",
  blocked:      "🔴",
  needs_review: "🟡",
};

function fmt(n, decimals = 5) {
  if (n == null || Number(n) === 0) return "—";
  return Number(n).toFixed(decimals);
}

function fmtPct(n) {
  if (n == null) return "—";
  return `${Math.round(Number(n) * 100)}%`;
}

function fmtRR(rr) {
  if (!rr || rr === 0) return "—";
  return `1:${Number(rr).toFixed(2)}`;
}

function fmtPnl(pnl) {
  const v = Number(pnl ?? 0);
  const sign = v >= 0 ? "+" : "";
  return `${sign}$${Math.abs(v).toFixed(2)}`;
}

/**
 * Build the combined Telegram HTML message.
 *
 * @param {Object} proposal  - reviewed_signal_proposals row
 * @param {Object} decision  - evaluateProposal() result
 */
function buildMessage(proposal, decision) {
  const dEmoji = DECISION_EMOJI[decision.status] ?? "⚪";
  const aEmoji = AI_EMOJI[proposal.status]       ?? "⚪";
  const symbol = (proposal.symbol ?? "").replace("_", "");
  const side   = (proposal.side   ?? "").toUpperCase();

  const lines = [
    // ── Header ──────────────────────────────────────────────────────────────
    `${dEmoji} <b>NEXUS TRADE PROPOSAL + RISK DECISION</b>`,
    ``,

    // ── Signal ──────────────────────────────────────────────────────────────
    `<b>Symbol:</b>     ${symbol}`,
    `<b>Side:</b>       ${side}`,
    `<b>Strategy:</b>   ${proposal.strategy_id ?? "—"}`,
    `<b>Timeframe:</b>  ${proposal.timeframe ?? "—"}m`,
    ``,

    // ── Price levels ─────────────────────────────────────────────────────────
    `<b>Entry:</b>  ${fmt(proposal.entry_price)}`,
    `<b>SL:</b>     ${fmt(proposal.stop_loss)}`,
    `<b>TP:</b>     ${fmt(proposal.take_profit)}`,
    `<b>R:R:</b>    ${fmtRR(decision.rr_ratio)}`,
    ``,

    // ── AI Analysis ───────────────────────────────────────────────────────────
    `${aEmoji} <b>AI Analyst</b>`,
    `Confidence: ${fmtPct(proposal.ai_confidence)}`,
    ``,
    `<b>Market Context:</b>`,
    proposal.market_context ?? "—",
    ``,
    `<b>Risk Notes:</b>`,
    proposal.risk_notes ?? "—",
    ``,
    `<b>AI Recommendation:</b>`,
    proposal.recommendation ?? "—",
    ``,

    // ── Risk Office ───────────────────────────────────────────────────────────
    `${dEmoji} <b>Risk Office</b>`,
    `Decision:       <b>${(decision.status ?? "—").toUpperCase()}</b>`,
    `Risk Score:     ${decision.risk_score ?? "—"}/100`,
    `Daily P&amp;L:      ${fmtPnl(decision.daily_pnl_used)} / -$100 limit`,
    `Open Positions: ${decision.open_positions_count ?? 0} / 3 max`,
    ``,
  ];

  // Rejection reason (if any)
  if (decision.rejection_reason) {
    lines.push(`<b>Rejection Reason:</b>`);
    lines.push(decision.rejection_reason);
    lines.push(``);
  }

  // Checks breakdown (compact)
  const checks = decision.checks ?? {};
  const checkLines = [
    `R:R ≥ 2:1     ${checks.rr_ok       ? "✓" : "✗"}`,
    `Prices valid   ${checks.prices_ok   ? "✓" : "✗"}`,
    `Daily P&amp;L ok ${checks.daily_pnl_ok ? "✓" : "✗"}`,
    `Positions ok   ${checks.positions_ok ? "✓" : "✗"}`,
    `No duplicate   ${checks.no_duplicate ? "✓" : "✗"}`,
  ].join("  |  ");

  lines.push(`<code>${checkLines}</code>`);
  lines.push(``);
  lines.push(`<i>trace: ${proposal.trace_id ?? "—"}</i>`);

  return lines.join("\n");
}

/**
 * Send the combined proposal + risk alert to Telegram.
 *
 * @param {Object} proposal  - reviewed_signal_proposals row
 * @param {Object} decision  - result from evaluateProposal()
 */
export async function sendRiskAlert(proposal, decision) {
  if (!BOT_TOKEN || !CHAT_ID) {
    console.warn("[risk-alert] BOT_TOKEN or CHAT_ID missing — skipping.");
    return;
  }
  if ((process.env.TELEGRAM_AUTO_REPORTS_ENABLED || "false") !== "true") {
    console.log("telegram_policy denied=true reason=manual_only_default");
    return;
  }

  const text = buildMessage(proposal, decision);

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
    console.error(`[risk-alert] Send failed: ${res.status} ${body}`);
  } else {
    const symbol = (proposal.symbol ?? "").replace("_", "");
    console.log(`[risk-alert] Sent: ${symbol} ${proposal.side?.toUpperCase()} → ${decision.status.toUpperCase()}`);
  }
}

/**
 * Send a plain system notification.
 */
export async function sendRiskSystemAlert(text) {
  if (!BOT_TOKEN || !CHAT_ID) return;
  await fetch(`https://api.telegram.org/bot${BOT_TOKEN}/sendMessage`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      chat_id:    CHAT_ID,
      text:       `🏦 <b>Nexus Risk Office</b>\n${text}`,
      parse_mode: "HTML",
    }),
  });
}
