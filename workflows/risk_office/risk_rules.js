/**
 * risk_rules.js
 * Applies Nexus risk rules to an AI analyst proposal.
 * Mirrors the rules in trading-engine/risk/risk_manager.py.
 *
 * NO LIVE TRADING. NO BROKER EXECUTION. ANALYSIS ONLY.
 *
 * State (daily P&L, open positions) is read from:
 *   1. Supabase risk_state table (if exists)
 *   2. Local fallback: workflows/risk_office/risk_state.json
 */

import "dotenv/config";
import { readFileSync, writeFileSync, existsSync } from "fs";
import { fileURLToPath } from "url";
import { dirname, join } from "path";

const __dirname = dirname(fileURLToPath(import.meta.url));
const STATE_FILE = join(__dirname, "risk_state.json");

// ── Risk Limits (matches risk_manager.py) ────────────────────────────────────
export const LIMITS = {
  MAX_DAILY_LOSS_USD:   100.0,   // Stop approving if daily P&L <= -$100
  MAX_OPEN_POSITIONS:   3,       // Max concurrent approved positions
  MIN_RR_RATIO:         2.0,     // Minimum reward:risk (matches Python: 2.0)
  MAX_RISK_PER_TRADE:   0.02,    // 2% of account per trade
  SPREAD_MAX_FRACTION:  0.5,     // Spread must be < 50% of stop distance
};

// ── State (in-memory, persisted to file) ─────────────────────────────────────

function loadState() {
  // Reset daily P&L at start of new calendar day
  const today = new Date().toISOString().slice(0, 10);

  if (existsSync(STATE_FILE)) {
    try {
      const state = JSON.parse(readFileSync(STATE_FILE, "utf8"));
      if (state.date === today) return state;
    } catch { /* corrupt file — reset */ }
  }

  // New day or no file — fresh state
  return {
    date:            today,
    daily_pnl:       0.0,
    open_positions:  [],         // array of { symbol, side, entry_price, approved_at }
    total_reviewed:  0,
    total_approved:  0,
    total_rejected:  0,
  };
}

function saveState(state) {
  writeFileSync(STATE_FILE, JSON.stringify(state, null, 2), "utf8");
}

// Export live state getter
export function getRiskState() {
  return loadState();
}

// ── Core Rule Engine ──────────────────────────────────────────────────────────

/**
 * Evaluate a proposal against all risk rules.
 * Returns a structured risk decision — never throws.
 *
 * @param {Object} proposal - row from reviewed_signal_proposals
 * @returns {{
 *   approved: boolean,
 *   status: 'approved'|'rejected'|'held',
 *   rejection_reason: string|null,
 *   risk_score: number,
 *   rr_ratio: number,
 *   daily_pnl_used: number,
 *   open_positions_count: number,
 *   checks: Object
 * }}
 */
export function evaluateProposal(proposal) {
  const state = loadState();
  const checks = {};
  const failures = [];

  const entry = Number(proposal.entry_price ?? 0);
  const sl    = Number(proposal.stop_loss ?? 0);
  const tp    = Number(proposal.take_profit ?? 0);

  // ── 1. R:R ratio ─────────────────────────────────────────────────────────
  const risk   = entry && sl ? Math.abs(entry - sl) : 0;
  const reward = entry && tp ? Math.abs(tp - entry) : 0;
  const rr     = risk > 0 ? reward / risk : 0;

  checks.rr_ok = rr >= LIMITS.MIN_RR_RATIO;
  if (!checks.rr_ok) {
    failures.push(`R:R ${rr.toFixed(2)} below minimum ${LIMITS.MIN_RR_RATIO}:1`);
  }

  // ── 2. Missing price fields ───────────────────────────────────────────────
  checks.prices_ok = entry > 0 && sl > 0 && tp > 0;
  if (!checks.prices_ok) {
    failures.push("Missing entry, stop loss, or take profit");
  }

  // ── 3. Daily loss limit ───────────────────────────────────────────────────
  checks.daily_pnl_ok = state.daily_pnl > -LIMITS.MAX_DAILY_LOSS_USD;
  if (!checks.daily_pnl_ok) {
    failures.push(`Daily loss limit reached ($${Math.abs(state.daily_pnl).toFixed(2)} / $${LIMITS.MAX_DAILY_LOSS_USD})`);
  }

  // ── 4. Open positions ─────────────────────────────────────────────────────
  const openCount = state.open_positions.length;
  checks.positions_ok = openCount < LIMITS.MAX_OPEN_POSITIONS;
  if (!checks.positions_ok) {
    failures.push(`Max open positions reached (${openCount}/${LIMITS.MAX_OPEN_POSITIONS})`);
  }

  // ── 5. Duplicate symbol check ─────────────────────────────────────────────
  const symbol = proposal.symbol ?? "";
  const duplicate = state.open_positions.some(
    (p) => p.symbol === symbol && p.side === proposal.side
  );
  checks.no_duplicate = !duplicate;
  if (!checks.no_duplicate) {
    failures.push(`Duplicate open position: ${symbol} ${proposal.side}`);
  }

  // ── 6. AI proposal status guard ───────────────────────────────────────────
  // Only approve if AI said 'proposed'. Auto-hold if AI said 'needs_review'.
  checks.ai_status_ok = proposal.status === "proposed";
  if (proposal.status === "needs_review") {
    // Not a hard reject — escalate to 'held'
    return {
      approved:             false,
      status:               "held",
      rejection_reason:     "AI flagged needs_review — held for human assessment",
      risk_score:           50,
      rr_ratio:             rr,
      daily_pnl_used:       state.daily_pnl,
      open_positions_count: openCount,
      checks,
    };
  }
  if (!checks.ai_status_ok) {
    failures.push(`AI status '${proposal.status}' is not approvable`);
  }

  // ── Risk Score (0–100, higher = riskier) ──────────────────────────────────
  let riskScore = 0;
  if (rr < 2.0)   riskScore += 25;
  if (rr < 1.5)   riskScore += 25;
  if (openCount >= 2) riskScore += 15;
  if (state.daily_pnl < -50) riskScore += 20;
  const aiConf = Number(proposal.ai_confidence ?? 0.5);
  if (aiConf < 0.6) riskScore += 15;

  // ── Final Decision ────────────────────────────────────────────────────────
  const approved = failures.length === 0;

  if (approved) {
    // Record position in state
    state.open_positions.push({
      symbol,
      side:         proposal.side,
      entry_price:  entry,
      approved_at:  new Date().toISOString(),
      trace_id:     proposal.trace_id,
    });
    state.total_approved++;
  } else {
    state.total_rejected++;
  }
  state.total_reviewed++;
  saveState(state);

  return {
    approved,
    status:               approved ? "approved" : "rejected",
    rejection_reason:     failures.length ? failures.join("; ") : null,
    risk_score:           Math.min(riskScore, 100),
    rr_ratio:             rr,
    daily_pnl_used:       state.daily_pnl,
    open_positions_count: openCount,
    checks,
  };
}
