import "dotenv/config";

// ── SAFETY GUARD ──────────────────────────────────────────────────────────────
// RESEARCH ONLY. No trading, no broker connections.
// ─────────────────────────────────────────────────────────────────────────────

const SUPABASE_URL = process.env.SUPABASE_URL;
const SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;

function serviceHeaders() {
  return {
    apikey: SUPABASE_SERVICE_ROLE_KEY,
    Authorization: `Bearer ${SUPABASE_SERVICE_ROLE_KEY}`,
    "Content-Type": "application/json",
    Prefer: "return=minimal",
  };
}

/**
 * Build relationship edges from classification and extracted data.
 *
 * Relationship types created:
 *   topic → subtheme       (contains)
 *   topic → source         (sourced_from)
 *   claim_type → topic     (extracted_from)
 *   workflow → topic       (extracted_from)
 *   opportunity → topic    (extracted_from)
 *
 * Examples produced:
 *   credit_repair → dispute_letters          (contains)
 *   grant_research → small_business_grants   (contains)
 *   business_opportunities → ai_automation_agency (contains)
 *   trading → TraderNick                     (sourced_from)
 *   opportunity → business_opportunities     (extracted_from)
 */
function buildRelationships(transcript, classification, extracted) {
  const { topic, subthemes } = classification;
  const now = new Date().toISOString();
  const relationships = [];

  // topic → subtheme (contains)
  for (const subtheme of subthemes ?? []) {
    relationships.push({
      from_node: topic,
      from_type: "topic",
      to_node: subtheme,
      to_type: "subtheme",
      relation: "contains",
      source: transcript.source_name,
      trace_id: transcript.trace_id,
      created_at: now,
    });
  }

  // topic → source (sourced_from)
  relationships.push({
    from_node: topic,
    from_type: "topic",
    to_node: transcript.source_name,
    to_type: "source",
    relation: "sourced_from",
    source: transcript.source_name,
    trace_id: transcript.trace_id,
    created_at: now,
  });

  // claim_type → topic (extracted_from)
  const claimTypes = [
    ...new Set((extracted.claims ?? []).map(c => c.claim_type).filter(Boolean)),
  ];
  for (const claimType of claimTypes) {
    relationships.push({
      from_node: claimType,
      from_type: "claim_type",
      to_node: topic,
      to_type: "topic",
      relation: "extracted_from",
      source: transcript.source_name,
      trace_id: transcript.trace_id,
      created_at: now,
    });
  }

  // subtheme → source (sourced_from) — for high-confidence subtheme detection
  for (const subtheme of (subthemes ?? []).slice(0, 3)) {
    relationships.push({
      from_node: subtheme,
      from_type: "subtheme",
      to_node: transcript.source_name,
      to_type: "source",
      relation: "sourced_from",
      source: transcript.source_name,
      trace_id: transcript.trace_id,
      created_at: now,
    });
  }

  return relationships;
}

/**
 * Write graph relationships to research_relationships table.
 * Gracefully skips if the table doesn't exist yet.
 *
 * @param {Object} transcript
 * @param {Object} classification
 * @param {Object} extracted
 */
export async function enrichGraph(transcript, classification, extracted) {
  if (!SUPABASE_URL || !SUPABASE_SERVICE_ROLE_KEY) {
    console.warn("[graph] Missing Supabase credentials — skipping graph enrichment.");
    return;
  }

  const relationships = buildRelationships(transcript, classification, extracted);

  if (!relationships.length) {
    console.log(`[graph] No relationships to write for "${transcript.title}".`);
    return;
  }

  try {
    const res = await fetch(`${SUPABASE_URL}/rest/v1/research_relationships`, {
      method: "POST",
      headers: serviceHeaders(),
      body: JSON.stringify(relationships),
    });

    if (!res.ok) {
      const body = await res.text();
      if (body.includes("does not exist") || body.includes("relation")) {
        console.warn(`[graph] Table "research_relationships" not found. Run docs/research_relationships.sql to create it.`);
        return;
      }
      console.warn(`[graph] Write failed (${res.status}): ${body.slice(0, 120)}`);
      return;
    }

    console.log(`[graph] Wrote ${relationships.length} relationship(s) for "${transcript.title}" (topic=${classification.topic}).`);

  } catch (err) {
    console.warn(`[graph] Error: ${err.message}`);
  }
}
