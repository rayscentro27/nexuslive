/**
 * approval_runner.js
 * Sends Telegram approval alerts for pending queue items.
 * Run standalone to drain the approval queue alert backlog.
 *
 * node approval_runner.js
 */

import "dotenv/config";
import { fetchPendingApprovals, updateApprovalStatus } from "./approval_queue.js";
import { sendApprovalAlert } from "./telegram_approval_alert.js";

async function run() {
  console.log("[approval-runner] Checking approval queue...");
  const pending = await fetchPendingApprovals();

  if (!pending.length) {
    console.log("[approval-runner] No pending approvals.");
    return;
  }

  console.log(`[approval-runner] ${pending.length} pending approval(s).`);
  let sent = 0;

  for (const item of pending) {
    try {
      await sendApprovalAlert(item);
      // Mark as notified — we keep status 'pending' (human decides approved/rejected)
      // but add a timestamp note by updating approval_status briefly.
      // In practice status stays 'pending' until human manually updates via Supabase.
      console.log(`[approval-runner] Alert sent for ${item.symbol} ${item.strategy_id}`);
      sent++;
    } catch (err) {
      console.error(`[approval-runner] Failed ${item.id}: ${err.message}`);
    }
  }

  console.log(`[approval-runner] Done — sent ${sent}/${pending.length} alerts.`);
}

run()
  .then(() => process.exit(0))
  .catch((err) => { console.error(err); process.exit(1); });
