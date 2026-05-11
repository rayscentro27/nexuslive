/**
 * risk_runner.js
 * Orchestrates the risk evaluation step for a single proposal.
 * Runs the rule engine and returns a structured risk result.
 */

import { scoreProposal } from "./risk_engine.js";

/**
 * Evaluate a proposal through the risk engine.
 *
 * @param {Object} proposal - reviewed_signal_proposals row
 * @param {Object|null} snapshot - market_price_snapshots row (for spread check)
 * @returns {{ score, flags, decision, riskNotes, trace_id }}
 */
export function runRiskEngine(proposal, snapshot) {
  const { score, flags, decision, riskNotes } = scoreProposal(proposal, snapshot);

  console.log(`[risk] ${(proposal.symbol ?? "").replace("_", "")} ${(proposal.side ?? "").toUpperCase()} — score: ${score}/100 → ${decision.toUpperCase()}`);
  if (Object.values(flags).some(Boolean)) {
    const active = Object.entries(flags).filter(([, v]) => v).map(([k]) => k);
    console.log(`[risk] Flags: ${active.join(", ")}`);
  }

  return { score, flags, decision, riskNotes, trace_id: proposal.trace_id };
}
