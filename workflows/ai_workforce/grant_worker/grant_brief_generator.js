// ── Grant Brief Generator ─────────────────────────────────────────────────────
// Generates a human-readable grant brief and Telegram alert from scored grants.
// ─────────────────────────────────────────────────────────────────────────────

const TELEGRAM_BOT_TOKEN = process.env.TELEGRAM_BOT_TOKEN;
const TELEGRAM_CHAT_ID = process.env.TELEGRAM_CHAT_ID;

/**
 * Generate a text brief summarising the top grant opportunities.
 * @param {Array} grants - Scored and ranked GrantOpportunity objects
 * @param {Object} [opts]
 * @param {number} [opts.topN=5] - Max grants to include in brief
 * @returns {Object} { title, body, grants }
 */
export function generateGrantBrief(grants, { topN = 5 } = {}) {
  const top = grants.slice(0, topN);
  const now = new Date().toISOString().slice(0, 10);

  const lines = [];
  lines.push(`NEXUS GRANT BRIEF — ${now}`);
  lines.push(`${top.length} grant opportunit${top.length === 1 ? "y" : "ies"} surfaced\n`);

  for (const [i, g] of top.entries()) {
    lines.push(`${i + 1}. ${g.title}`);
    if (g.program_name && g.program_name !== g.title) lines.push(`   Program : ${g.program_name}`);
    if (g.funding_amount) lines.push(`   Funding : ${g.funding_amount}`);
    if (g.geography)      lines.push(`   Geo     : ${g.geography}`);
    if (g.deadline)       lines.push(`   Deadline: ${g.deadline}`);
    if (g.target_business_type) lines.push(`   For     : ${g.target_business_type}`);
    if (g.eligibility_notes) {
      const note = g.eligibility_notes.slice(0, 120);
      lines.push(`   Eligibility: ${note}${g.eligibility_notes.length > 120 ? "…" : ""}`);
    }
    lines.push(`   Score   : ${g.score}/100 | Source: ${g.source}`);
    lines.push("");
  }

  lines.push("NEXT ACTIONS");
  lines.push("  → Review top-scored grants and confirm current eligibility");
  lines.push("  → Add near-deadline grants to calendar immediately");
  lines.push("  → Register on grants.gov and sbir.gov if not already done");
  lines.push("  → Contact Arizona Commerce Authority for AZ-specific programs");

  const body = lines.join("\n");
  return { title: `Grant Brief — ${now}`, body, grants: top };
}

/**
 * Format a brief into a Telegram Markdown message.
 * @param {Object} brief - Output from generateGrantBrief()
 * @returns {string}
 */
export function formatGrantBriefForTelegram(brief) {
  const top = brief.grants.slice(0, 3);
  const lines = [];

  lines.push(`🏦 *NEXUS GRANT BRIEF*`);
  lines.push(`${brief.grants.length} opportunit${brief.grants.length === 1 ? "y" : "ies"} detected\n`);

  for (const [i, g] of top.entries()) {
    const medal = ["🥇", "🥈", "🥉"][i] ?? "•";
    lines.push(`${medal} *${escMd(g.title)}*`);
    if (g.funding_amount) lines.push(`  💰 ${escMd(g.funding_amount)}`);
    if (g.deadline)       lines.push(`  📅 ${escMd(g.deadline)}`);
    if (g.geography)      lines.push(`  📍 ${escMd(g.geography)}`);
    lines.push(`  Score: ${g.score}/100`);
    lines.push("");
  }

  lines.push(`*Next:* Verify eligibility for top grant and check deadlines`);
  return lines.join("\n");
}

function escMd(s) {
  if (!s) return "";
  return String(s).replace(/[_*[\]()~`>#+=|{}.!-]/g, "\\$&");
}

/**
 * Send a Telegram alert for the grant brief.
 * @param {Object} brief - Output from generateGrantBrief()
 * @returns {Promise<void>}
 */
export async function sendGrantBriefAlert(brief) {
  if (!TELEGRAM_BOT_TOKEN || !TELEGRAM_CHAT_ID) {
    console.warn("[grant-brief] Telegram not configured — skipping alert.");
    return;
  }
  try {
    const text = formatGrantBriefForTelegram(brief);
    const res = await fetch(
      `https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          chat_id: TELEGRAM_CHAT_ID,
          text,
          parse_mode: "MarkdownV2",
        }),
      }
    );
    if (!res.ok) {
      const err = await res.text();
      console.warn(`[grant-brief] Telegram send failed: ${err}`);
    } else {
      console.log(`[grant-brief] Telegram alert sent (${brief.grants.length} grants).`);
    }
  } catch (err) {
    console.warn(`[grant-brief] Telegram error: ${err.message}`);
  }
}
