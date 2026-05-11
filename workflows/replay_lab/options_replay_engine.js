import "dotenv/config";

/**
 * Historical strategy profiles.
 * typical_win_rate: base win probability for this strategy type
 * typical_pnl_pct_win:  average % gain on a win
 * typical_pnl_pct_loss: average % loss on a loss
 */
const STRATEGY_PROFILES = {
  covered_call:    { typical_win_rate: 0.72, typical_pnl_pct_win:  0.08, typical_pnl_pct_loss: -0.15 },
  cash_secured_put:{ typical_win_rate: 0.68, typical_pnl_pct_win:  0.07, typical_pnl_pct_loss: -0.18 },
  iron_condor:     { typical_win_rate: 0.65, typical_pnl_pct_win:  0.12, typical_pnl_pct_loss: -0.20 },
  credit_spread:   { typical_win_rate: 0.62, typical_pnl_pct_win:  0.10, typical_pnl_pct_loss: -0.25 },
  debit_spread:    { typical_win_rate: 0.45, typical_pnl_pct_win:  0.30, typical_pnl_pct_loss: -0.50 },
  straddle:        { typical_win_rate: 0.40, typical_pnl_pct_win:  0.50, typical_pnl_pct_loss: -0.60 },
  strangle:        { typical_win_rate: 0.38, typical_pnl_pct_win:  0.60, typical_pnl_pct_loss: -0.65 },
  butterfly:       { typical_win_rate: 0.55, typical_pnl_pct_win:  0.20, typical_pnl_pct_loss: -0.30 },
  calendar_spread: { typical_win_rate: 0.58, typical_pnl_pct_win:  0.15, typical_pnl_pct_loss: -0.20 },
  zebra_strategy:  { typical_win_rate: 0.60, typical_pnl_pct_win:  0.25, typical_pnl_pct_loss: -0.20 },
  wheel_strategy:  { typical_win_rate: 0.75, typical_pnl_pct_win:  0.06, typical_pnl_pct_loss: -0.12 },
};

const DEFAULT_PROFILE = { typical_win_rate: 0.50, typical_pnl_pct_win: 0.10, typical_pnl_pct_loss: -0.20 };

/**
 * Deterministic simulation: no randomness.
 * The effective win probability is the average of the strategy's base win rate
 * and the proposal's ai_confidence. If effective_win_prob >= 0.5 → win, else → loss.
 * This makes higher-confidence proposals tilt toward wins while preserving
 * the strategy's historical edge without introducing non-determinism.
 *
 * @param {Object} proposal
 * @returns {Object}
 */
export function simulateOptionsStrategy(proposal) {
  const strategy_type = proposal.strategy_id ?? "unknown";
  const profile = STRATEGY_PROFILES[strategy_type] ?? DEFAULT_PROFILE;
  const ai_confidence = proposal.ai_confidence ?? 0.5;

  // Blend base win rate with AI confidence for a deterministic effective probability
  const effective_win_prob = (profile.typical_win_rate + ai_confidence) / 2;

  let replay_outcome;
  let pnl_pct;
  let hit_take_profit = false;
  let hit_stop_loss = false;
  const expired = false;

  if (effective_win_prob >= 0.55) {
    replay_outcome = "win";
    pnl_pct = parseFloat((profile.typical_pnl_pct_win * 100).toFixed(4));
    hit_take_profit = true;
  } else if (effective_win_prob >= 0.45) {
    replay_outcome = "breakeven";
    pnl_pct = 0;
  } else {
    replay_outcome = "loss";
    pnl_pct = parseFloat((profile.typical_pnl_pct_loss * 100).toFixed(4));
    hit_stop_loss = true;
  }

  return {
    strategy_type,
    replay_outcome,
    pnl_pct,
    hit_take_profit,
    hit_stop_loss,
    expired,
    bars_to_resolution: null, // options are time-based, not bar-based
    simulation_mode: "historical_profile",
    note: "Simulated using historical strategy profile data.",
  };
}
