import "dotenv/config";
import { shouldSendTelegram } from "../lib/telegram_spam_guard.js";
import { shouldSendTelegramNotification } from "../lib/telegram_notification_policy.js";

// ── SAFETY GUARD ──────────────────────────────────────────────────────────────
// RESEARCH ONLY. No trading, no broker connections.
// ─────────────────────────────────────────────────────────────────────────────

const TELEGRAM_BOT_TOKEN = process.env.TELEGRAM_BOT_TOKEN;
const TELEGRAM_CHAT_ID = process.env.TELEGRAM_CHAT_ID;

// Respect the TELEGRAM_RESEARCH_ALERTS_ENABLED gate (default off for safety).
// Set TELEGRAM_RESEARCH_ALERTS_ENABLED=true in .env to re-enable intelligence briefs.
const RESEARCH_ALERTS_ENABLED =
  process.env.TELEGRAM_RESEARCH_ALERTS_ENABLED === "true";

/**
 * Send a Telegram message via the Bot API.
 * @param {string} text
 * @returns {Promise<boolean>}
 */
async function sendTelegramMessage(text) {
  const policy = shouldSendTelegramNotification("research_summary");
  if (!policy.ok) {
    console.log(`[telegram-brief-alert] Policy denied: ${policy.reason}`);
    return false;
  }
  if (!RESEARCH_ALERTS_ENABLED) {
    console.log("[telegram-brief-alert] TELEGRAM_RESEARCH_ALERTS_ENABLED=false — suppressed.");
    return false;
  }
  if (!TELEGRAM_BOT_TOKEN || !TELEGRAM_CHAT_ID) {
    console.warn("[telegram-brief-alert] Missing credentials — skipping.");
    return false;
  }

  const gate = shouldSendTelegram("research_supernode_brief", text);
  if (!gate.ok) {
    console.log(`[telegram-brief-alert] Suppressed: ${gate.reason}`);
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
      console.warn(`[telegram-brief-alert] Send failed (${res.status}): ${body.slice(0, 200)}`);
      return false;
    }

    return true;
  } catch (err) {
    console.warn(`[telegram-brief-alert] Network error: ${err.message}`);
    return false;
  }
}

function escapeMarkdown(text) {
  if (!text) return "";
  return String(text)
    .replace(/\*/g, "\\*")
    .replace(/_/g, "\\_")
    .replace(/`/g, "\\`")
    .replace(/\[/g, "\\[");
}

/**
 * Send a formatted intelligence brief to Telegram.
 * This is a richer, digest-style message for end-of-run topic summaries.
 *
 * @param {Object[]} briefs - array of ResearchBrief objects for a topic
 * @param {string} topic
 * @returns {Promise<boolean>}
 */
export async function sendTopicBriefAlert(briefs, topic) {
  if (!briefs?.length) return false;

  const TOPIC_EMOJIS = {
    grant_research: "🏛️",
    credit_repair: "💳",
    business_opportunities: "🚀",
    crm_automation: "⚙️",
    trading: "📈",
    general_business_intelligence: "🧠",
  };

  const topicEmoji = TOPIC_EMOJIS[topic] ?? "🔬";

  // Aggregate top findings across all briefs
  const allFindings = briefs
    .flatMap((b) => b.key_findings ?? [])
    .filter(Boolean)
    .slice(0, 5);

  const allActions = briefs
    .flatMap((b) => b.action_items ?? [])
    .filter(Boolean)
    .slice(0, 4);

  const allOpportunities = briefs
    .flatMap((b) => b.opportunity_notes ?? [])
    .filter(Boolean)
    .slice(0, 3);

  const allRisks = briefs
    .flatMap((b) => b.risk_warnings ?? [])
    .filter(Boolean)
    .slice(0, 2);

  const avgConf = briefs.reduce((sum, b) => sum + (b.confidence ?? 0), 0) / briefs.length;

  const lines = [
    `${topicEmoji} *Nexus Intelligence Brief*`,
    `📊 Topic: \`${topic}\` | Sources: ${briefs.length} | Avg Conf: ${(avgConf * 100).toFixed(0)}%`,
    ``,
  ];

  if (allFindings.length) {
    lines.push(`*Top Findings:*`);
    allFindings.forEach((f) => lines.push(`• ${escapeMarkdown(f)}`));
    lines.push(``);
  }

  if (allOpportunities.length) {
    lines.push(`*Opportunities Identified:*`);
    allOpportunities.forEach((o) => lines.push(`✦ ${escapeMarkdown(o)}`));
    lines.push(``);
  }

  if (allActions.length) {
    lines.push(`*Recommended Actions:*`);
    allActions.forEach((a, i) => lines.push(`${i + 1}. ${escapeMarkdown(a)}`));
    lines.push(``);
  }

  if (allRisks.length) {
    lines.push(`⚠️ *Risks/Caveats:*`);
    allRisks.forEach((r) => lines.push(`• ${escapeMarkdown(r)}`));
    lines.push(``);
  }

  lines.push(`_Sources: ${briefs.map((b) => b.source_name).join(", ")}_`);

  const text = lines.join("\n");
  const sent = await sendTelegramMessage(text);
  if (sent) {
    console.log(`[telegram-brief-alert] Topic brief sent for: ${topic} (${briefs.length} sources)`);
  }
  return sent;
}

/**
 * Send a single brief as a standalone Telegram message.
 * Used when a single high-value source warrants immediate notification.
 *
 * @param {Object} brief - ResearchBrief
 * @param {string[]} nextActions
 * @returns {Promise<boolean>}
 */
export async function sendSingleBriefAlert(brief, nextActions = []) {
  const TOPIC_EMOJIS = {
    grant_research: "🏛️",
    credit_repair: "💳",
    business_opportunities: "🚀",
    crm_automation: "⚙️",
    trading: "📈",
    general_business_intelligence: "🧠",
  };

  const LANE_LABELS = {
    transcript: "📺 YouTube",
    manual: "📄 Manual",
    browser: "🌐 Browser",
  };

  const topicEmoji = TOPIC_EMOJIS[brief.topic] ?? "🔬";
  const laneLabel = LANE_LABELS[brief.lane] ?? brief.lane;
  const confPct = ((brief.confidence ?? 0) * 100).toFixed(0);

  const lines = [
    `${topicEmoji} *Research Brief* | ${laneLabel}`,
    ``,
    `*${escapeMarkdown(brief.title)}*`,
    `Source: _${escapeMarkdown(brief.source_name)}_`,
    `Conf: ${confPct}% | Topic: \`${brief.topic}\``,
    ``,
    escapeMarkdown(brief.summary ?? ""),
  ];

  if (brief.key_findings?.length) {
    lines.push(``, `*Findings:*`);
    brief.key_findings.slice(0, 3).forEach((f) => lines.push(`• ${escapeMarkdown(f)}`));
  }

  if (nextActions.length) {
    lines.push(``, `*Next:*`);
    nextActions.slice(0, 3).forEach((a, i) => lines.push(`${i + 1}. ${escapeMarkdown(a)}`));
  }

  const text = lines.join("\n");
  const sent = await sendTelegramMessage(text);
  if (sent) {
    console.log(`[telegram-brief-alert] Single brief sent: "${brief.title}"`);
  }
  return sent;
}
