import "dotenv/config";

/**
 * Simulates a forex trade from a proposal using static R:R analysis.
 * No live price data is used. Outcome is determined deterministically
 * from the proposal's own entry_price, stop_loss, and take_profit.
 *
 * R:R calculation:
 *   risk   = |entry_price - stop_loss|
 *   reward = |take_profit - entry_price|
 *   rr_ratio = reward / risk
 *
 * Outcome rules:
 *   rr_ratio >= 2.0 → tp_hit (win),  pnl_r = +rr_ratio
 *   rr_ratio >= 1.5 → breakeven,     pnl_r = 0
 *   rr_ratio <  1.5 → sl_hit (loss), pnl_r = -1.0
 *
 * @param {Object} proposal
 * @param {Object} opts  - reserved for future use
 * @returns {Object}
 */
export function simulateForexTrade(proposal, opts = {}) {
  const { entry_price, stop_loss, take_profit } = proposal;

  if (entry_price == null || stop_loss == null || take_profit == null) {
    throw new Error(
      `simulateForexTrade: proposal ${proposal.proposal_id} missing entry_price, stop_loss, or take_profit`
    );
  }

  const risk = Math.abs(entry_price - stop_loss);
  const reward = Math.abs(take_profit - entry_price);

  if (risk === 0) {
    throw new Error(
      `simulateForexTrade: proposal ${proposal.proposal_id} has zero risk (entry_price === stop_loss)`
    );
  }

  const rr_ratio = parseFloat((reward / risk).toFixed(4));

  // Simulated bars to resolution — proportional to R:R (purely illustrative)
  const bars_to_resolution = Math.round(20 + rr_ratio * 10);

  let replay_outcome;
  let pnl_r;
  let hit_take_profit = false;
  let hit_stop_loss = false;
  let expired = false;

  if (rr_ratio >= 2.0) {
    replay_outcome = "tp_hit";
    pnl_r = parseFloat(rr_ratio.toFixed(4));
    hit_take_profit = true;
  } else if (rr_ratio >= 1.5) {
    replay_outcome = "breakeven";
    pnl_r = 0;
  } else {
    replay_outcome = "sl_hit";
    pnl_r = -1.0;
    hit_stop_loss = true;
  }

  // pnl_pct: percentage gain/loss relative to entry
  const pnl_pct =
    replay_outcome === "tp_hit"
      ? parseFloat(((reward / entry_price) * 100).toFixed(4))
      : replay_outcome === "sl_hit"
      ? parseFloat(((-risk / entry_price) * 100).toFixed(4))
      : 0;

  return {
    entry_price,
    stop_loss,
    take_profit,
    rr_ratio,
    replay_outcome,
    pnl_r,
    pnl_pct,
    hit_take_profit,
    hit_stop_loss,
    expired,
    bars_to_resolution,
    simulation_mode: "static_rr",
    note: "Simulated based on R:R. No live price data used.",
  };
}
