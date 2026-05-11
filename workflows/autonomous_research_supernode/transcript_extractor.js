// ── Transcript extractor — thin adapter over Phase 7 implementation ───────────
// Imports from the proven research_ingestion module and normalises the payload
// field name from `transcript_text` → `content_text` for supernode consistency.
// ─────────────────────────────────────────────────────────────────────────────

import {
  extractFromYoutube as _extractFromYoutube,
  loadDropIns as _loadDropIns,
} from "../research_ingestion/transcript_extractor.js";

/**
 * Normalise a Phase 7 transcript payload → supernode content payload.
 * Adds `content_text` alias, keeps all original fields.
 */
function normalize(t) {
  return {
    ...t,
    content_text: t.transcript_text ?? t.content_text ?? "",
    source_type: t.source_type ?? "youtube_channel",
  };
}

/**
 * Extract transcripts from a YouTube channel or video source.
 * @param {Object} source - { url, name, topic, max_videos? }
 * @returns {Promise<Array>} normalized supernode payloads
 */
export async function extractFromYoutube(source) {
  const results = await _extractFromYoutube(source);
  return results.map(normalize);
}

/**
 * Load drop-in transcript files from the drop_in/ folder in research_ingestion.
 * @param {string|null} topicFilter
 * @returns {Array} normalized supernode payloads
 */
export function loadDropIns(topicFilter = null) {
  const results = _loadDropIns(topicFilter);
  return results.map(normalize);
}
