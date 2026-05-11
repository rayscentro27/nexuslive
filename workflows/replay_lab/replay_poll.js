import "dotenv/config";

const SUPABASE_URL = process.env.SUPABASE_URL;
const SUPABASE_KEY = process.env.SUPABASE_KEY;

function supabaseHeaders() {
  return {
    "Content-Type": "application/json",
    "apikey": SUPABASE_KEY,
    "Authorization": `Bearer ${SUPABASE_KEY}`,
  };
}

/**
 * Polls reviewed_signal_proposals that have not yet been replayed.
 * Filters: status IN ('proposed', 'needs_review') AND asset_type != 'options'
 * Excludes proposals already present in paper_trade_runs.
 *
 * @param {number} limit
 * @returns {Promise<Array>}
 */
export async function pollProposalsForReplay(limit = 10) {
  // Fetch proposals eligible for replay
  const proposalsUrl =
    `${SUPABASE_URL}/rest/v1/reviewed_signal_proposals` +
    `?status=in.("proposed","needs_review")` +
    `&asset_type=neq.options` +
    `&select=id,signal_id,symbol,side,asset_type,strategy_id,` +
    `entry_price,stop_loss,take_profit,ai_confidence,trace_id` +
    `&limit=${limit}`;

  const proposalsRes = await fetch(proposalsUrl, {
    headers: supabaseHeaders(),
  });

  if (!proposalsRes.ok) {
    const err = await proposalsRes.text();
    throw new Error(`pollProposalsForReplay: Supabase error fetching proposals: ${err}`);
  }

  const proposals = await proposalsRes.json();

  if (!proposals.length) return [];

  // Fetch already-replayed proposal IDs
  const alreadyRunUrl =
    `${SUPABASE_URL}/rest/v1/paper_trade_runs` +
    `?select=proposal_id`;

  const alreadyRunRes = await fetch(alreadyRunUrl, {
    headers: supabaseHeaders(),
  });

  if (!alreadyRunRes.ok) {
    const err = await alreadyRunRes.text();
    throw new Error(`pollProposalsForReplay: Supabase error fetching runs: ${err}`);
  }

  const existingRuns = await alreadyRunRes.json();
  const existingIds = new Set(existingRuns.map((r) => r.proposal_id).filter(Boolean));

  return proposals.filter((p) => !existingIds.has(p.id));
}

/**
 * Polls reviewed_signal_proposals for options asset type that have not been replayed.
 *
 * @param {number} limit
 * @returns {Promise<Array>}
 */
export async function pollOptionsProposalsForReplay(limit = 10) {
  const proposalsUrl =
    `${SUPABASE_URL}/rest/v1/reviewed_signal_proposals` +
    `?status=in.("proposed","needs_review")` +
    `&asset_type=eq.options` +
    `&select=id,signal_id,symbol,asset_type,strategy_id,` +
    `ai_confidence,trace_id` +
    `&limit=${limit}`;

  const proposalsRes = await fetch(proposalsUrl, {
    headers: supabaseHeaders(),
  });

  if (!proposalsRes.ok) {
    const err = await proposalsRes.text();
    throw new Error(`pollOptionsProposalsForReplay: Supabase error fetching proposals: ${err}`);
  }

  const proposals = await proposalsRes.json();

  if (!proposals.length) return [];

  // Fetch already-replayed proposal IDs
  const alreadyRunUrl =
    `${SUPABASE_URL}/rest/v1/paper_trade_runs` +
    `?select=proposal_id`;

  const alreadyRunRes = await fetch(alreadyRunUrl, {
    headers: supabaseHeaders(),
  });

  if (!alreadyRunRes.ok) {
    const err = await alreadyRunRes.text();
    throw new Error(`pollOptionsProposalsForReplay: Supabase error fetching runs: ${err}`);
  }

  const existingRuns = await alreadyRunRes.json();
  const existingIds = new Set(existingRuns.map((r) => r.proposal_id).filter(Boolean));

  return proposals.filter((p) => !existingIds.has(p.id));
}
