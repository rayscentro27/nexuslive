import "dotenv/config";
import { shouldSendTelegram } from "../lib/telegram_spam_guard.js";

// ── SAFETY GUARD ──────────────────────────────────────────────────────────────
// RESEARCH ONLY. No trading, no broker connections. Notification only.
// ─────────────────────────────────────────────────────────────────────────────

const TELEGRAM_BOT_TOKEN = process.env.TELEGRAM_BOT_TOKEN;
const TELEGRAM_CHAT_ID = process.env.TELEGRAM_CHAT_ID;

/**
 * Send a Nexus Brain ingestion summary alert to Telegram.
 *
 * @param {Array<{transcript, classification, extracted}>} results
 */
export async function sendIngestionAlert(results) {
  if ((process.env.TELEGRAM_RESEARCH_ALERTS_ENABLED || "false") !== "true") {
    console.log("[telegram-ingestion] TELEGRAM_RESEARCH_ALERTS_ENABLED=false — suppressed.");
    return;
  }
  if (!TELEGRAM_BOT_TOKEN || !TELEGRAM_CHAT_ID) {
    console.warn("[telegram-ingestion] Missing credentials — skipping alert.");
    return;
  }

  if (!results || results.length === 0) {
    console.log("[telegram-ingestion] No results to report.");
    return;
  }

  // Build summary lines
  const lines = ["NEXUS BRAIN INGESTION UPDATE", ""];

  // Show up to 3 individual transcript summaries
  for (const { transcript, classification, extracted } of results.slice(0, 3)) {
    const claims = extracted.claims?.length ?? 0;
    const opps = extracted.opportunity_notes?.length ?? 0;
    const warns = extracted.risk_warnings?.length ?? 0;
    const actions = extracted.action_items?.length ?? 0;

    lines.push(`Topic: ${classification.topic}`);
    lines.push(`Source: ${transcript.source_name}`);
    lines.push(`Title: ${transcript.title.slice(0, 55)}`);
    lines.push(`Claims: ${claims} | Opps: ${opps} | Warns: ${warns} | Actions: ${actions}`);
    lines.push("");
  }

  // Overflow notice
  if (results.length > 3) {
    lines.push(`+${results.length - 3} more transcript(s) processed.`);
    lines.push("");
  }

  // Batch totals
  const totalClaims = results.reduce((n, r) => n + (r.extracted.claims?.length ?? 0), 0);
  const topics = [...new Set(results.map(r => r.classification.topic))].join(", ");
  lines.push(`Total: ${results.length} transcript(s) | ${totalClaims} claim(s)`);
  lines.push(`Domains: ${topics}`);

  const text = lines.join("\n").slice(0, 1000);
  const gate = shouldSendTelegram("research_ingestion_summary", text);
  if (!gate.ok) {
    console.log(`[telegram-ingestion] Suppressed: ${gate.reason}`);
    return;
  }

  try {
    const res = await fetch(
      `https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ chat_id: TELEGRAM_CHAT_ID, text }),
      }
    );

    if (!res.ok) {
      const body = await res.text();
      console.warn(`[telegram-ingestion] Send failed (${res.status}): ${body.slice(0, 80)}`);
      return;
    }

    console.log("[telegram-ingestion] Ingestion alert sent.");

  } catch (err) {
    console.warn(`[telegram-ingestion] Error: ${err.message}`);
  }
}
