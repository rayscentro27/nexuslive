import "dotenv/config";
import { runCometResearchTask } from "./comet_researcher.js";

// ── SAFETY GUARD ──────────────────────────────────────────────────────────────
// RESEARCH ONLY. No trading, no broker connections.
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Run a credit-repair / consumer-rights Comet research task for a website source.
 *
 * Extraction goals focus on:
 *   - CFPB policy updates, FCRA changes
 *   - Credit dispute procedures and consumer rights
 *   - Medical debt, collections, and tradeline rules
 *   - New regulatory guidance and enforcement actions
 *   - Practical dispute letter tactics and timelines
 *
 * @param {Object} source - { name, url, topic }
 * @param {string} trace_id
 * @returns {Promise<Object>} CometResult
 */
export async function runCreditPolicyResearch(source, trace_id) {
  const extraction_goal =
    "Find current credit repair policies, consumer rights updates, and FCRA/CFPB " +
    "regulatory guidance. Extract: recent policy changes (especially medical debt, " +
    "collections, dispute rights), effective dates, how changes affect dispute letters, " +
    "any new consumer protections added, enforcement actions taken against bureaus or " +
    "creditors, and practical steps consumers can take. Note anything changed in the " +
    "last 6 months. Include relevant statute citations (FCRA, FDCPA, ECOA) where found.";

  return runCometResearchTask({
    topic: "credit_repair",
    source_name: source.name,
    source_url: source.url,
    extraction_goal,
    trace_id,
  });
}
