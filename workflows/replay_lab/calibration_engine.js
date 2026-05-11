import "dotenv/config";

const SUPABASE_URL = process.env.SUPABASE_URL;
const SUPABASE_KEY = process.env.SUPABASE_KEY;
const SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;

const CONFIDENCE_BANDS = [
  { label: "0.0-0.3", min: 0.0,  max: 0.3,  expected_win_rate: 0.15 },
  { label: "0.3-0.5", min: 0.3,  max: 0.5,  expected_win_rate: 0.40 },
  { label: "0.5-0.7", min: 0.5,  max: 0.7,  expected_win_rate: 0.60 },
  { label: "0.7-0.9", min: 0.7,  max: 0.9,  expected_win_rate: 0.80 },
  { label: "0.9-1.0", min: 0.9,  max: 1.01, expected_win_rate: 0.95 },
];

function readHeaders() {
  return {
    "Content-Type": "application/json",
    "apikey": SUPABASE_KEY,
    "Authorization": `Bearer ${SUPABASE_KEY}`,
  };
}

function writeHeaders() {
  return {
    "Content-Type": "application/json",
    "apikey": SUPABASE_SERVICE_ROLE_KEY,
    "Authorization": `Bearer ${SUPABASE_SERVICE_ROLE_KEY}`,
    "Prefer": "resolution=merge-duplicates,return=representation",
  };
}

/**
 * Fetches replay_results and joins with reviewed_signal_proposals by id.
 * Groups into confidence bands and computes calibration metrics.
 * Upserts results to confidence_calibration table.
 *
 * @returns {Promise<Array>}
 */
export async function computeCalibration() {
  // Fetch all replay_results
  const resultsRes = await fetch(
    `${SUPABASE_URL}/rest/v1/replay_results?select=proposal_id,replay_outcome,pnl_r`,
    { headers: readHeaders() }
  );

  if (!resultsRes.ok) {
    const err = await resultsRes.text();
    throw new Error(`computeCalibration: error fetching replay_results: ${err}`);
  }

  const results = await resultsRes.json();

  if (!results.length) {
    console.log("[calibration] No replay results found — nothing to calibrate.");
    return [];
  }

  // Fetch ai_confidence for each proposal referenced in results
  const proposalIds = [...new Set(results.map((r) => r.proposal_id))];

  // Supabase IN filter: proposal_id=in.(id1,id2,...)
  const idList = proposalIds.map((id) => `"${id}"`).join(",");
  const proposalsRes = await fetch(
    `${SUPABASE_URL}/rest/v1/reviewed_signal_proposals` +
      `?id=in.(${idList})&select=id,ai_confidence`,
    { headers: readHeaders() }
  );

  if (!proposalsRes.ok) {
    const err = await proposalsRes.text();
    throw new Error(`computeCalibration: error fetching proposals: ${err}`);
  }

  const proposals = await proposalsRes.json();
  const confidenceMap = Object.fromEntries(
    proposals.map((p) => [p.id, p.ai_confidence ?? 0.5])
  );

  // Classify each result into a confidence band
  const bandAccumulators = CONFIDENCE_BANDS.map((b) => ({
    ...b,
    samples: 0,
    wins: 0,
    losses: 0,
  }));

  for (const result of results) {
    const conf = confidenceMap[result.proposal_id] ?? 0.5;
    const band = bandAccumulators.find((b) => conf >= b.min && conf < b.max);
    if (!band) continue;

    band.samples += 1;
    const isWin =
      result.replay_outcome === "tp_hit" || result.replay_outcome === "win";
    const isLoss =
      result.replay_outcome === "sl_hit" || result.replay_outcome === "loss";
    if (isWin) band.wins += 1;
    if (isLoss) band.losses += 1;
  }

  const calibration = bandAccumulators
    .filter((b) => b.samples > 0)
    .map((b) => {
      const actual_win_rate = parseFloat((b.wins / b.samples).toFixed(4));
      const calibration_gap = parseFloat(
        (actual_win_rate - b.expected_win_rate).toFixed(4)
      );
      return {
        confidence_band: b.label,
        samples: b.samples,
        wins: b.wins,
        losses: b.losses,
        actual_win_rate,
        expected_win_rate: b.expected_win_rate,
        calibration_gap,
        computed_at: new Date().toISOString(),
      };
    });

  // Upsert to confidence_calibration table
  if (calibration.length > 0) {
    const upsertRes = await fetch(
      `${SUPABASE_URL}/rest/v1/confidence_calibration?on_conflict=confidence_band`,
      {
        method: "POST",
        headers: writeHeaders(),
        body: JSON.stringify(calibration),
      }
    );

    if (!upsertRes.ok) {
      const err = await upsertRes.text();
      throw new Error(`computeCalibration: upsert error: ${err}`);
    }
  }

  return calibration;
}

/**
 * Converts a calibration array into a human-readable summary string.
 *
 * @param {Array} calibrationArray
 * @returns {string}
 */
export function interpretCalibration(calibrationArray) {
  if (!calibrationArray || calibrationArray.length === 0) {
    return "No calibration data available.";
  }

  const lines = ["=== Calibration Summary ==="];

  for (const band of calibrationArray) {
    const gap = band.calibration_gap;
    const gapPct = (Math.abs(gap) * 100).toFixed(1);
    const direction = gap > 0.05 ? "underconfident" : gap < -0.05 ? "overconfident" : "well-calibrated";

    const expectedPct = (band.expected_win_rate * 100).toFixed(0);
    const actualPct = (band.actual_win_rate * 100).toFixed(0);

    lines.push(
      `Band ${band.confidence_band}: AI is ${direction} ` +
        `(expected ${expectedPct}%, actual ${actualPct}%, gap ${gap > 0 ? "+" : ""}${gapPct}%) ` +
        `[${band.samples} samples]`
    );
  }

  // Find biggest gap
  const sorted = [...calibrationArray].sort(
    (a, b) => Math.abs(b.calibration_gap) - Math.abs(a.calibration_gap)
  );
  const worst = sorted[0];
  if (worst && Math.abs(worst.calibration_gap) > 0.05) {
    const dir = worst.calibration_gap < 0 ? "overconfident" : "underconfident";
    const expectedPct = (worst.expected_win_rate * 100).toFixed(0);
    const actualPct = (worst.actual_win_rate * 100).toFixed(0);
    lines.push(
      `\nLargest gap: AI is ${dir} at ${worst.confidence_band} band ` +
        `(expected ${expectedPct}%, actual ${actualPct}%).`
    );
  }

  return lines.join("\n");
}
