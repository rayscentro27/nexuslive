import "dotenv/config";
import { runCometResearchTask } from "./comet_researcher.js";

// ── SAFETY GUARD ──────────────────────────────────────────────────────────────
// RESEARCH ONLY. No trading, no broker connections.
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Run a business-opportunities Comet research task for a website source.
 *
 * Extraction goals focus on:
 *   - Emerging business models (SaaS, agency, automation)
 *   - Revenue ranges, time to profitability
 *   - Bootstrapped founder case studies
 *   - Client acquisition channels
 *   - Automation and AI leverage opportunities
 *
 * @param {Object} source - { name, url, topic }
 * @param {string} trace_id
 * @returns {Promise<Object>} CometResult
 */
export async function runBusinessResearch(source, trace_id) {
  const extraction_goal =
    "Find trending business opportunities suitable for solo founders or small teams. " +
    "Extract: business model descriptions, revenue ranges (monthly/annual), time to " +
    "first revenue, time to profitability, startup costs, required skills, client " +
    "acquisition strategies, and real founder case studies or testimonials. " +
    "Prioritize AI automation, SaaS, done-for-you services, and info-product businesses. " +
    "Note any opportunities involving recurring revenue or passive income components.";

  return runCometResearchTask({
    topic: "business_opportunities",
    source_name: source.name,
    source_url: source.url,
    extraction_goal,
    trace_id,
  });
}
