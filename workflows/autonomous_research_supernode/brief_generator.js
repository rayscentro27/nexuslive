import "dotenv/config";
import { randomUUID } from "crypto";
import { isTransientSupabaseError, supabaseInsert } from "./supabase_rest.js";

// ── SAFETY GUARD ──────────────────────────────────────────────────────────────
// RESEARCH ONLY. No trading, no broker connections.
// ─────────────────────────────────────────────────────────────────────────────

const SUPABASE_URL = process.env.SUPABASE_URL;
const SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;

/**
 * @typedef {Object} ResearchBrief
 * @property {string} topic
 * @property {string} lane - "transcript" | "manual" | "browser"
 * @property {string} title
 * @property {string} summary - 2-4 sentence executive summary
 * @property {string[]} key_findings - top 3-5 findings
 * @property {string[]} action_items - recommended next steps
 * @property {string[]} opportunity_notes - business opportunities identified
 * @property {string[]} risk_warnings - risks or caveats
 * @property {number} confidence - 0-1
 * @property {string} trace_id
 * @property {string} created_at
 */

/**
 * Generate a research brief from processed artifacts and claims.
 *
 * @param {Object} transcript - normalized source payload (has content_text, title, topic, etc.)
 * @param {Object} classification - { topic, subthemes, confidence }
 * @param {Object} extracted - { summary, claims, key_points, action_items, risk_warnings, opportunity_notes }
 * @param {string} lane - "transcript" | "manual" | "browser"
 * @returns {ResearchBrief}
 */
export function generateBrief(transcript, classification, extracted, lane = "transcript") {
  const trace_id = transcript.trace_id ?? randomUUID();

  const key_findings = [
    ...(extracted.key_points ?? []).slice(0, 3),
    ...(extracted.claims ?? [])
      .filter((c) => (c.confidence ?? 0) >= 0.65)
      .slice(0, 2)
      .map((c) => c.claim_text),
  ].filter(Boolean).slice(0, 5);

  const brief = {
    topic: classification.topic,
    subtheme: classification.subthemes?.[0] ?? null,
    lane,
    source_name: transcript.source_name,
    source_url: transcript.source_url ?? null,
    title: transcript.title,
    summary: extracted.summary ?? `Research completed for: ${transcript.title}`,
    key_findings,
    action_items: extracted.action_items ?? [],
    opportunity_notes: extracted.opportunity_notes ?? [],
    risk_warnings: extracted.risk_warnings ?? [],
    confidence: parseFloat((classification.confidence ?? 0.5).toFixed(3)),
    trace_id,
    created_at: new Date().toISOString(),
  };

  return brief;
}

/**
 * Write a research brief to the research_briefs table (if it exists).
 * Fails silently if table not found — briefs are supplemental.
 *
 * @param {ResearchBrief} brief
 * @returns {Promise<Object|null>}
 */
export async function writeBrief(brief) {
  if (!SUPABASE_URL || !SUPABASE_SERVICE_ROLE_KEY) {
    console.warn("[brief-generator] Missing Supabase credentials — skipping brief write.");
    return null;
  }

  try {
    const rows = await supabaseInsert("research_briefs", [brief]);
    const row = Array.isArray(rows) ? rows[0] : rows;
    console.log(`[brief-generator] Brief written: "${brief.title}" (topic=${brief.topic}, lane=${brief.lane})`);
    return row ?? brief;
  } catch (err) {
    if (String(err?.message ?? "").includes("42P01") || String(err?.message ?? "").includes("404")) {
      return null;
    }
    if (isTransientSupabaseError(err)) {
      console.warn(`[brief-generator] Brief write degraded: ${err.message}`);
      return null;
    }
    console.warn(`[brief-generator] Brief write error: ${err.message}`);
    return null;
  }
}

/**
 * Format a brief for console display during runs.
 * @param {ResearchBrief} brief
 */
export function formatBriefForLog(brief) {
  const lines = [
    ``,
    `┌─ RESEARCH BRIEF ─────────────────────────────────────────────`,
    `│ Topic:   ${brief.topic} | Lane: ${brief.lane}`,
    `│ Source:  ${brief.source_name}`,
    `│ Title:   ${brief.title}`,
    `│ Conf:    ${(brief.confidence * 100).toFixed(0)}%`,
    `├──────────────────────────────────────────────────────────────`,
    `│ Summary: ${brief.summary}`,
  ];

  if (brief.key_findings?.length) {
    lines.push(`├─ Key Findings:`);
    brief.key_findings.forEach((f, i) => lines.push(`│   ${i + 1}. ${f}`));
  }

  if (brief.action_items?.length) {
    lines.push(`├─ Action Items:`);
    brief.action_items.forEach((a) => lines.push(`│   → ${a}`));
  }

  if (brief.opportunity_notes?.length) {
    lines.push(`├─ Opportunities:`);
    brief.opportunity_notes.forEach((o) => lines.push(`│   ✦ ${o}`));
  }

  if (brief.risk_warnings?.length) {
    lines.push(`├─ Risks:`);
    brief.risk_warnings.forEach((r) => lines.push(`│   ⚠ ${r}`));
  }

  lines.push(`└──────────────────────────────────────────────────────────────`);
  return lines.join("\n");
}
