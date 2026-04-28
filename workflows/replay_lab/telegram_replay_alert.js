import "dotenv/config";

const TELEGRAM_BOT_TOKEN = process.env.TELEGRAM_BOT_TOKEN;
const TELEGRAM_CHAT_ID = process.env.TELEGRAM_CHAT_ID;

/**
 * Sends an HTML-formatted text message via Telegram Bot API.
 *
 * @param {string} text  HTML-formatted message
 * @returns {Promise<void>}
 */
async function sendTelegramMessage(text) {
  if (!TELEGRAM_BOT_TOKEN || !TELEGRAM_CHAT_ID) {
    console.warn("[telegram] TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set — skipping send.");
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
    const err = await res.text();
    throw new Error(`sendTelegramMessage: API error: ${err}`);
  }
}

/**
 * Sends a structured Replay Lab Report to Telegram.
 *
 * @param {Object}  stats        - { total_runs, wins, losses, breakevens, avg_pnl_r }
 * @param {Array}   scorecards   - [{ strategy_id, replay_win_rate, replay_avg_pnl_r, replay_count }]
 * @param {Array}   calibration  - [{ confidence_band, actual_win_rate, expected_win_rate, calibration_gap }]
 * @returns {Promise<void>}
 */
export async function sendReplaySummary(stats, scorecards = [], calibration = []) {
  const winRate =
    stats.total_runs > 0
      ? ((stats.wins / stats.total_runs) * 100).toFixed(1)
      : "0.0";

  const lines = [
    "📊 <b>NEXUS REPLAY LAB REPORT</b>",
    "",
    "<b>Overall Stats</b>",
    `• Total Runs: <b>${stats.total_runs}</b>`,
    `• Win Rate: <b>${winRate}%</b> (${stats.wins}W / ${stats.losses}L / ${stats.breakevens}BE)`,
    `• Avg PnL(R): <b>${stats.avg_pnl_r}</b>`,
  ];

  // Top 3 strategies by win rate
  if (scorecards.length > 0) {
    lines.push("", "<b>Top Strategies</b>");
    const top3 = [...scorecards]
      .sort((a, b) => b.replay_win_rate - a.replay_win_rate)
      .slice(0, 3);
    for (const sc of top3) {
      const winPct = (sc.replay_win_rate * 100).toFixed(1);
      const pnlR =
        sc.replay_avg_pnl_r != null ? sc.replay_avg_pnl_r.toFixed(3) : "N/A";
      lines.push(
        `• <code>${sc.strategy_id}</code>: ${winPct}% win, R=${pnlR} (n=${sc.replay_count})`
      );
    }
  }

  // Calibration — largest gaps
  if (calibration.length > 0) {
    const significant = calibration
      .filter((b) => Math.abs(b.calibration_gap) > 0.05)
      .sort((a, b) => Math.abs(b.calibration_gap) - Math.abs(a.calibration_gap))
      .slice(0, 3);

    if (significant.length > 0) {
      lines.push("", "<b>Calibration Gaps</b>");
      for (const band of significant) {
        const dir = band.calibration_gap < 0 ? "overconfident ⚠️" : "underconfident";
        const expectedPct = (band.expected_win_rate * 100).toFixed(0);
        const actualPct = (band.actual_win_rate * 100).toFixed(0);
        lines.push(
          `• Band ${band.confidence_band}: ${dir} (exp ${expectedPct}%, actual ${actualPct}%)`
        );
      }
    } else {
      lines.push("", "✅ <b>Calibration:</b> AI is well-calibrated across all bands.");
    }
  }

  lines.push("", "<i>Research only. No live trades.</i>");

  await sendTelegramMessage(lines.join("\n"));
}

/**
 * Sends a plain-text system alert to Telegram.
 *
 * @param {string} text
 * @returns {Promise<void>}
 */
export async function sendSystemAlert(text) {
  await sendTelegramMessage(`⚙️ <b>NEXUS REPLAY LAB</b>\n\n${text}`);
}
