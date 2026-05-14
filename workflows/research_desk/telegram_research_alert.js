import "dotenv/config";
import { shouldSendTelegram } from "../lib/telegram_spam_guard.js";
import { shouldSendTelegramNotification } from "../lib/telegram_notification_policy.js";

// ── SAFETY GUARD ──────────────────────────────────────────────────────────────
// This module is RESEARCH ONLY. Sends research desk alerts to Telegram.
// No trading, no broker connections.
// ─────────────────────────────────────────────────────────────────────────────

const TELEGRAM_BOT_TOKEN = process.env.TELEGRAM_BOT_TOKEN;
const TELEGRAM_CHAT_ID = process.env.TELEGRAM_CHAT_ID;

async function sendTelegramMessage(text) {
  const policy = shouldSendTelegramNotification("research_summary");
  if (!policy.ok) {
    console.log(`[telegram] Policy denied: ${policy.reason}`);
    return;
  }
  if ((process.env.TELEGRAM_RESEARCH_ALERTS_ENABLED || "false") !== "true") {
    console.log("[telegram] TELEGRAM_RESEARCH_ALERTS_ENABLED=false — suppressed.");
    return;
  }
  if (!TELEGRAM_BOT_TOKEN || !TELEGRAM_CHAT_ID) {
    console.warn("[telegram] TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set. Skipping.");
    return;
  }

  const url = `https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage`;
  const gate = shouldSendTelegram("research_desk_summary", text);
  if (!gate.ok) {
    console.log(`[telegram] Suppressed: ${gate.reason}`);
    return;
  }
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      chat_id: TELEGRAM_CHAT_ID,
      text,
      parse_mode: "HTML",
      disable_web_page_preview: true,
    }),
  });

  if (!res.ok) {
    const body = await res.text();
    throw new Error(`Telegram sendMessage failed (${res.status}): ${body}`);
  }

  const data = await res.json();
  if (!data.ok) {
    throw new Error(`Telegram API error: ${data.description}`);
  }

  return data;
}

function truncate(str, maxLen) {
  if (!str) return "";
  return str.length <= maxLen ? str : str.slice(0, maxLen - 1) + "…";
}

/**
 * Sends a research desk summary alert to Telegram.
 * Max message ~400 chars. Truncates gracefully.
 * @param {Array} briefs
 * @param {Array} hypotheses
 * @param {Array} gaps
 */
export async function sendResearchAlert(briefs = [], hypotheses = [], gaps = []) {
  const now = new Date().toLocaleString("en-US", {
    timeZone: "America/New_York",
    dateStyle: "short",
    timeStyle: "short",
  });

  const topHypothesis = hypotheses[0];
  const topTitle = topHypothesis
    ? truncate(topHypothesis.hypothesis_title, 80)
    : "None";

  const highGaps = gaps.filter((g) => g.severity === "high").length;
  const medGaps = gaps.filter((g) => g.severity === "medium").length;

  let message = `<b>Research Desk</b> | ${now} ET\n`;
  message += `Hypotheses: ${hypotheses.length} | Gaps: ${gaps.length} | Briefs: ${briefs.length}\n`;

  if (topHypothesis) {
    const priority = topHypothesis.priority_score != null
      ? parseFloat(topHypothesis.priority_score).toFixed(2)
      : "N/A";
    message += `\nTop: ${topTitle}\n`;
    message += `Priority: ${priority} | Asset: ${topHypothesis.asset_type ?? "all"}\n`;
  }

  if (highGaps > 0 || medGaps > 0) {
    message += `\nGap flags: ${highGaps} high, ${medGaps} medium\n`;
  }

  message += `\n<i>RESEARCH ONLY — No live trading</i>`;

  // Final truncation safety — Telegram limit is 4096 but we keep it short
  const final = truncate(message, 400);

  console.log("[telegram] Sending research alert...");
  try {
    await sendTelegramMessage(final);
    console.log("[telegram] Research alert sent.");
  } catch (err) {
    console.error("[telegram] Failed to send research alert:", err.message);
  }
}
