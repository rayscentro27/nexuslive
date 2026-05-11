import "dotenv/config";

// ── SAFETY GUARD ──────────────────────────────────────────────────────────────
// This module is RESEARCH ONLY. No trading, no broker connections.
// ─────────────────────────────────────────────────────────────────────────────

const THEMES = [
  {
    name: "breakout_behavior",
    keywords: [
      "breakout", "break out", "price break", "level break", "resistance break",
      "support break", "range break", "consolidation break",
    ],
  },
  {
    name: "spread_sensitivity",
    keywords: [
      "spread", "bid ask", "bid-ask", "slippage", "transaction cost",
      "spread cost", "liquidity cost",
    ],
  },
  {
    name: "iv_crush",
    keywords: [
      "iv crush", "implied volatility crush", "vol crush", "volatility crush",
      "post earnings", "earnings crush", "vega risk",
    ],
  },
  {
    name: "mean_reversion",
    keywords: [
      "mean reversion", "revert", "reversion", "oversold bounce", "overbought pullback",
      "range bound", "regression to mean", "rubber band",
    ],
  },
  {
    name: "trend_continuation",
    keywords: [
      "trend continuation", "trend following", "momentum continuation",
      "pullback entry", "flag pattern", "higher high", "higher low",
      "trend strength", "adx",
    ],
  },
  {
    name: "covered_call_stability",
    keywords: [
      "covered call", "call writing", "income strategy", "premium collection",
      "covered write", "call overlay",
    ],
  },
  {
    name: "options_structure_weakness",
    keywords: [
      "options structure", "naked put", "short put", "credit spread weakness",
      "iron condor failure", "theta decay risk", "assignment risk",
      "options loss", "undefined risk",
    ],
  },
  {
    name: "confidence_calibration_issue",
    keywords: [
      "confidence calibration", "overconfidence", "underconfidence",
      "miscalibrated", "calibration gap", "probability estimate",
      "expected vs actual", "win rate mismatch",
    ],
  },
  {
    name: "risk_threshold_adjustment",
    keywords: [
      "risk threshold", "stop loss adjustment", "position size adjustment",
      "max loss", "drawdown limit", "risk parameter", "risk rule",
      "risk tolerance", "kelly criterion",
    ],
  },
  {
    name: "volatility_regime",
    keywords: [
      "volatility regime", "low volatility", "high volatility", "vix",
      "vol spike", "volatility expansion", "volatility contraction",
      "regime change", "market regime",
    ],
  },
];

function textOf(artifact) {
  return [artifact.title ?? "", artifact.summary ?? ""].join(" ").toLowerCase();
}

function claimTextOf(claim) {
  return [claim.claim_text ?? "", claim.claim_type ?? ""].join(" ").toLowerCase();
}

function matchesTheme(text, theme) {
  return theme.keywords.some((kw) => text.includes(kw.toLowerCase()));
}

function extractKeyTerms(matchedKeywords, text) {
  // Return unique matched keywords found in the text, up to 8
  const found = matchedKeywords.filter((kw) => text.includes(kw.toLowerCase()));
  return [...new Set(found)].slice(0, 8);
}

function computeConfidence(sourceCount, totalSources) {
  if (totalSources === 0) return 0;
  const ratio = sourceCount / Math.max(totalSources, 1);
  if (sourceCount >= 5) return Math.min(0.95, 0.7 + ratio * 0.25);
  if (sourceCount >= 3) return Math.min(0.75, 0.5 + ratio * 0.25);
  if (sourceCount >= 1) return Math.min(0.5, 0.2 + ratio * 0.3);
  return 0;
}

/**
 * Clusters research artifacts and claims into predefined themes.
 * @param {Object} inputs - Output from pollResearchInputs()
 * @returns {Array<{cluster_name, theme, source_count, summary, key_terms, confidence}>}
 */
export function clusterResearch(inputs) {
  const { artifacts = [], claims = [] } = inputs;

  console.log(`[clusterer] Clustering ${artifacts.length} artifacts and ${claims.length} claims...`);

  const totalSources = artifacts.length + claims.length;
  const clusters = [];

  for (const theme of THEMES) {
    const matchedArtifacts = artifacts.filter((a) => matchesTheme(textOf(a), theme));
    const matchedClaims = claims.filter((c) => matchesTheme(claimTextOf(c), theme));

    const sourceCount = matchedArtifacts.length + matchedClaims.length;

    // Collect all matching text for key term extraction
    const allText = [
      ...matchedArtifacts.map(textOf),
      ...matchedClaims.map(claimTextOf),
    ].join(" ");

    const keyTerms = extractKeyTerms(theme.keywords, allText);

    // Build summary from artifact titles (up to 3)
    const titles = matchedArtifacts.slice(0, 3).map((a) => a.title ?? "(untitled)");
    const claimSamples = matchedClaims.slice(0, 2).map((c) => c.claim_text ?? "");

    let summary = "";
    if (sourceCount === 0) {
      summary = `No sources found for theme: ${theme.name}.`;
    } else {
      summary = `Theme "${theme.name}" matched ${matchedArtifacts.length} artifact(s) and ${matchedClaims.length} claim(s).`;
      if (titles.length) {
        summary += ` Articles: ${titles.join("; ")}.`;
      }
      if (claimSamples.length) {
        summary += ` Sample claims: ${claimSamples.join("; ")}.`;
      }
    }

    const confidence = computeConfidence(sourceCount, totalSources);

    clusters.push({
      cluster_name: theme.name,
      theme: theme.name,
      source_count: sourceCount,
      summary,
      key_terms: keyTerms,
      confidence,
    });
  }

  const nonEmpty = clusters.filter((c) => c.source_count > 0);
  console.log(
    `[clusterer] Produced ${clusters.length} clusters (${nonEmpty.length} with matches).`
  );

  return clusters;
}
