import "dotenv/config";
import { runCometResearchTask } from "./comet_researcher.js";

// ── SAFETY GUARD ──────────────────────────────────────────────────────────────
// RESEARCH ONLY. No trading, no broker connections.
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Run a grant-domain Comet research task for a website source.
 *
 * Extraction goals focus on:
 *   - Active grant programs, eligibility, award amounts
 *   - Application deadlines and cycles
 *   - SBIR/STTR, SBA, state, local micro-grant programs
 *   - Required documentation and application tips
 *
 * @param {Object} source - { name, url, topic }
 * @param {string} trace_id
 * @returns {Promise<Object>} CometResult
 */
export async function runGrantResearch(source, trace_id) {
  const extraction_goal =
    "Find active grant programs available to small businesses and entrepreneurs. " +
    "Extract: program names, award amounts (min/max), eligibility requirements, " +
    "application deadlines, open/closed status, application links, and any tips " +
    "for winning. Focus on federal SBIR/STTR, SBA programs, state business grants, " +
    "and local micro-grants. Note any new programs announced in the last 90 days.";

  return runCometResearchTask({
    topic: "grant_research",
    source_name: source.name,
    source_url: source.url,
    extraction_goal,
    trace_id,
  });
}
