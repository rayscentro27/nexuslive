/**
 * risk_engine.js
 * Pure rule-based risk scorer. Runs locally — no AI call required.
 * Optionally augmented by risk_runner.js which may add AI risk notes.
 *
 * Score starts at 100. Penalties subtract.
 * ≥70 → approved | 40–69 → manual_review | <40 → blocked
 *
 * NO LIVE TRADING. NO BROKER EXECUTION.
 */

import "dotenv/config";
import { readFileSync, writeFileSync, existsSync } from "fs";
import { fileURLToPath } from "url";
import { dirname, join }  from "path";

const __dirname    = dirname(fileURLToPath(import.meta.url));
const STATE_FILE   = join(__dirname, "risk_state.json");
const SPREAD_LIMIT = Number(process.env.SPREAD_THRESHOLD ?? 0.0003);

// ── Known strategy set ────────────────────────────────────────────────────────
const KNOWN_STRATEGIES = new Set([
  "london_breakout", "ny_open", "asian_session", "scalp", "swing",
  "trend_follow", "mean_reversion", "momentum", "breakout", "reversal",
  "covered_call", "cash_secured_put", "iron_condor", "credit_spread",
  "debit_spread", "zebra_strategy", "stock_repair_strategy",
  "bull_call_spread", "bear_put_spread", "straddle", "strangle",
  "butterfly", "calendar_spread", "diagonal_spread", "wheel_strategy",
]);

// ── Penalties ─────────────────────────────────────────────────────────────────
const PENALTY = {
  poor_rr:          30,
  low_confidence:   25,
  high_spread:      15,
  unknown_strategy: 20,
  duplicate_signal: 15,
  conflict:         20,
  missing_sl:       30,
  low_rr_options:   15,
};

// ── Daily state ───────────────────────────────────────────────────────────────
function loadState() {
  const today = new Date().toISOString().slice(0, 10);
  if (existsSync(STATE_FILE)) {
    try {
      const s = JSON.parse(readFileSync(STATE_FILE, "utf8"));
      if (s.date === today) return s;
    } catch { /* reset */ }
  }
  return {
    date:            today,
    daily_pnl:       0,
    open_positions:  [],  // [{ symbol, side, strategy_id, approved_at }]
    total_evaluated: 0,
    total_approved:  0,
    total_blocked:   0,
    total_review:    0,
  };
}

function saveState(state) {
  writeFileSync(STATE_FILE, JSON.stringify(state, null, 2), "utf8");
}

export function getRiskState() { return loadState(); }

// ── Core scorer ───────────────────────────────────────────────────────────────

export function scoreProposal(proposal, snapshot) {
  let score = 100;
  const flags = {};

  const isOptions = proposal.asset_type === "options";
  const entry     = Number(proposal.entry_price  ?? 0);
  const sl        = Number(proposal.stop_loss    ?? 0);
  const tp        = Number(proposal.take_profit  ?? 0);
  const conf      = Number(proposal.ai_confidence ?? 0);
  const stratId   = (proposal.strategy_id ?? "").toLowerCase().replace(/\s+/g, "_");

  // ── FOREX rules ───────────────────────────────────────────────────────────

  if (!isOptions) {
    // Missing stop loss
    flags.missing_sl = !sl || sl === 0;
    if (flags.missing_sl) score -= PENALTY.missing_sl;

    // R:R check
    const risk   = entry && sl ? Math.abs(entry - sl) : 0;
    const reward = entry && tp ? Math.abs(tp   - entry) : 0;
    const rr     = risk > 0 ? reward / risk : 0;
    flags.poor_rr = rr < 2.0 && !flags.missing_sl;
    if (flags.poor_rr) score -= PENALTY.poor_rr;

    // Spread check
    const spread = snapshot ? Number(snapshot.spread ?? 0) : 0;
    flags.high_spread = spread > SPREAD_LIMIT;
    if (flags.high_spread) score -= PENALTY.high_spread;
  } else {
    // OPTIONS: no traditional SL required, but poor R:R note
    flags.missing_sl = false;
    flags.poor_rr    = false;

    // Simple options R:R sanity
    const hasEntry = entry > 0;
    flags.low_rr_options = !hasEntry;
    if (flags.low_rr_options) score -= PENALTY.low_rr_options;

    // Spread N/A for options (different concept)
    flags.high_spread = false;
  }

  // ── Common rules ──────────────────────────────────────────────────────────

  // Confidence
  flags.low_confidence = conf < 0.60;
  if (flags.low_confidence) score -= PENALTY.low_confidence;

  // Unknown strategy
  flags.unknown_strategy = !stratId || !KNOWN_STRATEGIES.has(stratId);
  if (flags.unknown_strategy) score -= PENALTY.unknown_strategy;

  // Duplicate / conflict (check state)
  const state = loadState();
  const dup = state.open_positions.some(
    (p) => p.symbol === proposal.symbol && p.side === proposal.side
  );
  flags.duplicate_signal = dup;
  if (flags.duplicate_signal) score -= PENALTY.duplicate_signal;

  const conflict = state.open_positions.some(
    (p) => p.symbol === proposal.symbol && p.side !== proposal.side
  );
  flags.conflict = conflict;
  if (flags.conflict) score -= PENALTY.conflict;

  // Clamp
  score = Math.max(0, Math.min(100, score));

  // Decision
  const decision = score >= 70 ? "approved" : score >= 40 ? "manual_review" : "blocked";

  // Update state
  state.total_evaluated++;
  if (decision === "approved")      state.total_approved++;
  else if (decision === "blocked")  state.total_blocked++;
  else                              state.total_review++;

  if (decision !== "blocked") {
    state.open_positions.push({
      symbol:      proposal.symbol,
      side:        proposal.side,
      strategy_id: proposal.strategy_id,
      asset_type:  proposal.asset_type,
      approved_at: new Date().toISOString(),
    });
  }
  saveState(state);

  // R:R string for notes
  const riskDist   = entry && sl ? Math.abs(entry - sl) : 0;
  const rewardDist = entry && tp ? Math.abs(tp - entry) : 0;
  const rrStr      = riskDist > 0 ? `${(rewardDist / riskDist).toFixed(2)}:1` : "N/A";

  const flagSummary = Object.entries(flags)
    .filter(([, v]) => v)
    .map(([k]) => k.replace(/_/g, " "))
    .join(", ") || "none";

  const riskNotes = [
    `Score: ${score}/100.`,
    `Decision: ${decision.toUpperCase()}.`,
    `R:R: ${rrStr}.`,
    `Confidence: ${Math.round(conf * 100)}%.`,
    `Flags: ${flagSummary}.`,
  ].join(" ");

  return { score, flags, decision, riskNotes };
}
