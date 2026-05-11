import "dotenv/config";

// ── SAFETY GUARD ──────────────────────────────────────────────────────────────
// This module is RESEARCH ONLY. Detects coverage gaps in research data.
// No trading, no broker connections.
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Detects research coverage gaps from inputs and current hypotheses.
 * @param {Object} inputs - Output from pollResearchInputs()
 * @param {Array} hypotheses - Output from generateHypotheses()
 * @returns {Array<{gap_type, asset_type, description, severity, notes, created_at}>}
 */
export function detectCoverageGaps(inputs, hypotheses) {
  const {
    artifacts = [],
    claims = [],
    optimizations = [],
    replayResults = [],
    scorecards = [],
    calibration = [],
  } = inputs;

  console.log("[gaps] Detecting coverage gaps...");

  const now = new Date().toISOString();
  const gaps = [];

  // ── 1. No options hypotheses ─────────────────────────────────────────────────
  const optionsHypotheses = hypotheses.filter(
    (h) => h.asset_type === "options"
  );
  if (optionsHypotheses.length === 0) {
    gaps.push({
      gap_type: "no_options_coverage",
      asset_type: "options",
      description: "No hypotheses with asset_type=options were generated in this cycle.",
      severity: "high",
      notes:
        "Research inputs may lack options-specific content. " +
        "Consider adding options-focused research artifacts or claims.",
      created_at: now,
    });
  }

  // ── 2. Weak calibration ──────────────────────────────────────────────────────
  const weakCalibration = calibration.filter(
    (c) => Math.abs(parseFloat(c.calibration_gap ?? 0)) > 0.3
  );
  if (weakCalibration.length > 0) {
    const bands = weakCalibration.map((c) => c.confidence_band ?? "unknown").join(", ");
    gaps.push({
      gap_type: "weak_confidence_calibration",
      asset_type: "all",
      description: `Confidence calibration gap > 0.3 in bands: ${bands}.`,
      severity: "medium",
      notes:
        `${weakCalibration.length} calibration band(s) show significant deviation ` +
        "between expected and actual win rates. AI confidence thresholds need review.",
      created_at: now,
    });
  }

  // ── 3. No replay data ────────────────────────────────────────────────────────
  if (replayResults.length === 0) {
    gaps.push({
      gap_type: "no_replay_data",
      asset_type: "all",
      description: "No replay results found in replay_results table.",
      severity: "high",
      notes:
        "Hypothesis validation cannot proceed without replay data. " +
        "Run the replay lab to populate replay_results before promoting hypotheses.",
      created_at: now,
    });
  }

  // ── 4. Low scorecard count ───────────────────────────────────────────────────
  if (scorecards.length < 5) {
    gaps.push({
      gap_type: "low_scorecard_coverage",
      asset_type: "all",
      description: `Only ${scorecards.length} agent scorecard metric(s) found (expected >= 5).`,
      severity: "low",
      notes:
        "Run the performance lab scorecard generator to populate agent_scorecards " +
        "with analyst and risk office metrics.",
      created_at: now,
    });
  }

  // ── 5. No optimization data ──────────────────────────────────────────────────
  if (optimizations.length === 0) {
    gaps.push({
      gap_type: "no_optimization_data",
      asset_type: "all",
      description: "No strategy optimization records found in strategy_optimizations.",
      severity: "medium",
      notes:
        "Hypothesis generation from optimization signals is disabled. " +
        "Populate strategy_optimizations via the optimization lab.",
      created_at: now,
    });
  }

  // ── 6. Underresearched themes ────────────────────────────────────────────────
  // Detect from clusterer — we need clusters passed alongside inputs,
  // but we infer from artifacts if available.
  // For hypotheses, check if any theme-linked hypothesis has very low evidence.
  const lowEvidenceHypotheses = hypotheses.filter((h) => {
    const evidenceLines = h.supporting_evidence ?? [];
    const sourceMatch = evidenceLines
      .join(" ")
      .match(/matched (\d+) source/);
    if (sourceMatch) {
      return parseInt(sourceMatch[1], 10) < 2;
    }
    return false;
  });

  for (const h of lowEvidenceHypotheses) {
    const themeMatch = h.hypothesis_text?.match(/"([^"]+)"/);
    const themeName = themeMatch ? themeMatch[1] : h.hypothesis_title.slice(0, 40);
    gaps.push({
      gap_type: "underresearched_theme",
      asset_type: "all",
      description: `Theme "${themeName}" has < 2 sources and may be under-evidenced.`,
      severity: "low",
      notes:
        `Hypothesis "${h.hypothesis_title.slice(0, 60)}" rests on thin evidence. ` +
        "Additional research artifacts or claims in this theme would strengthen the hypothesis.",
      created_at: now,
    });
  }

  console.log(
    `[gaps] Detected ${gaps.length} gap(s): ` +
    gaps.map((g) => `${g.gap_type}(${g.severity})`).join(", ")
  );

  return gaps;
}
