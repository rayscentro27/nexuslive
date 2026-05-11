import "dotenv/config";

// ── SAFETY GUARD ──────────────────────────────────────────────────────────────
// This module is RESEARCH ONLY. Generates human-readable research briefs.
// No trading, no broker connections.
// ─────────────────────────────────────────────────────────────────────────────

function num(val, decimals = 2) {
  if (val === null || val === undefined) return "N/A";
  return parseFloat(val).toFixed(decimals);
}

function pct(val) {
  if (val === null || val === undefined) return "N/A";
  return `${(parseFloat(val) * 100).toFixed(1)}%`;
}

/**
 * Creates a brief summarizing the top 3 hypotheses.
 * @param {Array} hypotheses - Ranked hypotheses
 * @returns {Object}
 */
function topHypothesesBrief(hypotheses) {
  const top3 = hypotheses.slice(0, 3);
  const now = new Date().toISOString();

  if (top3.length === 0) {
    return {
      title: "Top Research Hypotheses",
      summary: "No hypotheses were generated in this cycle.",
      priority: "low",
      brief_type: "top_hypotheses",
      linked_hypothesis_id: null,
      created_at: now,
    };
  }

  const lines = top3.map((h, i) => {
    const priority = num(h.priority_score);
    const plausibility = num(h.plausibility_score);
    const assetType = h.asset_type ?? "all";
    return (
      `${i + 1}. [${assetType}] ${h.hypothesis_title} ` +
      `(priority=${priority}, plausibility=${plausibility}, status=${h.status})`
    );
  });

  const topPriority = top3[0].priority_score ?? 0;
  const briefPriority = topPriority >= 0.75 ? "high" : topPriority >= 0.5 ? "medium" : "low";

  return {
    title: "Top Research Hypotheses",
    summary:
      `${hypotheses.length} hypothesis(es) generated this cycle. Top 3:\n` +
      lines.join("\n"),
    priority: briefPriority,
    brief_type: "top_hypotheses",
    linked_hypothesis_id: top3[0].trace_id ?? null,
    created_at: now,
  };
}

/**
 * Creates a brief summarizing all coverage gaps.
 * @param {Array} gaps
 * @returns {Object}
 */
function coverageGapsBrief(gaps) {
  const now = new Date().toISOString();

  if (gaps.length === 0) {
    return {
      title: "Research Coverage Gaps",
      summary: "No coverage gaps detected in this cycle.",
      priority: "low",
      brief_type: "coverage_gaps",
      linked_hypothesis_id: null,
      created_at: now,
    };
  }

  const high = gaps.filter((g) => g.severity === "high");
  const medium = gaps.filter((g) => g.severity === "medium");
  const low = gaps.filter((g) => g.severity === "low");

  const lines = [
    `${gaps.length} gap(s) found — high: ${high.length}, medium: ${medium.length}, low: ${low.length}.`,
  ];

  for (const g of gaps) {
    lines.push(`[${g.severity}] ${g.gap_type}: ${g.description}`);
  }

  const overallPriority = high.length > 0 ? "high" : medium.length > 0 ? "medium" : "low";

  return {
    title: "Research Coverage Gaps",
    summary: lines.join("\n"),
    priority: overallPriority,
    brief_type: "coverage_gaps",
    linked_hypothesis_id: null,
    created_at: now,
  };
}

/**
 * Creates a performance snapshot brief from scorecards.
 * @param {Array} scorecards
 * @returns {Object}
 */
function performanceSnapshotBrief(scorecards) {
  const now = new Date().toISOString();

  if (scorecards.length === 0) {
    return {
      title: "Agent Performance Snapshot",
      summary: "No scorecard data available. Run performance lab to generate scorecards.",
      priority: "low",
      brief_type: "performance_snapshot",
      linked_hypothesis_id: null,
      created_at: now,
    };
  }

  function metricVal(agentName, metricType) {
    const row = scorecards.find(
      (s) => s.agent_name === agentName && s.metric_type === metricType
    );
    return row ? row.metric_value : null;
  }

  // Analyst metrics
  const blockRate = metricVal("analyst", "block_rate");
  const avgConf = metricVal("analyst", "avg_confidence");
  const totalReviewed = metricVal("analyst", "total_reviewed");

  // Risk office metrics
  const approvalRate = metricVal("risk_office", "approval_rate");
  const totalDecisions = metricVal("risk_office", "total_decisions");
  const avgRiskScore = metricVal("risk_office", "avg_risk_score");

  const lines = [
    "AI Analyst:",
    `  Total reviewed: ${totalReviewed ?? "N/A"}`,
    `  Block rate: ${pct(blockRate)}`,
    `  Avg confidence: ${num(avgConf, 3)}`,
    "",
    "Risk Office:",
    `  Total decisions: ${totalDecisions ?? "N/A"}`,
    `  Approval rate: ${pct(approvalRate)}`,
    `  Avg risk score: ${num(avgRiskScore, 3)}`,
  ];

  // Determine priority based on interesting thresholds
  let priority = "low";
  if (blockRate !== null && blockRate > 0.5) priority = "medium";
  if (approvalRate !== null && approvalRate < 0.3) priority = "high";

  return {
    title: "Agent Performance Snapshot",
    summary: lines.join("\n"),
    priority,
    brief_type: "performance_snapshot",
    linked_hypothesis_id: null,
    created_at: now,
  };
}

/**
 * Generates all research briefs for this cycle.
 * @param {Array} hypotheses - Ranked hypotheses
 * @param {Array} gaps - Detected coverage gaps
 * @param {Object} inputs - Output from pollResearchInputs()
 * @returns {Array<{title, summary, priority, brief_type, linked_hypothesis_id, created_at}>}
 */
export function generateBriefs(hypotheses, gaps, inputs) {
  const { scorecards = [] } = inputs;

  console.log("[briefs] Generating research briefs...");

  const briefs = [
    topHypothesesBrief(hypotheses),
    coverageGapsBrief(gaps),
    performanceSnapshotBrief(scorecards),
  ];

  console.log(`[briefs] Generated ${briefs.length} brief(s).`);
  return briefs;
}
