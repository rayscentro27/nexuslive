/**
 * approval_queue.js
 * Manages the approval_queue Supabase table.
 * Queues proposals that passed risk office (approved or manual_review).
 * Status: pending → approved | rejected (human updates manually).
 */

import "dotenv/config";

const SUPABASE_URL = process.env.SUPABASE_URL;
const SERVICE_KEY  = process.env.SUPABASE_SERVICE_ROLE_KEY;
const SUPABASE_KEY = process.env.SUPABASE_KEY;

function wh() {   // write headers
  return {
    "Content-Type": "application/json",
    "apikey":        SERVICE_KEY,
    "Authorization": `Bearer ${SERVICE_KEY}`,
    "Prefer":        "return=representation",
  };
}
function rh() {   // read headers
  return {
    "Content-Type": "application/json",
    "apikey":        SUPABASE_KEY,
    "Authorization": `Bearer ${SUPABASE_KEY}`,
  };
}

/**
 * Add a proposal + risk decision to the approval queue.
 */
export async function enqueueApproval(item) {
  if (!SUPABASE_URL || !SERVICE_KEY) throw new Error("service_role key required");

  const row = {
    proposal_id:     item.proposal_id ?? null,
    signal_id:       item.signal_id   ?? null,
    symbol:          item.symbol,
    side:            item.side        ?? null,
    asset_type:      item.asset_type  ?? "forex",
    strategy_id:     item.strategy_id ?? null,
    risk_score:      item.risk_score  ?? null,
    decision:        item.decision,           // approved | manual_review
    approval_status: "pending",
    trace_id:        item.trace_id    ?? null,
  };

  const res = await fetch(`${SUPABASE_URL}/rest/v1/approval_queue`, {
    method:  "POST",
    headers: wh(),
    body:    JSON.stringify(row),
  });

  if (!res.ok) throw new Error(`enqueueApproval: ${res.status} ${await res.text()}`);
  const body  = await res.json();
  const saved = Array.isArray(body) ? body[0] : body;
  console.log(`[approval-queue] Queued: ${saved?.id} — ${row.symbol} ${row.decision}`);
  return saved;
}

/**
 * Fetch all pending approvals that have not yet had an alert sent.
 * (Alerts are sent once; after sending we mark them with a note in risk_notes or
 *  simply track by checking if a Telegram alert already went out.)
 */
export async function fetchPendingApprovals() {
  if (!SUPABASE_URL || !SUPABASE_KEY) return [];

  const url = new URL(`${SUPABASE_URL}/rest/v1/approval_queue`);
  url.searchParams.set("approval_status", "eq.pending");
  url.searchParams.set("select", "*");
  url.searchParams.set("order", "created_at.asc");
  url.searchParams.set("limit", "10");

  const res = await fetch(url.toString(), { headers: rh() });
  if (!res.ok) return [];
  return await res.json();
}

/**
 * Update approval_status for a queue entry.
 * (Called manually or by a future webhook handler — not auto-approved.)
 */
export async function updateApprovalStatus(queueId, status) {
  const res = await fetch(
    `${SUPABASE_URL}/rest/v1/approval_queue?id=eq.${queueId}`,
    {
      method:  "PATCH",
      headers: { ...wh(), "Prefer": "return=minimal" },
      body:    JSON.stringify({ approval_status: status }),
    }
  );
  if (!res.ok) console.warn(`[approval-queue] Could not update ${queueId}: ${res.status}`);
}
