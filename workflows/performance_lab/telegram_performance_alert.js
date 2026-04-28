import "dotenv/config";

const TELEGRAM_BOT_TOKEN = process.env.TELEGRAM_BOT_TOKEN;
const TELEGRAM_CHAT_ID = process.env.TELEGRAM_CHAT_ID;

async function sendTelegramMessage(text) {
  if (!TELEGRAM_BOT_TOKEN || !TELEGRAM_CHAT_ID) {
    console.warn("[telegram] TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set. Skipping.");
    return;
  }

  const url = `https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage`;
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

function rankEmoji(label) {
  switch (label) {
    case "elite": return "★";
    case "strong": return "▲";
    case "average": return "◆";
    case "weak": return "▼";
    case "poor": return "✗";
    default: return "?";
  }
}

function pct(val) {
  if (val === null || val === undefined) return "N/A";
  return `${(val * 100).toFixed(1)}%`;
}

function num(val, decimals = 2) {
  if (val === null || val === undefined) return "N/A";
  return parseFloat(val).toFixed(decimals);
}

/**
 * Sends a full performance summary to Telegram.
 * @param {Array} forexRankings - Output from rankForexStrategies()
 * @param {Array} optionsRankings - Output from rankOptionsStrategies()
 * @param {Object} agentScorecards - { analystMetrics, riskMetrics }
 */
export async function sendPerformanceSummary(
  forexRankings = [],
  optionsRankings = [],
  agentScorecards = {}
) {
  const now = new Date().toLocaleString("en-US", {
    timeZone: "America/New_York",
    dateStyle: "medium",
    timeStyle: "short",
  });

  let message = `<b>Nexus Performance Lab Report</b>\n`;
  message += `<i>${now} ET</i>\n\n`;

  // --- Forex Rankings ---
  message += `<b>Forex Strategy Rankings</b>\n`;
  if (!forexRankings.length) {
    message += `  No forex data yet.\n`;
  } else {
    const top3 = forexRankings.slice(0, 3);
    for (let i = 0; i < top3.length; i++) {
      const r = top3[i];
      const emoji = rankEmoji(r.ranking_label);
      message += `  ${i + 1}. ${emoji} <b>${r.strategy_id}</b>\n`;
      message += `      Win: ${pct(r.win_rate)}  Expcy: ${num(r.expectancy)}R  Score: ${num(r.score, 1)}\n`;
    }
    if (forexRankings.length > 3) {
      message += `  <i>+${forexRankings.length - 3} more strategies</i>\n`;
    }
  }

  message += `\n`;

  // --- Options Rankings ---
  message += `<b>Options Strategy Performance</b>\n`;
  if (!optionsRankings.length) {
    message += `  No options data yet.\n`;
  } else {
    const top3 = optionsRankings.slice(0, 3);
    for (let i = 0; i < top3.length; i++) {
      const r = top3[i];
      const emoji = rankEmoji(r.ranking_label);
      message += `  ${i + 1}. ${emoji} <b>${r.strategy_type}</b>\n`;
      message += `      Win: ${pct(r.win_rate)}  AvgPnL: ${num(r.avg_pnl_pct, 1)}%  Score: ${num(r.score, 1)}\n`;
    }
    if (optionsRankings.length > 3) {
      message += `  <i>+${optionsRankings.length - 3} more strategies</i>\n`;
    }
  }

  message += `\n`;

  // --- Analyst Metrics ---
  const analyst = agentScorecards.analystMetrics;
  message += `<b>AI Analyst</b>\n`;
  if (!analyst) {
    message += `  No analyst metrics available.\n`;
  } else {
    message += `  Reviewed: ${analyst.total_reviewed}  Block: ${pct(analyst.block_rate)}  Proposed: ${pct(analyst.proposed_rate)}\n`;
    message += `  Avg Confidence: ${num(analyst.avg_confidence, 3)}\n`;
    if (analyst.high_conf_win_rate !== null) {
      message += `  High Conf Win Rate: ${pct(analyst.high_conf_win_rate)}\n`;
    }
    if (analyst.low_conf_win_rate !== null) {
      message += `  Low Conf Win Rate: ${pct(analyst.low_conf_win_rate)}\n`;
    }
  }

  message += `\n`;

  // --- Risk Office Metrics ---
  const risk = agentScorecards.riskMetrics;
  message += `<b>Risk Office</b>\n`;
  if (!risk) {
    message += `  No risk metrics available.\n`;
  } else {
    message += `  Total: ${risk.total_decisions}  Approved: ${pct(risk.approval_rate)}  Blocked: ${risk.blocked}\n`;
    message += `  Avg Risk Score: ${num(risk.avg_risk_score, 3)}\n`;
    if (risk.false_approval_rate !== null) {
      message += `  False Approval Rate: ${pct(risk.false_approval_rate)}\n`;
    }
    if (risk.top_flags.length) {
      message += `  Top Flag: ${risk.top_flags[0].flag} (${risk.top_flags[0].count}x)\n`;
    }
  }

  message += `\n<i>RESEARCH ONLY — No live trading</i>`;

  console.log("[telegram] Sending performance summary...");
  try {
    await sendTelegramMessage(message);
    console.log("[telegram] Performance summary sent.");
  } catch (err) {
    console.error("[telegram] Failed to send performance summary:", err.message);
  }
}

/**
 * Sends a plain system alert to Telegram.
 * @param {string} text
 */
export async function sendSystemAlert(text) {
  const safeText = `<b>Nexus System Alert</b>\n\n${text}`;
  console.log("[telegram] Sending system alert...");
  try {
    await sendTelegramMessage(safeText);
    console.log("[telegram] Alert sent.");
  } catch (err) {
    console.error("[telegram] Failed to send alert:", err.message);
  }
}
