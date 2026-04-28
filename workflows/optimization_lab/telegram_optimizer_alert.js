// telegram_optimizer_alert.js — Sends optimization reports to Telegram
// RESEARCH ONLY — no live trading, no broker execution, no order placement

import "dotenv/config";

const BOT_TOKEN = process.env.TELEGRAM_BOT_TOKEN;
const CHAT_ID = process.env.TELEGRAM_CHAT_ID;

const TELEGRAM_API = `https://api.telegram.org/bot${BOT_TOKEN}`;

// ---------------------------------------------------------------------------
// sendOptimizationReport
// ---------------------------------------------------------------------------
/**
 * Sends a formatted optimization report to Telegram.
 *
 * Sections:
 *   - Header: NEXUS OPTIMIZATION LAB REPORT
 *   - Forex Optimizations (top 3 by improvement_score)
 *   - Options Optimizations (top 3)
 *   - Threshold Recommendations
 *   - Confidence Calibration Status
 *   - Footer: NO AUTO CHANGES — human review required
 *
 * @param {Object} report  Result from runFullOptimization() or similar
 * @returns {Promise<Object>}  Telegram API response
 */
export async function sendOptimizationReport(report) {
  if (!BOT_TOKEN || !CHAT_ID) {
    console.error("[telegram_optimizer_alert] TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set.");
    return null;
  }

  const message = buildReportMessage(report);

  console.log("[telegram_optimizer_alert] Sending optimization report to Telegram...");
  return sendTelegramMessage(message);
}

// ---------------------------------------------------------------------------
// sendSystemAlert
// ---------------------------------------------------------------------------
/**
 * Sends a plain system alert message to Telegram.
 *
 * @param {string} text  Alert message text
 * @returns {Promise<Object>}  Telegram API response
 */
export async function sendSystemAlert(text) {
  if (!BOT_TOKEN || !CHAT_ID) {
    console.error("[telegram_optimizer_alert] TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set.");
    return null;
  }

  const message = `<b>NEXUS SYSTEM ALERT</b>\n\n${escapeHtml(text)}`;
  console.log("[telegram_optimizer_alert] Sending system alert...");
  return sendTelegramMessage(message);
}

