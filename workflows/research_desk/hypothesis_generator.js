import "dotenv/config";
import { randomUUID } from "crypto";

// ── SAFETY GUARD ──────────────────────────────────────────────────────────────
// This module is RESEARCH ONLY. Generates hypotheses from research data.
// No trading, no broker connections, no live execution.
// ─────────────────────────────────────────────────────────────────────────────

const THEME_HYPOTHESIS_TEMPLATES = {
  breakout_behavior: {
    hypothesis_title: "Breakout entries show diminished follow-through in low-volume sessions",
    asset_type: "forex",
    market_type: "trending",
    hypothesis_text:
      "Research evidence suggests breakout signals may be generating false positives " +
      "during low-volume or extended consolidation periods. " +
      "A refined entry filter incorporating volume confirmation could improve breakout success rate.",
  },
  spread_sensitivity: {
    hypothesis_title: "Spread costs materially reduce net expectancy on short-timeframe strategies",
    asset_type: "forex",
    market_type: "all",
    hypothesis_text:
      "Spread sensitivity analysis indicates that strategies with tight profit targets " +
      "are disproportionately impacted by variable spreads during news events. " +
      "Widening the minimum R target or avoiding high-spread windows could restore edge.",
  },
  iv_crush: {
    hypothesis_title: "IV crush post-earnings creates reliable premium decay windows for short vol strategies",
    asset_type: "options",
    market_type: "earnings",
    hypothesis_text:
      "Multiple sources document consistent implied volatility compression following earnings announcements. " +
      "Short vega structures entered 1-3 days pre-earnings may capture crush without directional risk.",
  },
  mean_reversion: {
    hypothesis_title: "Mean reversion signals perform better in range-bound regimes than trending markets",
    asset_type: "forex",
    market_type: "ranging",
    hypothesis_text:
      "Research clustering around mean reversion themes suggests these signals carry regime dependency. " +
      "Applying a regime filter (ADX < 20) before triggering mean reversion entries may reduce false reversals.",
  },
  trend_continuation: {
    hypothesis_title: "Pullback entries on confirmed trend continuation outperform breakout entries 2:1",
    asset_type: "forex",
    market_type: "trending",
    hypothesis_text:
      "Evidence from trend continuation research supports buying pullbacks to structure " +
      "rather than chasing breakouts. Win rates and R multiples favor lower-risk entry on retests.",
  },
  covered_call_stability: {
    hypothesis_title: "Covered call overlays generate consistent premium income in low-volatility regimes",
    asset_type: "options",
    market_type: "low_vol",
    hypothesis_text:
      "Research supports covered call writing as a stable income mechanism when IV is moderate. " +
      "Optimal strike selection (OTM 0.20-0.30 delta) and weekly expiry rolling may enhance consistency.",
  },
  options_structure_weakness: {
    hypothesis_title: "Undefined-risk options structures carry tail exposure that is systematically underweighted",
    asset_type: "options",
    market_type: "all",
    hypothesis_text:
      "Research signals indicate that naked puts and short calls are more frequently involved in " +
      "outsized loss events than their win rates suggest. Defined-risk structures should be preferred.",
  },
  confidence_calibration_issue: {
    hypothesis_title: "AI confidence scores are systematically overestimated in high-confidence bands",
    asset_type: "all",
    market_type: "all",
    hypothesis_text:
      "Calibration data suggests AI analyst confidence is higher than realized win rates in upper bands. " +
      "Recalibrating confidence thresholds or applying a downward bias correction may improve signal quality.",
  },
  risk_threshold_adjustment: {
    hypothesis_title: "Current risk thresholds are calibrated for volatility regimes that may have shifted",
    asset_type: "all",
    market_type: "all",
    hypothesis_text:
      "Research indicates risk parameters (stop distances, position sizing) may need regime-sensitive adjustment. " +
      "A dynamic risk budget that scales with recent ATR or VIX would adapt to changing conditions.",
  },
  volatility_regime: {
    hypothesis_title: "Strategy performance is strongly regime-dependent and requires a vol regime classifier",
    asset_type: "all",
    market_type: "all",
    hypothesis_text:
      "Volatility regime clustering suggests a significant share of strategy variance is explained by " +
      "the current vol regime rather than strategy parameters alone. " +
      "A regime-aware routing layer could improve overall system performance.",
  },
};

