// -- Autonomous Opportunity Brief Generator ----------------------------------
// Produces concise opportunity briefs and optional Telegram notifications.
// -----------------------------------------------------------------------------

const TELEGRAM_BOT_TOKEN = process.env.TELEGRAM_BOT_TOKEN;
const TELEGRAM_CHAT_ID = process.env.TELEGRAM_CHAT_ID;

function summarizeBy(list, key) {
  const map = new Map();
  for (const row of list) {
    const bucket = row[key] ?? "unknown";
    map.set(bucket, (map.get(bucket) ?? 0) + 1);
  }
  return [...map.entries()]
    .sort((a, b) => b[1] - a[1])
    .map(([name, count]) => ({ name, count }));
}

export function generateOpportunityBrief(opportunities, { job_type = "opportunity_scan", top_n = 8 } = {}) {
  const top = opportunities.slice(0, top_n);
  const byType = summarizeBy(top, "opportunity_type");
  const byOwner = summarizeBy(top, "recommended_owner");

  const summaryLine = top.length
    ? `${top.length} prioritized opportunities generated from multi-table Nexus Brain signals.`
    : "No opportunities met the active threshold.";

  return {
    title: `Autonomous Opportunity Brief - ${new Date().toISOString().slice(0, 10)}`,
    job_type,
    summary: summaryLine,
    top_claims: top.slice(0, 5).map((o) => o.evidence_summary),
    recent_insights: top.slice(0, 5).map((o) => `${o.opportunity_type}: ${o.title}`),
    opportunities: top,
    opportunities_by_type: byType,
    opportunities_by_owner: byOwner,
    risk_warnings: top
      .filter((o) => o.urgency === "high")
      .slice(0, 3)
      .map((o) => `High-urgency item: ${o.title}`),
    generated_at: new Date().toISOString(),
  };
}

export function formatBriefForLog(brief) {
  const lines = [];
  lines.push("\n+- AUTONOMOUS OPPORTUNITY BRIEF -----------------------------");
  lines.push(`| Job Type: ${brief.job_type}`);
  lines.push(`| Summary : ${brief.summary}`);

  if (brief.opportunities_by_type?.length) {
    lines.push("+- By Type:");
    for (const t of brief.opportunities_by_type.slice(0, 6)) {
      lines.push(`|   - ${t.name}: ${t.count}`);
    }
  }

  if (brief.opportunities?.length) {
    lines.push("+- Top Opportunities:");
    for (const o of brief.opportunities.slice(0, 5)) {
      lines.push(`|   [${o.score}] ${o.title} (${o.opportunity_type} | ${o.recommended_owner})`);
    }
  }

  if (brief.risk_warnings?.length) {
    lines.push("+- Risk Warnings:");
    for (const warning of brief.risk_warnings) {
      lines.push(`|   ! ${warning}`);
    }
  }

  lines.push("+------------------------------------------------------------");
  return lines.join("\n");
}

function escMd(text) {
  return String(text ?? "").replace(/[_*\[\]()~`>#+=|{}.!-]/g, "\\$&");
}

export function formatBriefForTelegram(brief) {
  const lines = [];
  lines.push("NEXUS *Autonomous Opportunity Brief*");
  lines.push(`Job: \`${escMd(brief.job_type)}\``);
  lines.push(escMd(brief.summary));
  lines.push("");

  for (const o of (brief.opportunities ?? []).slice(0, 4)) {
    lines.push(`- *${escMd(o.title)}*`);
    lines.push(`  ${escMd(o.opportunity_type)} | ${escMd(o.niche)} | score ${o.score}`);
  }

  return lines.join("\n");
}

export async function sendOpportunityBriefAlert(brief) {
  if (!TELEGRAM_BOT_TOKEN || !TELEGRAM_CHAT_ID) {
    return false;
  }
  if ((process.env.TELEGRAM_AUTO_REPORTS_ENABLED || "false") !== "true") {
    console.log("telegram_policy denied=true reason=manual_only_default");
    return false;
  }

  const payload = {
    chat_id: TELEGRAM_CHAT_ID,
    text: formatBriefForTelegram(brief),
    parse_mode: "MarkdownV2",
    disable_web_page_preview: true,
  };

  const res = await fetch(`https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  return res.ok;
}
