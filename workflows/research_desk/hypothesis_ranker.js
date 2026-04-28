import "dotenv/config";

// ── SAFETY GUARD ──────────────────────────────────────────────────────────────
// This module is RESEARCH ONLY. Re-scores and sorts hypotheses.
// No trading, no broker connections.
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Computes replay win rate for a given strategy_id from replay_results.
 * @param {string} strategyId
 * @param {Array} replayResults
 * @returns {number|null}
 */
function replayWinRate(strategyId, replayResults) {
  if (!strategyId) return null;
  const relevant = replayResults.filter((r) => r.strategy_id === strategyId);
  if (relevant.length === 0) return null;
  const wins = relevant.filter((r) => r.replay_outcome === "tp_hit").length;
  return wins / relevant.length;
}

/**
 * Finds max improvement score for a strategy in optimization data.
 * @param {string} strategyId
 * @param {Array} optimizations
 * @returns {number}
 */
function maxImprovementScore(strategyId, optimizations) {
  if (!strategyId) return 0;
  const relevant = optimizations.filter((o) => o.strategy_id === strategyId);
  if (relevant.length === 0) return 0;
  return Math.max(...relevant.map((o) => parseFloat(o.improvement_score ?? 0)));
}

/**
 * Finds max calibration gap from calibration data.
 * @param {Array} calibration
 * @returns {number}
 */
function maxCalibrationGap(calibration) {
  if (!calibration.length) return 0;
  return Math.max(...calibration.map((c) => Math.abs(parseFloat(c.calibration_gap ?? 0))));
}

/**
 * Re-scores and sorts hypotheses by priority.
 * @param {Array} hypotheses
 * @param {Object} inputs - Output from pollResearchInputs()
 * @returns {Array} Sorted hypotheses (priority_score desc)
 */
export function rankHypotheses(hypotheses, inputs) {
  const { replayResults = [], optimizations = [], calibration = [] } = inputs;

  console.log(`[ranker] Ranking ${hypotheses.length} hypotheses...`);

  const maxCalGap = maxCalibrationGap(calibration);

  const rescored = hypotheses.map((h) => {
    let boost = 0;

    // Boost hypotheses linked to low replay win rate strategies (need more attention)
    if (h.linked_strategy_id) {
      const winRate = replayWinRate(h.linked_strategy_id, replayResults);
      if (winRate !== null) {
        if (winRate < 0.4) {
          boost += 0.15; // low win rate → higher priority to investigate
        } else if (winRate > 0.7) {
          boost += 0.05; // high win rate → slight boost (confirm the edge)
        }
      }

      // Boost based on optimization improvement score
      const impScore = maxImprovementScore(h.linked_strategy_id, optimizations);
      if (impScore >= 50) boost += 0.1;
      else if (impScore >= 30) boost += 0.05;
    }

    // Boost calibration hypotheses when gaps are severe
    if (
      h.hypothesis_title.toLowerCase().includes("calibration") ||
      h.hypothesis_title.toLowerCase().includes("overestimates") ||
      h.hypothesis_title.toLowerCase().includes("underestimates")
    ) {
      if (maxCalGap > 0.35) boost += 0.12;
      else if (maxCalGap > 0.2) boost += 0.06;
    }

    // Clamp priority_score to [0, 1]
    const newPriority = Math.min(1.0, (h.priority_score ?? 0.5) + boost);

    return { ...h, priority_score: parseFloat(newPriority.toFixed(4)) };
  });

  // Sort descending by priority_score, then plausibility, then novelty
  rescored.sort((a, b) => {
    const pDiff = (b.priority_score ?? 0) - (a.priority_score ?? 0);
    if (Math.abs(pDiff) > 0.001) return pDiff;
    const plDiff = (b.plausibility_score ?? 0) - (a.plausibility_score ?? 0);
    if (Math.abs(plDiff) > 0.001) return plDiff;
    return (b.novelty_score ?? 0) - (a.novelty_score ?? 0);
  });

  console.log(
    `[ranker] Top hypothesis: "${rescored[0]?.hypothesis_title ?? "none"}" ` +
    `(priority=${rescored[0]?.priority_score ?? "N/A"})`
  );

  return rescored;
}
