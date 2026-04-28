import "dotenv/config";
import { readFileSync, existsSync } from "fs";

// ── SAFETY GUARD ──────────────────────────────────────────────────────────────
// RESEARCH ONLY. No trading, no broker connections.
// ─────────────────────────────────────────────────────────────────────────────

const VALID_TOPICS = [
  "trading",
  "credit_repair",
  "grant_research",
  "business_opportunities",
  "crm_automation",
  "general_business_intelligence",
];

const VALID_TYPES = [
  "youtube_channel",
  "youtube_video",
  "website",
  "manual",
  "local_file",
];

// Research lanes by source type
export const LANE = {
  TRANSCRIPT: "transcript",
  MANUAL: "manual",
  BROWSER: "browser",
};

/**
 * Load and validate sources from a JSON seed file.
 */
export function loadSources(filePath) {
  if (!existsSync(filePath)) {
    console.error(`[registry] Sources file not found: ${filePath}`);
    process.exit(1);
  }

  let parsed;
  try {
    parsed = JSON.parse(readFileSync(filePath, "utf8"));
  } catch (err) {
    console.error(`[registry] Failed to parse ${filePath}: ${err.message}`);
    process.exit(1);
  }

  const sources = parsed.sources ?? [];

  // Validate and annotate each source with its research lane
  const validated = [];
  for (const s of sources) {
    if (!s.url && s.type !== "manual") {
      console.warn(`[registry] Skipping source "${s.name}" — no url.`);
      continue;
    }

    if (s.topic && !VALID_TOPICS.includes(s.topic)) {
      console.warn(`[registry] Unknown topic "${s.topic}" for "${s.name}" — using general_business_intelligence.`);
      s.topic = "general_business_intelligence";
    }

    validated.push({
      ...s,
      lane: getLane(s.type),
    });
  }

  console.log(`[registry] Loaded ${validated.length} source(s) from ${filePath}.`);
  return validated;
}

/**
 * Determine which research lane handles this source type.
 */
export function getLane(sourceType) {
  if (sourceType === "youtube_channel" || sourceType === "youtube_video") return LANE.TRANSCRIPT;
  if (sourceType === "manual" || sourceType === "local_file") return LANE.MANUAL;
  if (sourceType === "website") return LANE.BROWSER;
  return LANE.MANUAL;
}

/**
 * Filter sources by topic.
 */
export function filterByTopic(sources, topic) {
  if (!topic) return sources;
  return sources.filter(s => s.topic === topic);
}

/**
 * Filter sources by research lane.
 */
export function filterByLane(sources, lane) {
  return sources.filter(s => s.lane === lane);
}

/**
 * Apply source limit per run.
 */
export function limitSources(sources, max) {
  const limit = max ?? parseInt(process.env.MAX_RESEARCH_SOURCES ?? "10", 10);
  if (sources.length > limit) {
    console.log(`[registry] Capping to ${limit} source(s) (MAX_RESEARCH_SOURCES=${limit}).`);
    return sources.slice(0, limit);
  }
  return sources;
}