// ---------------------------------------------------------------------------
// Message builder
// ---------------------------------------------------------------------------
function buildReportMessage(report) {
  const lines = [];
  const ts = report.generated_at
    ? new Date(report.generated_at).toLocaleString("en-US", { timeZone: "America/New_York" })
    : new Date().toLocaleString("en-US", { timeZone: "America/New_York" });

  // Header
  lines.push("<b>NEXUS OPTIMIZATION LAB REPORT</b>");
  lines.push(`<i>${ts} ET</i>`);
  lines.push("");

  // -------------------------------------------------------------------------
  // Forex Optimizations
  // -------------------------------------------------------------------------
  lines.push("<b>FOREX OPTIMIZATIONS</b>");
  const forexOpts = (report.forex_optimizations || [])
    .filter((o) => o.improvement_score > 0)
    .sort((a, b) => b.improvement_score - a.improvement_score)
    .slice(0, 3);

  if (forexOpts.length === 0) {
    lines.push("  No forex optimizations available.");
  } else {
    for (const opt of forexOpts) {
      lines.push(
        `  Strategy: <code>${escapeHtml(opt.strategy_id || "unknown")}</code>  ` +
          `Score: <b>${opt.improvement_score}</b>/100`
      );
      if (opt.avg_rr != null) {
        lines.push(`    Avg RR: ${opt.avg_rr.toFixed(2)}`);
      }
      if (opt.optimal_rr != null) {
        lines.push(`    Optimal RR: ${opt.optimal_rr.toFixed(1)}`);
      }
      if (opt.suggested_sl_pct != null) {
        lines.push(`    Suggested SL: ${opt.suggested_sl_pct.toFixed(3)}%`);
      }
      if (opt.suggested_tp_pct != null) {
        lines.push(`    Suggested TP: ${opt.suggested_tp_pct.toFixed(3)}%`);
      }
      if (opt.notes) {
        lines.push(`    Note: ${escapeHtml(truncate(opt.notes, 120))}`);
      }
      lines.push("");
    }
  }

  // -------------------------------------------------------------------------
  // Options Optimizations
  // -------------------------------------------------------------------------
  lines.push("<b>OPTIONS OPTIMIZATIONS</b>");
  const optionsOpts = (report.options_optimizations || [])
    .filter((o) => o.improvement_score > 0)
    .sort((a, b) => b.improvement_score - a.improvement_score)
    .slice(0, 3);

  if (optionsOpts.length === 0) {
    lines.push("  No options optimizations available.");
  } else {
    for (const opt of optionsOpts) {
      lines.push(
        `  Type: <code>${escapeHtml(opt.strategy_type || "unknown")}</code>  ` +
          `Score: <b>${opt.improvement_score}</b>/100`
      );
      if (opt.parameter_name) {
        const orig =
          opt.original_value != null ? opt.original_value.toFixed(4) : "n/a";
        const sugg =
          opt.suggested_value != null
            ? opt.suggested_value.toFixed(4)
            : "n/a";
        lines.push(`    ${escapeHtml(opt.parameter_name)}: ${orig} → ${sugg}`);
      }
      if (opt.notes) {
        lines.push(`    Note: ${escapeHtml(truncate(opt.notes, 120))}`);
      }
      lines.push("");
    }
  }

  // -------------------------------------------------------------------------
  // Threshold Recommendations
  // -------------------------------------------------------------------------
  lines.push("<b>THRESHOLD RECOMMENDATIONS</b>");
  const risk = report.threshold_optimizations?.risk;
  const confThresh = report.threshold_optimizations?.confidence;

  if (risk) {
    const riskChanged =
      risk.suggested_approval_threshold !== risk.current_approval_threshold;
    lines.push(
      `  Risk approval: ${risk.current_approval_threshold} → ` +
        `<b>${risk.suggested_approval_threshold}</b>` +
        (riskChanged ? " [change suggested]" : " [no change]")
    );
    lines.push(
      `  Risk review: ${risk.current_review_threshold} → ` +
        `<b>${risk.suggested_review_threshold}</b>`
    );
    if (risk.improvement_note) {
      lines.push(`  ${escapeHtml(truncate(risk.improvement_note, 150))}`);
    }
  } else {
    lines.push("  No risk threshold data available.");
  }
  lines.push("");

  if (confThresh) {
    const confChanged =
      Math.abs(
        confThresh.suggested_min_confidence - confThresh.current_min_confidence
      ) > 0.02;
    lines.push(
      `  Min confidence: ${confThresh.current_min_confidence.toFixed(2)} → ` +
        `<b>${confThresh.suggested_min_confidence.toFixed(2)}</b>` +
        (confChanged ? " [change suggested]" : " [no change]")
    );
    if (confThresh.improvement_note) {
      lines.push(`  ${escapeHtml(truncate(confThresh.improvement_note, 150))}`);
    }
  }

  lines.push("");

  // -------------------------------------------------------------------------
  // Confidence Calibration Status
  // -------------------------------------------------------------------------
  lines.push("<b>CONFIDENCE CALIBRATION</b>");
  const calibration = report.confidence_optimizations?.calibration;

  if (calibration) {
    const qualityEmoji = {
      excellent: "EXCELLENT",
      good: "GOOD",
      fair: "FAIR",
      poor: "POOR",
    };
    lines.push(
      `  Quality: <b>${qualityEmoji[calibration.calibration_quality] || calibration.calibration_quality.toUpperCase()}</b>` +
        (calibration.max_gap != null
          ? ` (max gap: ${(calibration.max_gap * 100).toFixed(1)}%)`
          : "")
    );
    if (calibration.overconfident_bands?.length) {
      lines.push(`  Overconfident bands: ${calibration.overconfident_bands.length}`);
    }
    if (calibration.underconfident_bands?.length) {
      lines.push(
        `  Underconfident bands: ${calibration.underconfident_bands.length}`
      );
    }
    if (calibration.recommendation) {
      lines.push(`  ${escapeHtml(truncate(calibration.recommendation, 150))}`);
    }
  } else {
    lines.push("  No calibration data available.");
  }

  // Calibration recommendations
  const calibRecs = report.confidence_optimizations?.recommendations || [];
  if (calibRecs.length > 0 && calibRecs[0] !== "No calibration data available.") {
    lines.push("");
    lines.push("  Top recommendation:");
    lines.push(`  ${escapeHtml(truncate(calibRecs[0], 200))}`);
  }

  lines.push("");

  // -------------------------------------------------------------------------
  // Footer
  // -------------------------------------------------------------------------
  lines.push(
    "<b>NO AUTO CHANGES — all suggestions require human review before implementation.</b>"
  );
  lines.push("<i>Nexus Optimization Lab — Research Only</i>");

  return lines.join("\n");
}

// ---------------------------------------------------------------------------
// Telegram API
// ---------------------------------------------------------------------------
async function sendTelegramMessage(text, parseMode = "HTML") {
  const payload = {
    chat_id: CHAT_ID,
    text,
    parse_mode: parseMode,
    disable_web_page_preview: true,
  };

  const res = await fetch(`${TELEGRAM_API}/sendMessage`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  const data = await res.json();

  if (!data.ok) {
    // If message is too long, split it
    if (data.error_code === 400 && data.description?.includes("MESSAGE_TOO_LONG")) {
      console.warn("[telegram_optimizer_alert] Message too long — splitting...");
      const mid = Math.floor(text.length / 2);
      const splitIdx = text.lastIndexOf("\n", mid);
      const part1 = text.slice(0, splitIdx);
      const part2 = text.slice(splitIdx);
      await sendTelegramMessage(part1, parseMode);
      return sendTelegramMessage(part2, parseMode);
    }
    console.error(
      "[telegram_optimizer_alert] Telegram API error:",
      JSON.stringify(data)
    );
    throw new Error(`Telegram send failed: ${data.description}`);
  }

  console.log("[telegram_optimizer_alert] Message sent successfully.");
  return data;
}

// ---------------------------------------------------------------------------
// Utilities
// ---------------------------------------------------------------------------
function escapeHtml(text) {
  if (typeof text !== "string") return String(text ?? "");
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function truncate(text, maxLen) {
  if (!text || text.length <= maxLen) return text;
  return text.slice(0, maxLen - 3) + "...";
}
