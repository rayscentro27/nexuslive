// ── Claim extractor — thin adapter over Phase 7 implementation ────────────────
// Supernode payloads use `content_text`; Phase 7 uses `transcript_text`.
// This adapter bridges the two before calling the proven extractor.
// ─────────────────────────────────────────────────────────────────────────────

import { extractClaims as _extractClaims } from "../research_ingestion/claim_extractor.js";

/**
 * Extract structured claims from a supernode content payload.
 * Bridges content_text → transcript_text for the Phase 7 extractor.
 *
 * @param {Object} payload - supernode payload with content_text field
 * @param {string} topic
 * @returns {Promise<Object>} { summary, claims, key_points, action_items, risk_warnings, opportunity_notes }
 */
export async function extractClaims(payload, topic) {
  const adapted = {
    ...payload,
    transcript_text: payload.content_text ?? payload.transcript_text ?? "",
  };
  return _extractClaims(adapted, topic);
}
