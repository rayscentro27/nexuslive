import "dotenv/config";
import { readFileSync, existsSync, readdirSync } from "fs";
import path from "path";
import { randomUUID } from "crypto";

// ── SAFETY GUARD ──────────────────────────────────────────────────────────────
// RESEARCH ONLY. No trading, no broker connections.
// ─────────────────────────────────────────────────────────────────────────────

const MANUAL_DIR = "./manual_sources";

/**
 * Load manual research from a structured JSON file.
 * Format: { manual_sources: [ { topic, subtheme, title, content_text, source_name, ... } ] }
 *
 * @param {string} filePath
 * @param {string|null} topicFilter
 * @returns {Array} normalized supernode payloads
 */
export function loadManualJson(filePath, topicFilter = null) {
  if (!existsSync(filePath)) {
    console.warn(`[manual-loader] File not found: ${filePath}`);
    return [];
  }

  let parsed;
  try {
    parsed = JSON.parse(readFileSync(filePath, "utf8"));
  } catch (err) {
    console.warn(`[manual-loader] Parse error in ${filePath}: ${err.message}`);
    return [];
  }

  const sources = parsed.manual_sources ?? parsed.sources ?? [];
  const results = [];

  for (const s of sources) {
    if (topicFilter && s.topic !== topicFilter) continue;

    const text = s.content_text ?? s.transcript_text ?? s.content ?? "";
    if (text.trim().length < 50) {
      console.warn(`[manual-loader] Skipping "${s.title}" — content too short.`);
      continue;
    }

    results.push({
      source_name: s.source_name ?? s.title ?? "Manual Source",
      source_type: s.source_type ?? "manual",
      source_url: s.source_url ?? null,
      topic: s.topic ?? "general_business_intelligence",
      subtheme: s.subtheme ?? null,
      title: s.title ?? "Untitled",
      content_text: text,
      published_at: s.published_at ?? new Date().toISOString().slice(0, 10),
      trace_id: s.trace_id ?? randomUUID(),
    });
  }

  console.log(`[manual-loader] Loaded ${results.length} manual source(s) from ${filePath}.`);
  return results;
}

/**
 * Load all text/md/json files from the manual_sources/ folder.
 * Text/md files: named with topic prefix (credit_repair_notes.txt).
 * JSON files: must follow the manual_sources format above.
 *
 * @param {string|null} topicFilter
 * @returns {Array} normalized supernode payloads
 */
export function loadManualFolder(topicFilter = null) {
  if (!existsSync(MANUAL_DIR)) {
    console.log(`[manual-loader] No manual_sources/ folder found — skipping folder scan.`);
    return [];
  }

  const TOPIC_IDS = [
    "trading", "credit_repair", "grant_research",
    "business_opportunities", "crm_automation", "general_business_intelligence",
  ];

  const files = readdirSync(MANUAL_DIR).filter(f =>
    f.endsWith(".txt") || f.endsWith(".md") || f.endsWith(".json")
  );

  if (!files.length) {
    console.log("[manual-loader] No files found in manual_sources/.");
    return [];
  }

  const results = [];

  for (const file of files) {
    const filePath = path.join(MANUAL_DIR, file);

    // JSON files — delegate to loadManualJson
    if (file.endsWith(".json")) {
      results.push(...loadManualJson(filePath, topicFilter));
      continue;
    }

    // Text/markdown files
    const content_text = readFileSync(filePath, "utf8").trim();
    if (content_text.length < 50) continue;

    const topic = TOPIC_IDS.find(t => file.startsWith(t)) ?? "general_business_intelligence";
    if (topicFilter && topic !== topicFilter) continue;

    const title = file.replace(/\.[^.]+$/, "").replace(/_/g, " ");

    results.push({
      source_name: file,
      source_type: "manual",
      source_url: filePath,
      topic,
      subtheme: null,
      title,
      content_text,
      published_at: new Date().toISOString().slice(0, 10),
      trace_id: randomUUID(),
    });

    console.log(`[manual-loader] Loaded: "${title}" (topic=${topic})`);
  }

  return results;
}
