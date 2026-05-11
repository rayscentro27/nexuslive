import "dotenv/config";
import { randomUUID } from "crypto";

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
    Prefer: "return=representation",
  };
}

async function supabasePost(table, rows) {
  if (!SUPABASE_URL || !SUPABASE_SERVICE_ROLE_KEY) {
    console.warn(`[artifact-writer] Missing Supabase credentials — skipping write to ${table}.`);
    return [];
  }

  try {
    const res = await fetch(`${SUPABASE_URL}/rest/v1/${table}`, {
      method: "POST",
      headers: serviceHeaders(),
      body: JSON.stringify(rows),
    });

    if (!res.ok) {
      const body = await res.text();
      // Only treat as "table missing" when PostgREST returns 404 or the Postgres
      // error code is 42P01 (undefined_table) — not on constraint violations which
      // also contain the word "relation" in their message.
      const parsed = (() => { try { return JSON.parse(body); } catch { return {}; } })();
      if (res.status === 404 || parsed.code === "42P01") {
        console.warn(`[artifact-writer] Table "${table}" not found. Run SQL doc to create it.`);
        return [];
      }
      console.warn(`[artifact-writer] Write to ${table} failed (${res.status}): ${body.slice(0, 200)}`);
      return [];
    }

    const result = await res.json();
    return Array.isArray(result) ? result : [result];
  } catch (err) {
    console.warn(`[artifact-writer] ${table} write error: ${err.message}`);
    return [];
  }
}

/**
 * Write a research artifact to the research_artifacts table.
 *
 * @param {Object} transcript - normalized transcript payload
 * @param {Object} classification - { topic, subthemes, confidence }
 * @param {Object} extracted - { summary, claims, key_points, action_items, risk_warnings, opportunity_notes }
 * @returns {Promise<Object>} saved artifact row
 */
export async function writeArtifact(transcript, classification, extracted) {
  const artifact = {
    // Map to both new (source) and existing (channel_name) column names
    source: transcript.source_name,
    channel_name: transcript.source_name,
    source_type: transcript.source_type ?? "youtube_channel",
    source_url: transcript.source_url ?? null,
    topic: classification.topic,
    subtheme: classification.subthemes?.[0] ?? null,
    subthemes: classification.subthemes ?? [],
    tags: classification.subthemes ?? [],     // existing column
    title: transcript.title,
    summary: extracted.summary ?? null,
    content: (transcript.transcript_text ?? "").slice(0, 4000),
    key_points: extracted.key_points ?? [],
    action_items: extracted.action_items ?? [],
    risk_warnings: extracted.risk_warnings ?? [],
    opportunity_notes: extracted.opportunity_notes ?? [],
    confidence: parseFloat((classification.confidence ?? 0.5).toFixed(3)),
    published_at: transcript.published_at ?? null,
    trace_id: transcript.trace_id ?? randomUUID(),
    created_at: new Date().toISOString(),
  };

  const rows = await supabasePost("research_artifacts", [artifact]);
  console.log(`[artifact-writer] Artifact written: "${transcript.title}" (topic=${classification.topic})`);
  return rows[0] ?? artifact;
}

/**
 * Write structured claims to the research_claims table.
 *
 * @param {Object} transcript - normalized transcript payload
 * @param {Object} classification - { topic, subthemes, confidence }
 * @param {Object} extracted - { claims, ... }
 * @returns {Promise<Array>} saved claim rows
 */
export async function writeClaims(transcript, classification, extracted) {
  const rawClaims = extracted.claims ?? [];

  if (!rawClaims.length) {
    console.log(`[artifact-writer] No claims to write for: "${transcript.title}"`);
    return [];
  }

  const claims = rawClaims.map(c => ({
    artifact_id: null,            // existing column — nullable FK
    source: transcript.source_name,
    topic: c.topic ?? classification.topic,
    subtheme: c.subtheme ?? classification.subthemes?.[0] ?? null,
    claim_text: c.claim_text,
    claim_type: c.claim_type ?? "strategy",
    confidence: parseFloat((c.confidence ?? 0.5).toFixed(3)),
    trace_id: transcript.trace_id ?? randomUUID(),
    created_at: new Date().toISOString(),
  }));

  const rows = await supabasePost("research_claims", claims);
  console.log(`[artifact-writer] ${rows.length > 0 ? rows.length : claims.length} claim(s) written for: "${transcript.title}"`);
  return rows;
}
