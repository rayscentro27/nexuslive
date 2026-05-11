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
 * Computes risk office performance metrics from risk_decisions table.
 * @returns {Promise<Object>} Risk metrics object
 */
export async function computeRiskMetrics() {
  console.log("[risk-metrics] Fetching risk_decisions...");

  const decisions = await supabaseGet(
    "risk_decisions",
    "select=proposal_id,decision,risk_score,risk_flags,trace_id"
  ).catch((err) => {
    console.warn("[risk-metrics] risk_decisions fetch failed:", err.message);
    return [];
  });

  const total_decisions = decisions.length;

  if (!total_decisions) {
    console.log("[risk-metrics] No risk decisions found. Returning zero metrics.");
    return {
      total_decisions: 0,
      approved: 0,
      manual_review: 0,
      blocked: 0,
      approval_rate: 0,
      avg_risk_score: 0,
      top_flags: [],
      false_approval_rate: null,
    };
  }

  const approved = decisions.filter((d) =>
    d.decision === "approved" || d.decision === "approve"
  );
  const manual_review = decisions.filter((d) =>
    d.decision === "manual_review" || d.decision === "review"
  );
  const blocked = decisions.filter((d) =>
    d.decision === "blocked" || d.decision === "block"
  );

  const approval_rate = parseFloat(
    (approved.length / total_decisions).toFixed(4)
  );

  const riskScores = decisions
    .map((d) => d.risk_score)
    .filter((v) => v !== null && v !== undefined);
  const avg_risk_score = parseFloat(mean(riskScores).toFixed(4));

  // Tally risk flags
  const flagCounts = new Map();
  for (const d of decisions) {
    let flags = d.risk_flags;
    if (!flags) continue;
    // Handle both array and stringified array
    if (typeof flags === "string") {
      try {
        flags = JSON.parse(flags);
      } catch {
        flags = [flags];
      }
    }
    // risk_flags stored as {flag_name: bool} object — extract truthy keys
    if (!Array.isArray(flags)) {
      if (typeof flags === "object" && flags !== null) {
        flags = Object.entries(flags).filter(([, v]) => v).map(([k]) => k);
      } else {
        flags = [String(flags)];
      }
    }
    for (const flag of flags) {
      const key = String(flag).trim();
      if (key) flagCounts.set(key, (flagCounts.get(key) ?? 0) + 1);
    }
  }

  const top_flags = [...flagCounts.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10)
    .map(([flag, count]) => ({ flag, count }));

  // Cross-reference: approved decisions that later became losses
  let false_approval_rate = null;

  console.log("[risk-metrics] Cross-referencing with proposal_outcomes...");
  const outcomes = await supabaseGet(
    "proposal_outcomes",
    "select=proposal_id,outcome_status"
  ).catch((err) => {
    console.warn("[risk-metrics] proposal_outcomes fetch failed:", err.message);
    return [];
  });

  if (outcomes.length && approved.length) {
    const outcomeMap = new Map(outcomes.map((o) => [o.proposal_id, o.outcome_status]));

    const approvedWithOutcome = approved.filter((d) =>
      outcomeMap.has(d.proposal_id)
    );

    if (approvedWithOutcome.length) {
      const falsely = approvedWithOutcome.filter(
        (d) => outcomeMap.get(d.proposal_id) === "loss"
      );
      false_approval_rate = parseFloat(
        (falsely.length / approvedWithOutcome.length).toFixed(4)
      );
    }
  }

  const result = {
    total_decisions,
    approved: approved.length,
    manual_review: manual_review.length,
    blocked: blocked.length,
    approval_rate,
    avg_risk_score,
    top_flags,
    false_approval_rate,
  };

  console.log(
    `[risk-metrics] total=${total_decisions}, approved=${approved.length}, approval_rate=${approval_rate}, avg_risk_score=${avg_risk_score}`
  );
  return result;
}
