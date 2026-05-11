import "dotenv/config";

// ── SAFETY GUARD ──────────────────────────────────────────────────────────────
// This module is RESEARCH ONLY. Links hypotheses to existing strategy records.
// No trading, no broker connections.
// ─────────────────────────────────────────────────────────────────────────────

const SUPABASE_URL = process.env.SUPABASE_URL;
const SUPABASE_KEY = process.env.SUPABASE_KEY;

function readHeaders() {
  return {
    apikey: SUPABASE_KEY,
    Authorization: `Bearer ${SUPABASE_KEY}`,
  };
}

/**
 * Fetches strategy_library records for validation.
 * @returns {Promise<Array>}
 */
async function fetchStrategyLibrary() {
  if (!SUPABASE_URL || !SUPABASE_KEY) {
    console.warn("[linker] SUPABASE credentials not set — skipping strategy library fetch.");
    return [];
  }

  const url =
    `${SUPABASE_URL}/rest/v1/strategy_library` +
    `?select=id,strategy_id,strategy_name,market`;

  try {
    const res = await fetch(url, { headers: readHeaders() });
    if (!res.ok) {
      const body = await res.text();
      console.warn(`[linker] strategy_library fetch failed (${res.status}): ${body}`);
      return [];
    }
    return res.json();
  } catch (err) {
    console.warn(`[linker] strategy_library fetch error: ${err.message}`);
    return [];
  }
}

/**
 * Validates and links hypotheses to existing strategies.
 * @param {Array} hypotheses
 * @param {Object} inputs - Output from pollResearchInputs()
 * @returns {Promise<Array>} Hypotheses with validated linked_strategy_id
 */
export async function linkHypothesesToStrategies(hypotheses, inputs) {
  const { replayResults = [], optimizations = [] } = inputs;

  console.log(`[linker] Linking ${hypotheses.length} hypotheses to strategies...`);

  const strategyLibrary = await fetchStrategyLibrary();

  // Build lookup sets for fast validation
  const libraryIds = new Set(strategyLibrary.map((s) => s.strategy_id).filter(Boolean));
  const replayIds = new Set(replayResults.map((r) => r.strategy_id).filter(Boolean));
  const optimizationIds = new Set(optimizations.map((o) => o.strategy_id).filter(Boolean));

  // Combined known strategy IDs
  const knownIds = new Set([...libraryIds, ...replayIds, ...optimizationIds]);

  const linked = hypotheses.map((h) => {
    const candidateId = h.linked_strategy_id;

    if (!candidateId) {
      // No link — check if we can infer one from the title
      return {
        ...h,
        linked_strategy_id: null,
        supporting_evidence: [
          ...(h.supporting_evidence ?? []),
          "No existing strategy link — candidate for new strategy",
        ],
      };
    }

    if (knownIds.has(candidateId)) {
      // Valid link
      const libraryEntry = strategyLibrary.find((s) => s.strategy_id === candidateId);
      const note = libraryEntry
        ? `Linked to strategy library: ${libraryEntry.strategy_name ?? candidateId} (${libraryEntry.market ?? "unknown"})`
        : `Strategy ID ${candidateId} found in replay/optimization data`;
      return {
        ...h,
        supporting_evidence: [...(h.supporting_evidence ?? []), note],
      };
    }

    // Link not found — clear it
    console.warn(
      `[linker] Strategy ID "${candidateId}" not found in library, replay, or optimizations — clearing link.`
    );
    return {
      ...h,
      linked_strategy_id: null,
      supporting_evidence: [
        ...(h.supporting_evidence ?? []),
        `Strategy ID "${candidateId}" not found in known strategies — link cleared. Candidate for new strategy.`,
      ],
    };
  });

  const linkedCount = linked.filter((h) => h.linked_strategy_id !== null).length;
  console.log(
    `[linker] Linking complete — ${linkedCount} linked, ${linked.length - linkedCount} unlinked.`
  );

  return linked;
}
