import "dotenv/config";

const SUPABASE_URL = process.env.SUPABASE_URL;
const SUPABASE_KEY = process.env.SUPABASE_KEY;

function supabaseHeaders() {
  return {
    apikey: SUPABASE_KEY,
    Authorization: `Bearer ${SUPABASE_KEY}`,
    "Content-Type": "application/json",
  };
}

async function supabaseGet(table, params = "") {
  const url = `${SUPABASE_URL}/rest/v1/${table}${params ? "?" + params : ""}`;
  const res = await fetch(url, { headers: supabaseHeaders() });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`Supabase GET ${table} failed (${res.status}): ${body}`);
  }
  return res.json();
}

function mean(arr) {
  if (!arr.length) return 0;
  return arr.reduce((a, b) => a + b, 0) / arr.length;
}

/**
 * Computes AI analyst performance metrics.
 * @returns {Promise<Object>} Analyst metrics object
 */
export async function computeAnalystMetrics() {
  console.log("[analyst-metrics] Fetching reviewed_signal_proposals...");

  const proposals = await supabaseGet(
    "reviewed_signal_proposals",
    "select=id,status,ai_confidence,trace_id"
  ).catch((err) => {
    console.warn("[analyst-metrics] reviewed_signal_proposals fetch failed:", err.message);
    return [];
  });

  const total_reviewed = proposals.length;

  if (!total_reviewed) {
    console.log("[analyst-metrics] No proposals found. Returning zero metrics.");
    return {
      total_reviewed: 0,
      block_rate: 0,
      proposed_rate: 0,
      avg_confidence: 0,
      high_conf_win_rate: null,
      low_conf_win_rate: null,
    };
  }

  const blocked = proposals.filter((p) => p.status === "blocked");
  const proposed = proposals.filter((p) =>
    p.status === "proposed" || p.status === "needs_review" || p.status === "approved"
  );

  const block_rate = parseFloat((blocked.length / total_reviewed).toFixed(4));
  const proposed_rate = parseFloat((proposed.length / total_reviewed).toFixed(4));

  const confidenceValues = proposals
    .map((p) => p.ai_confidence)
    .filter((v) => v !== null && v !== undefined);
  const avg_confidence = parseFloat(mean(confidenceValues).toFixed(4));

  // Cross-reference with proposal_outcomes for confidence accuracy
  console.log("[analyst-metrics] Fetching proposal_outcomes for confidence cross-reference...");

  const outcomes = await supabaseGet(
    "proposal_outcomes",
    "select=proposal_id,outcome_status"
  ).catch((err) => {
    console.warn("[analyst-metrics] proposal_outcomes fetch failed:", err.message);
    return [];
  });

  let high_conf_win_rate = null;
  let low_conf_win_rate = null;

  if (outcomes.length && confidenceValues.length) {
    const outcomeMap = new Map(outcomes.map((o) => [o.proposal_id, o.outcome_status]));

    // High confidence = ai_confidence >= 0.75, Low = < 0.75
    const HIGH_THRESHOLD = 0.75;

    const highConfProposals = proposals.filter(
      (p) => p.ai_confidence !== null && p.ai_confidence >= HIGH_THRESHOLD
    );
    const lowConfProposals = proposals.filter(
      (p) => p.ai_confidence !== null && p.ai_confidence < HIGH_THRESHOLD
    );

    const calcWinRate = (group) => {
      const withOutcome = group.filter((p) => outcomeMap.has(p.id));
      if (!withOutcome.length) return null;
      const wins = withOutcome.filter(
        (p) => outcomeMap.get(p.id) === "win"
      );
      return parseFloat((wins.length / withOutcome.length).toFixed(4));
    };

    high_conf_win_rate = calcWinRate(highConfProposals);
    low_conf_win_rate = calcWinRate(lowConfProposals);
  }

  const result = {
    total_reviewed,
    block_rate,
    proposed_rate,
    avg_confidence,
    high_conf_win_rate,
    low_conf_win_rate,
  };

  console.log(
    `[analyst-metrics] total=${total_reviewed}, block_rate=${block_rate}, proposed_rate=${proposed_rate}, avg_confidence=${avg_confidence}`
  );
  return result;
}
