import "dotenv/config";
import { runCometResearchTask } from "./comet_researcher.js";

// ── SAFETY GUARD ──────────────────────────────────────────────────────────────
// RESEARCH ONLY. No trading, no broker connections.
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Run a trading-domain Comet research task for a website source.
 *
 * Extraction goals focus on:
 *   - Market structure, volatility regimes, session patterns
 *   - Options flow, earnings setups, forex seasonality
 *   - Risk management frameworks and position sizing
 *   - Strategy education from regulated financial sources
 *
 * @param {Object} source - { name, url, topic }
 * @param {string} trace_id
 * @returns {Promise<Object>} CometResult
 */
export async function runTradingResearch(source, trace_id) {
  const extraction_goal =
    "Find trading strategies, market analysis frameworks, and risk management " +
    "techniques covered on this site. Extract: strategy names and descriptions, " +
    "market conditions they work in, entry/exit criteria, position sizing guidance, " +
    "risk-to-reward targets, relevant instruments (forex, options, equities), " +
    "and any educational content on volatility, session timing, or options flow. " +
    "Note any backtested results, statistics, or performance benchmarks cited. " +
    "Focus on educational content only — no signals, no recommendations.";

  return runCometResearchTask({
    topic: "trading",
    source_name: source.name,
    source_url: source.url,
    extraction_goal,
    trace_id,
  });
}
