import "dotenv/config";

/**
 * Builds context for a replay run.
 * historicalPrices is null — no live price feed is used.
 * Simulation uses entry/SL/TP from the proposal directly (static_rr mode).
 *
 * @param {Object} proposal
 * @returns {Promise<Object>}
 */
export async function buildReplayContext(proposal) {
  return {
    proposal,
    historicalPrices: null,
    scenarioNote: "Simulated using entry/SL/TP from proposal. No live price data.",
    simulationMode: "static_rr",
  };
}
