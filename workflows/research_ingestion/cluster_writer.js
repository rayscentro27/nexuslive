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
 * Group a batch of ingestion results into topic+subtheme clusters and write
 * them to the existing research_clusters table (compatible with Phase 6
 * Research Desk format: cluster_name, theme, source_count, summary,
 * key_terms JSONB, confidence).
 *
 * @param {Array<{transcript, classification, extracted}>} batchResults
 */
export async function writeClusters(batchResults) {
  if (!SUPABASE_URL || !SUPABASE_SERVICE_ROLE_KEY) {
    console.warn("[clusters] Missing Supabase credentials — skipping cluster write.");
    return;
  }

  if (!batchResults.length) {
    console.log("[clusters] No results to cluster.");
    return;
  }

  // Group by topic + primary subtheme
  const clusterMap = new Map();

  for (const { transcript, classification, extracted } of batchResults) {
    const { topic, subthemes, confidence } = classification;
    const subtheme = subthemes?.[0] ?? "general";
    const key = `${topic}::${subtheme}`;

    if (!clusterMap.has(key)) {
      clusterMap.set(key, {
        cluster_name: `${topic}__${subtheme}`,
        theme: topic,
        source_count: 0,
        sources: [],
        key_terms: [],
        confidences: [],
        created_at: new Date().toISOString(),
      });
    }

    const cluster = clusterMap.get(key);
    cluster.source_count++;
    cluster.sources.push(transcript.source_name);
    cluster.confidences.push(confidence ?? 0.5);

    // Harvest key terms from claim texts
    for (const claim of extracted.claims ?? []) {
      const words = (claim.claim_text ?? "")
        .toLowerCase()
        .split(/\W+/)
        .filter(w => w.length > 5);
      cluster.key_terms.push(...words.slice(0, 5));
    }
  }

  const now = new Date().toISOString();
  const clusters = [...clusterMap.values()].map(c => {
    const avgConf = c.confidences.length
      ? parseFloat((c.confidences.reduce((a, b) => a + b, 0) / c.confidences.length).toFixed(2))
      : 0.5;

    const uniqueTerms = [...new Set(c.key_terms)].slice(0, 20);
    const sourceList = [...new Set(c.sources)].join(", ");

    return {
      cluster_name: c.cluster_name,
      theme: c.theme,
      source_count: c.source_count,
      summary: `Ingestion cluster: topic=${c.theme}, subtheme=${c.cluster_name.split("__")[1] ?? "general"}. Sources: ${sourceList}.`,
      key_terms: uniqueTerms,
      confidence: avgConf,
      created_at: now,
    };
  });

  if (!clusters.length) {
    console.log("[clusters] No clusters produced.");
    return;
  }

  try {
    const res = await fetch(
      `${SUPABASE_URL}/rest/v1/research_clusters?on_conflict=cluster_name`,
      {
        method: "POST",
        headers: {
          ...serviceHeaders(),
          Prefer: "resolution=merge-duplicates,return=minimal",
        },
        body: JSON.stringify(clusters),
      }
    );

    if (!res.ok) {
      const body = await res.text();
      if (body.includes("does not exist") || body.includes("relation")) {
        console.warn(`[clusters] Table "research_clusters" not found. Run docs/research_clusters.sql to create it.`);
        return;
      }
      // If no unique constraint, fall back to plain insert
      if (body.includes("42P10") || body.includes("no unique")) {
        const res2 = await fetch(`${SUPABASE_URL}/rest/v1/research_clusters`, {
          method: "POST",
          headers: serviceHeaders(),
          body: JSON.stringify(clusters),
        });
        if (!res2.ok) {
          const b2 = await res2.text();
          console.warn(`[clusters] Write failed (${res2.status}): ${b2.slice(0, 120)}`);
          return;
        }
      } else {
        console.warn(`[clusters] Write failed (${res.status}): ${body.slice(0, 120)}`);
        return;
      }
    }

    console.log(`[clusters] Wrote ${clusters.length} cluster(s): ${clusters.map(c => c.cluster_name).join(", ")}`);

  } catch (err) {
    console.warn(`[clusters] Error: ${err.message}`);
  }
}
