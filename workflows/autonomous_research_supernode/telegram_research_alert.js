import "dotenv/config";

// ── SAFETY GUARD ──────────────────────────────────────────────────────────────
// RESEARCH ONLY. No trading, no broker connections.
// ─────────────────────────────────────────────────────────────────────────────

const TELEGRAM_BOT_TOKEN = process.env.TELEGRAM_BOT_TOKEN;
const TELEGRAM_CHAT_ID = process.env.TELEGRAM_CHAT_ID;

/**
 * Send a Telegram message via the Bot API.
 * @param {string} text - message text (Markdown)
 * @returns {Promise<boolean>} true if sent successfully
 */
async function sendTelegramMessage(text) {
  if (!TELEGRAM_BOT_TOKEN || !TELEGRAM_CHAT_ID) {
    console.warn("[telegram-research-alert] Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID — skipping.");
    return false;
  }

  try {
    const res = await fetch(
      `https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          chat_id: TELEGRAM_CHAT_ID,
          text,
          parse_mode: "Markdown",
          disable_web_page_preview: true,
        }),
      }
    );

    if (!res.ok) {
      const body = await res.text();
      console.warn(`[telegram-research-alert] Send failed (${res.status}): ${body.slice(0, 200)}`);
      return false;
    }

    return true;
  } catch (err) {
    console.warn(`[telegram-research-alert] Network error: ${err.message}`);
    return false;
  }
}

/**
 * Lane labels for display.
 */
const LANE_LABELS = {
  transcript: "📺 YouTube",
  manual: "📄 Manual",
  browser: "🌐 Browser",
};

/**
 * Topic emojis for display.
 */
const TOPIC_EMOJIS = {
  grant_research: "🏛️",
  credit_repair: "💳",
  business_opportunities: "🚀",
  crm_automation: "⚙️",
  trading: "📈",
  general_business_intelligence: "🧠",
};

/**
 * Send a per-source research completion alert.
 *
 * @param {Object} brief - ResearchBrief object
 * @param {string[]} nextActions - generated next actions
 * @returns {Promise<boolean>}
 */
export async function sendResearchAlert(brief, nextActions = []) {
  const laneLabel = LANE_LABELS[brief.lane] ?? brief.lane;
  const topicEmoji = TOPIC_EMOJIS[brief.topic] ?? "🔬";
  const confPct = ((brief.confidence ?? 0) * 100).toFixed(0);

  const lines = [
    `${topicEmoji} *Nexus Research* | ${laneLabel}`,
    ``,
    `*${escapeMarkdown(brief.title)}*`,
    `_${escapeMarkdown(brief.source_name)}_`,
    ``,
    `📊 Topic: \`${brief.topic}\` | Conf: ${confPct}%`,
    ``,
    `*Summary:*`,
    escapeMarkdown(brief.summary ?? ""),
  ];

  if (brief.key_findings?.length) {
    lines.push(``, `*Key Findings:*`);
    brief.key_findings.slice(0, 3).forEach((f) => {
      lines.push(`• ${escapeMarkdown(f)}`);
    });
  }

  if (nextActions.length) {
    lines.push(``, `*Next Actions:*`);
    nextActions.slice(0, 3).forEach((a, i) => {
      lines.push(`${i + 1}\\. ${escapeMarkdown(a)}`);
    });
  }

  if (brief.risk_warnings?.length) {
    lines.push(``, `⚠️ *Risks:* ${escapeMarkdown(brief.risk_warnings[0])}`);
  }

  const text = lines.join("\n");
  const sent = await sendTelegramMessage(text);
  if (sent) {
    console.log(`[telegram-research-alert] Alert sent for: "${brief.title}"`);
  }
  return sent;
}

/**
 * Send a run-complete summary alert after all sources are processed.
 *
 * @param {Object} summary - { topic, totalSources, successCount, failCount, lanes, elapsedMs }
 * @returns {Promise<boolean>}
 */
export async function sendRunSummaryAlert(summary) {
  const {
    topic,
    totalSources = 0,
    successCount = 0,
    failCount = 0,
    lanes = {},
    elapsedMs = 0,
  } = summary;

  const topicEmoji = TOPIC_EMOJIS[topic] ?? "🔬";
  const elapsedSec = (elapsedMs / 1000).toFixed(1);

  const laneBreakdown = Object.entries(lanes)
    .map(([lane, count]) => `${LANE_LABELS[lane] ?? lane}: ${count}`)
    .join(" | ");

  const lines = [
    `${topicEmoji} *Nexus Research Run Complete*`,
    ``,
    `📊 Topic: \`${topic ?? "all"}\``,
    `✅ Success: ${successCount} / ${totalSources}`,
    failCount > 0 ? `❌ Failed: ${failCount}` : null,
    laneBreakdown ? `🔀 Lanes: ${laneBreakdown}` : null,
    `⏱ Elapsed: ${elapsedSec}s`,
    ``,
    `_Research artifacts saved to Nexus Brain (Supabase)_`,
  ].filter(Boolean);

  const text = lines.join("\n");
  const sent = await sendTelegramMessage(text);
  if (sent) {
    console.log(`[telegram-research-alert] Run summary alert sent.`);
  }
  return sent;
}

/**
 * Escape special Markdown characters for Telegram MarkdownV2.
 * Using regular Markdown mode so only minimal escaping needed.
 */
function escapeMarkdown(text) {
  if (!text) return "";
  return String(text)
    .replace(/\*/g, "\\*")
    .replace(/_/g, "\\_")
    .replace(/`/g, "\\`")
    .replace(/\[/g, "\\[");
}