function scoreFromSources(sourceCount) {
  if (sourceCount >= 5) return 0.9;
  if (sourceCount >= 3) return 0.75;
  if (sourceCount >= 2) return 0.6;
  return 0.45;
}

function buildHypothesis(override) {
  return {
    hypothesis_title: override.hypothesis_title,
    asset_type: override.asset_type ?? "all",
    market_type: override.market_type ?? "all",
    hypothesis_text: override.hypothesis_text,
    supporting_evidence: override.supporting_evidence ?? [],
    novelty_score: override.novelty_score ?? 0.5,
    plausibility_score: override.plausibility_score ?? 0.6,
    priority_score: override.priority_score ?? 0.5,
    linked_strategy_id: override.linked_strategy_id ?? null,
    status: "candidate",
    trace_id: randomUUID(),
  };
}

/**
 * Generates research hypotheses from clusters and raw inputs.
 * @param {Array} clusters - Output from clusterResearch()
 * @param {Object} inputs - Output from pollResearchInputs()
 * @returns {Array} Array of hypothesis objects
 */
export function generateHypotheses(clusters, inputs) {
  const { optimizations = [], replayResults = [], calibration = [], scorecards = [] } = inputs;

  console.log("[hypotheses] Generating hypotheses from clusters and inputs...");
  const hypotheses = [];

  // ── 1. Cluster-based hypotheses ──────────────────────────────────────────────
  for (const cluster of clusters) {
    if (cluster.source_count < 1) continue;

    const template = THEME_HYPOTHESIS_TEMPLATES[cluster.theme];
    if (!template) continue;

    const plausibility = scoreFromSources(cluster.source_count);
    const novelty = cluster.source_count === 1 ? 0.7 : cluster.source_count <= 3 ? 0.55 : 0.4;
    const priority = (plausibility + novelty + cluster.confidence) / 3;

    const evidence = [
      `Cluster "${cluster.theme}" matched ${cluster.source_count} source(s)`,
      `Key terms: ${cluster.key_terms.join(", ") || "none"}`,
      `Cluster summary: ${cluster.summary.slice(0, 120)}`,
    ];

    hypotheses.push(
      buildHypothesis({
        ...template,
        supporting_evidence: evidence,
        novelty_score: novelty,
        plausibility_score: plausibility,
        priority_score: priority,
      })
    );
  }

  // ── 2. Calibration-based hypotheses ─────────────────────────────────────────
  for (const cal of calibration) {
    const gap = parseFloat(cal.calibration_gap ?? 0);
    if (gap <= 0.2) continue;

    const direction = cal.actual_win_rate < cal.expected_win_rate ? "overestimates" : "underestimates";
    const band = cal.confidence_band ?? "unknown";

    hypotheses.push(
      buildHypothesis({
        hypothesis_title: `AI ${direction} confidence in the ${band} band`,
        asset_type: "all",
        market_type: "all",
        hypothesis_text:
          `Calibration data shows a gap of ${gap.toFixed(3)} between actual win rate ` +
          `(${cal.actual_win_rate}) and expected win rate (${cal.expected_win_rate}) ` +
          `in the "${band}" confidence band. ` +
          `The AI model ${direction} probability for signals in this range. ` +
          `Recalibrating decision thresholds for this band could improve downstream accuracy.`,
        supporting_evidence: [
          `Confidence band: ${band}`,
          `Actual win rate: ${cal.actual_win_rate}`,
          `Expected win rate: ${cal.expected_win_rate}`,
          `Calibration gap: ${gap.toFixed(3)}`,
        ],
        novelty_score: gap > 0.35 ? 0.8 : 0.6,
        plausibility_score: 0.85,
        priority_score: Math.min(0.95, 0.6 + gap),
      })
    );
  }

  // ── 3. High-improvement optimization hypotheses ──────────────────────────────
  for (const opt of optimizations) {
    const score = parseFloat(opt.improvement_score ?? 0);
    if (score < 30) continue;

    const stratId = opt.strategy_id ?? "unknown";
    const optType = opt.optimization_type ?? "parameter";
    const param = opt.parameter_name ?? "unspecified";

    hypotheses.push(
      buildHypothesis({
        hypothesis_title: `Strategy ${stratId}: ${optType} optimization on "${param}" yields ${score.toFixed(0)}% improvement`,
        asset_type: "all",
        market_type: "all",
        hypothesis_text:
          `Optimization data indicates that adjusting "${param}" ` +
          `for strategy "${stratId}" via ${optType} optimization ` +
          `produces a ${score.toFixed(0)}% improvement score. ` +
          `This parameter change should be validated through replay before promotion.`,
        supporting_evidence: [
          `Strategy: ${stratId}`,
          `Optimization type: ${optType}`,
          `Parameter: ${param}`,
          `Improvement score: ${score.toFixed(0)}`,
          opt.notes ? `Notes: ${opt.notes}` : "No additional notes",
        ],
        novelty_score: 0.5,
        plausibility_score: Math.min(0.95, 0.5 + score / 200),
        priority_score: Math.min(0.95, 0.4 + score / 150),
        linked_strategy_id: stratId !== "unknown" ? stratId : null,
      })
    );
  }

  // ── 4. Replay extremes hypotheses ────────────────────────────────────────────
  if (replayResults.length > 0) {
    const tpHits = replayResults.filter((r) => r.replay_outcome === "tp_hit");
    const slHits = replayResults.filter((r) => r.replay_outcome === "sl_hit");

    // All tp_hit — momentum hypothesis
    if (tpHits.length === replayResults.length && replayResults.length >= 3) {
      hypotheses.push(
        buildHypothesis({
          hypothesis_title: "Recent replay shows 100% take-profit hit rate — possible data or strategy bias",
          asset_type: "all",
          market_type: "trending",
          hypothesis_text:
            `All ${replayResults.length} replay results hit take-profit, suggesting either a strong ` +
            `momentum bias in the dataset or overfitting in the replay parameters. ` +
            `Out-of-sample validation is recommended before promoting these strategies.`,
          supporting_evidence: [
            `Total replays: ${replayResults.length}`,
            `All outcomes: tp_hit`,
            "Possible cause: data selection bias or strategy overfitting",
          ],
          novelty_score: 0.65,
          plausibility_score: 0.6,
          priority_score: 0.7,
        })
      );
    }

    // All sl_hit — failure hypothesis
    if (slHits.length === replayResults.length && replayResults.length >= 3) {
      hypotheses.push(
        buildHypothesis({
          hypothesis_title: "Recent replay shows 100% stop-loss hit rate — strategies need re-evaluation",
          asset_type: "all",
          market_type: "all",
          hypothesis_text:
            `All ${replayResults.length} replay results hit stop-loss, indicating these strategies ` +
            `are performing at or below chance. Parameters, entry logic, or market regime alignment ` +
            `should be re-evaluated before any further testing.`,
          supporting_evidence: [
            `Total replays: ${replayResults.length}`,
            `All outcomes: sl_hit`,
            "Recommendation: full strategy re-evaluation",
          ],
          novelty_score: 0.7,
          plausibility_score: 0.8,
          priority_score: 0.85,
        })
      );
    }
  }

  console.log(`[hypotheses] Generated ${hypotheses.length} hypotheses.`);
  return hypotheses;
}
