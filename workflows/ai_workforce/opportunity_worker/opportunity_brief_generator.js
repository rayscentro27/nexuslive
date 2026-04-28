// ── Opportunity Brief Generator ───────────────────────────────────────────────
// Generates a human-readable opportunity brief and Telegram alert.
// ─────────────────────────────────────────────────────────────────────────────

const TELEGRAM_BOT_TOKEN = process.env.TELEGRAM_BOT_TOKEN;
const TELEGRAM_CHAT_ID = process.env.TELEGRAM_CHAT_ID;

const TYPE_LABELS = {
  saas: "SaaS Product",
  automation_agency: "Automation Agency",
  ai_product: "AI Product",
  content_creator: "Content / Creator",
  service_business: "Service Business",
  acquisition: "Business Acquisition",
  ecommerce: "E-Commerce",
  local_business: "Local / Main Street Business",
  other: "Business Opportunity",
};

const URGENCY_ICON = { high: "🔥", medium: "⚡", low: "💡" };

/**
 * Generate a text brief summarising top business opportunities.
 * @param {Array} opps - Scored and ranked BusinessOpportunity objects
 * @param {Object} [opts]
 * @param {number} [opts.topN=5] - Max opportunities to include
 * @returns {Object} { title, body, opps }
 */
export function generateOpportunityBrief(opps, { topN = 5 } = {}) {
  const top = opps.slice(0, topN);
  const now = new Date().toISOString().slice(0, 10);

  const lines = [];
  lines.push(`NEXUS OPPORTUNITY BRIEF — ${now}`);
  lines.push(`${top.length} business opportunit${top.length === 1 ? "y" : "ies"} surfaced\n`);

  // Group by niche for pattern recognition
  const niches = [...new Set(top.map((o) => o.niche))];
  if (niches.length < top.length) {
    lines.push(`Recurring niches: ${niches.join(", ")}\n`);
  }

  for (const [i, o] of top.entries()) {
    const urgencyIcon = URGENCY_ICON[o.urgency] ?? "•";
    const typeLabel = TYPE_LABELS[o.opportunity_type] ?? o.opportunity_type;
    lines.push(`${i + 1}. ${urgencyIcon} ${o.title}`);
    lines.push(`   Type        : ${typeLabel}`);
    lines.push(`   Niche       : ${o.niche}`);
    lines.push(`   Monetization: ${o.monetization_hint}`);
    lines.push(`   Urgency     : ${o.urgency}`);
    if (o.evidence_summary) {
      const ev = o.evidence_summary.slice(0, 120);
      lines.push(`   Evidence    : ${ev}${o.evidence_summary.length > 120 ? "…" : ""}`);
    }
    lines.push(`   Score: ${o.score}/100 | Source: ${o.source}`);
    lines.push("");
  }

  lines.push("NEXT ACTIONS");
  lines.push("  → Validate top opportunity with a 1-week landing page sprint");
  lines.push("  → Check Indie Hackers / Starter Story for comparable case studies");
  lines.push("  → Map 3 potential service packages with pricing and target client profile");
  lines.push("  → Identify recurring-revenue version of top service idea");

  const body = lines.join("\n");
  return { title: `Opportunity Brief — ${now}`, body, opps: top };
}

/**
 * Format brief for Telegram MarkdownV2.
 * @param {Object} brief - Output from generateOpportunityBrief()
 * @returns {string}
 */
export function formatOpportunityBriefForTelegram(brief) {
  const top = brief.opps.slice(0, 3);
  const lines = [];

  lines.push(`💼 *NEXUS OPPORTUNITY BRIEF*`);
  lines.push(`${brief.opps.length} opportunit${brief.opps.length === 1 ? "y" : "ies"} detected\n`);

  // Niche pattern summary
  const niches = [...new Set(brief.opps.map((o) => o.niche))];
  if (niches.length) {
    lines.push(`📊 Top niches: ${escMd(niches.slice(0, 3).join(", "))}\n`);
  }

  for (const [i, o] of top.entries()) {
    const medal = ["🥇", "🥈", "🥉"][i] ?? "•";
    const urgencyIcon = URGENCY_ICON[o.urgency] ?? "";
    const typeLabel = TYPE_LABELS[o.opportunity_type] ?? o.opportunity_type;
    lines.push(`${medal} ${urgencyIcon} *${escMd(o.title)}*`);
    lines.push(`  📂 ${escMd(typeLabel)} — ${escMd(o.niche)}`);
    lines.push(`  💰 ${escMd(o.monetization_hint)}`);
    lines.push(`  Score: ${o.score}/100`);
    lines.push("");
  }

  lines.push(`*Next:* Validate top opportunity with landing page sprint`);
  return lines.join("\n");
}

function escMd(s) {
  if (!s) return "";
  return String(s).replace(/[_*[\]()~`>#+=|{}.!-]/g, "\\$&");
}

/**
 * Send Telegram alert for the opportunity brief.
 * @param {Object} brief - Output from generateOpportunityBrief()
 * @returns {Promise<void>}
 */
export async function sendOpportunityBriefAlert(brief) {
  if (!TELEGRAM_BOT_TOKEN || !TELEGRAM_CHAT_ID) {
    console.warn("[opp-brief] Telegram not configured — skipping alert.");
    return;
  }
  try {
    const text = formatOpportunityBriefForTelegram(brief);
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
      console.warn(`[opp-brief] Telegram send failed: ${err}`);
    } else {
      console.log(`[opp-brief] Telegram alert sent (${brief.opps.length} opportunities).`);
    }
  } catch (err) {
    console.warn(`[opp-brief] Telegram error: ${err.message}`);
  }
}
