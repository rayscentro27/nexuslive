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

/**
 * Returns approved proposals that do not yet have a recorded outcome.
 * Joins reviewed_signal_proposals + approval_queue (approved) - proposal_outcomes.
 */
export async function getPendingOutcomeProposals() {
  console.log("[mapper] Fetching approved proposals from approval_queue...");

  // Fetch approved entries from approval_queue
  const approved = await supabaseGet(
    "approval_queue",
    "decision=eq.approved&select=proposal_id"
  ).catch((err) => {
    console.warn("[mapper] approval_queue fetch failed:", err.message);
    return [];
  });

  if (!approved.length) {
    console.log("[mapper] No approved proposals found.");
    return [];
  }

  const approvedIds = approved.map((r) => r.proposal_id);

  // Fetch existing outcomes so we can exclude them
  const existingOutcomes = await supabaseGet(
    "proposal_outcomes",
    "select=proposal_id"
  ).catch((err) => {
    console.warn("[mapper] proposal_outcomes fetch failed:", err.message);
    return [];
  });

  const outcomeIds = new Set(existingOutcomes.map((r) => r.proposal_id));

  // Filter to approved proposals without outcomes
  const pendingIds = approvedIds.filter((id) => !outcomeIds.has(id));

  if (!pendingIds.length) {
    console.log("[mapper] All approved proposals already have outcomes.");
    return [];
  }

  console.log(`[mapper] ${pendingIds.length} proposals pending outcome...`);

  // Fetch full proposal details for pending IDs
  const idList = pendingIds.map((id) => `"${id}"`).join(",");
  const proposals = await supabaseGet(
    "reviewed_signal_proposals",
    `proposal_id=in.(${idList})&select=proposal_id,symbol,side,asset_type,strategy_id,entry_price,stop_loss,take_profit,ai_confidence,trace_id`
  ).catch((err) => {
    console.warn("[mapper] reviewed_signal_proposals fetch failed:", err.message);
    return [];
  });

  return proposals.map((p) => ({
    proposal_id: p.proposal_id,
    symbol: p.symbol,
    side: p.side,
    asset_type: p.asset_type,
    strategy_id: p.strategy_id,
    entry_price: p.entry_price,
    stop_loss: p.stop_loss,
    take_profit: p.take_profit,
    ai_confidence: p.ai_confidence,
    trace_id: p.trace_id,
  }));
}

/**
 * Returns aggregate outcome stats across all recorded outcomes.
 */
export async function getOutcomeStats() {
  console.log("[mapper] Computing outcome stats...");

  const outcomes = await supabaseGet(
    "proposal_outcomes",
    "select=outcome_status"
  ).catch((err) => {
    console.warn("[mapper] proposal_outcomes fetch failed:", err.message);
    return [];
  });

  const stats = { total: 0, wins: 0, losses: 0, breakevens: 0, pending: 0 };

  for (const row of outcomes) {
    stats.total++;
    switch (row.outcome_status) {
      case "win":
        stats.wins++;
        break;
      case "loss":
        stats.losses++;
        break;
      case "breakeven":
        stats.breakevens++;
        break;
      default:
        stats.pending++;
    }
  }

  // Count pending from approval_queue
  const pending = await getPendingOutcomeProposals().catch(() => []);
  stats.pending = pending.length;

  console.log(`[mapper] Stats: total=${stats.total}, wins=${stats.wins}, losses=${stats.losses}, breakevens=${stats.breakevens}, pending=${stats.pending}`);
  return stats;
}
