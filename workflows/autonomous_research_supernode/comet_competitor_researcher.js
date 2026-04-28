import "dotenv/config";
import { runCometResearchTask } from "./comet_researcher.js";

// ── SAFETY GUARD ──────────────────────────────────────────────────────────────
// RESEARCH ONLY. No trading, no broker connections.
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Run a CRM/automation competitor Comet research task for a website source.
 *
 * Extraction goals focus on:
 *   - CRM workflow automation patterns
 *   - GoHighLevel, HubSpot, Zapier, Make.com, n8n stacks
 *   - Lead generation and nurture automation
 *   - Agency pricing models and service packages
 *   - ROI metrics and efficiency benchmarks
 *
 * @param {Object} source - { name, url, topic }
 * @param {string} trace_id
 * @returns {Promise<Object>} CometResult
 */
export async function runCompetitorResearch(source, trace_id) {
  const extraction_goal =
    "Find CRM automation workflows, agency service models, and lead generation " +
    "strategies used by top marketing and automation agencies. Extract: software stacks " +
    "(GHL, HubSpot, Zapier, n8n, Make.com), workflow templates, pricing for done-for-you " +
    "services, efficiency metrics (lead response time, conversion rates, automation rates), " +
    "client onboarding approaches, and any competitive differentiators. Note any new " +
    "AI-powered automation features or integrations announced recently.";

  return runCometResearchTask({
    topic: "crm_automation",
    source_name: source.name,
    source_url: source.url,
    extraction_goal,
    trace_id,
  });
}
