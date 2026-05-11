import "dotenv/config";
import { computeAnalystMetrics } from "./analyst_metrics.js";
import { computeRiskMetrics } from "./risk_metrics.js";

const SUPABASE_URL = process.env.SUPABASE_URL;
const SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;

function serviceHeaders() {
  return {
    apikey: SUPABASE_SERVICE_ROLE_KEY,
    Authorization: `Bearer ${SUPABASE_SERVICE_ROLE_KEY}`,
    "Content-Type": "application/json",
    Prefer: "resolution=merge-duplicates",
  };
}

async function upsertScorecard(agent_name, metric_type, metric_value, notes) {
  const url = `${SUPABASE_URL}/rest/v1/agent_scorecards?on_conflict=agent_name,metric_type,period`;
  const payload = {
    agent_name,
    agent_role: agent_name,
    metric_type,
    metric_value,
    notes: notes ?? null,
    updated_at: new Date().toISOString(),
  };

  const res = await fetch(url, {
    method: "POST",
    headers: serviceHeaders(),
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const body = await res.text();
    throw new Error(`Upsert scorecard failed (${res.status}): ${body}`);
  }

  return res.status;
}

function analystRows(metrics) {
  return [
    {
      metric_type: "total_reviewed",
      metric_value: metrics.total_reviewed,
      notes: "Total proposals reviewed by AI analyst",
    },
    {
      metric_type: "block_rate",
      metric_value: metrics.block_rate,
      notes: `${(metrics.block_rate * 100).toFixed(1)}% of proposals blocked`,
    },
    {
      metric_type: "proposed_rate",
      metric_value: metrics.proposed_rate,
      notes: `${(metrics.proposed_rate * 100).toFixed(1)}% of proposals sent to approval`,
    },
    {
      metric_type: "avg_confidence",
      metric_value: metrics.avg_confidence,
      notes: `Mean ai_confidence across all reviewed proposals`,
    },
    ...(metrics.high_conf_win_rate !== null
      ? [
          {
            metric_type: "high_conf_win_rate",
            metric_value: metrics.high_conf_win_rate,
            notes: "Win rate for proposals with ai_confidence >= 0.75",
          },
        ]
      : []),
    ...(metrics.low_conf_win_rate !== null
      ? [
          {
            metric_type: "low_conf_win_rate",
            metric_value: metrics.low_conf_win_rate,
            notes: "Win rate for proposals with ai_confidence < 0.75",
          },
        ]
      : []),
  ];
}

function riskRows(metrics) {
  const rows = [
    {
      metric_type: "total_decisions",
      metric_value: metrics.total_decisions,
      notes: "Total risk decisions made",
    },
    {
      metric_type: "approval_rate",
      metric_value: metrics.approval_rate,
      notes: `${(metrics.approval_rate * 100).toFixed(1)}% of proposals approved`,
    },
    {
      metric_type: "avg_risk_score",
      metric_value: metrics.avg_risk_score,
      notes: "Mean risk score across all decisions",
    },
    {
      metric_type: "blocked_count",
      metric_value: metrics.blocked,
      notes: "Number of proposals blocked by risk office",
    },
    {
      metric_type: "manual_review_count",
      metric_value: metrics.manual_review,
      notes: "Number of proposals sent to manual review",
    },
  ];

  if (metrics.false_approval_rate !== null) {
    rows.push({
      metric_type: "false_approval_rate",
      metric_value: metrics.false_approval_rate,
      notes: "Rate of approved proposals that resulted in losses",
    });
  }

  if (metrics.top_flags.length) {
    rows.push({
      metric_type: "top_risk_flag",
      metric_value: null,
      notes: `Most common flag: ${metrics.top_flags[0].flag} (${metrics.top_flags[0].count}x)`,
    });
  }

  return rows;
}

/**
 * Generates scorecards for analyst and risk_office agents and writes to agent_scorecards.
 * @returns {Promise<{ updated: number, created: number }>}
 */
export async function generateAllScorecards() {
  console.log("[scorecards] Generating all agent scorecards...");

  const [analystMetrics, riskMetrics] = await Promise.all([
    computeAnalystMetrics(),
    computeRiskMetrics(),
  ]);

  const scorecardTasks = [
    ...analystRows(analystMetrics).map((r) => ({
      agent_name: "analyst",
      ...r,
    })),
    ...riskRows(riskMetrics).map((r) => ({
      agent_name: "risk_office",
      ...r,
    })),
  ];

  let created = 0;
  let errors = 0;

  for (const task of scorecardTasks) {
    try {
      const status = await upsertScorecard(
        task.agent_name,
        task.metric_type,
        task.metric_value,
        task.notes
      );
      created++;
      console.log(
        `[scorecards] Upserted ${task.agent_name}.${task.metric_type} = ${task.metric_value}`
      );
    } catch (err) {
      errors++;
      console.warn(
        `[scorecards] Failed to upsert ${task.agent_name}.${task.metric_type}: ${err.message}`
      );
    }
  }

  console.log(
    `[scorecards] Complete — upserted: ${created}, errors: ${errors}`
  );

  // Return created/updated split is not possible without checking pre-existence;
  // treat all successful upserts as "updated" (merge-duplicates handles insert/update)
  return { updated: created, created: 0 };
}
