import "dotenv/config";

// ── SAFETY GUARD ──────────────────────────────────────────────────────────────
// RESEARCH ONLY. No trading, no broker connections.
// ─────────────────────────────────────────────────────────────────────────────

const SUPABASE_URL = process.env.SUPABASE_URL;
const SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;
const HF_TOKEN = process.env.HF_TOKEN;
const HF_MODEL = process.env.HF_MODEL ?? "sentence-transformers/all-MiniLM-L6-v2";

// Rate-limit HF calls — free tier throttles quickly
const EMBED_DELAY_MS = 600;

function sleep(ms) {
  return new Promise(r => setTimeout(r, ms));
}

/**
 * Fetch a vector embedding from HuggingFace Inference API.
 * Returns null if HF_TOKEN is not set or the call fails.
 * The existing research table uses REAL[] embeddings (384-dim, all-MiniLM-L6-v2).
 *
 * @param {string} text - text to embed (truncated to 512 chars)
 * @returns {Promise<number[]|null>}
 */
async function getEmbedding(text) {
  if (!HF_TOKEN) return null;

  try {
    const res = await fetch(
      `https://api-inference.huggingface.co/models/${HF_MODEL}`,
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${HF_TOKEN}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ inputs: text.slice(0, 512) }),
      }
    );

    if (!res.ok) {
      // 503 = model loading, 429 = rate limited — both are transient
      if ([404, 429, 503].includes(res.status)) {
        console.log(`[memory] HF API ${res.status} — skipping embedding for this chunk.`);
      } else {
        console.warn(`[memory] HF API ${res.status} — skipping embedding for this chunk.`);
      }
      return null;
    }

    const result = await res.json();

    // HF sentence-transformers returns [[...]] for batch or [...] for single
    if (Array.isArray(result[0])) return result[0];
    if (Array.isArray(result)) return result;
    return null;

  } catch (err) {
    console.log(`[memory] Embedding call failed: ${err.message}`);
    return null;
  }
}

/**
 * Write a chunk to the existing Supabase `research` table.
 * This table is used by the existing research-engine pipeline and
 * supports semantic search via stored embeddings.
 *
 * Fields: source, title, content, embedding (REAL[])
 */
async function writeToResearchTable(source, title, content, embedding) {
  if (!SUPABASE_URL || !SUPABASE_SERVICE_ROLE_KEY) return;

  const row = {
    source,
    title: title.slice(0, 255),
    content: content.slice(0, 2000),
    ...(embedding ? { embedding } : {}),
    created_at: new Date().toISOString(),
  };

  try {
    const res = await fetch(`${SUPABASE_URL}/rest/v1/research`, {
      method: "POST",
      headers: {
        apikey: SUPABASE_SERVICE_ROLE_KEY,
        Authorization: `Bearer ${SUPABASE_SERVICE_ROLE_KEY}`,
        "Content-Type": "application/json",
        Prefer: "return=minimal",
      },
      body: JSON.stringify(row),
    });

    if (!res.ok) {
      const body = await res.text();
      // Ignore duplicate title errors (idempotent behavior)
      if (body.includes("duplicate") || body.includes("unique")) return;
      console.warn(`[memory] research table write failed: ${body.slice(0, 100)}`);
    }
  } catch (err) {
    console.warn(`[memory] research table error: ${err.message}`);
  }
}

/**
 * Enrich vector memory from a research artifact.
 *
 * Writes chunks to the existing `research` table:
 *   - [topic_summary] chunk from the AI-generated summary
 *   - [key_point] chunks from top key points
 *   - [claim] chunks from top extracted claims
 *
 * If HF_TOKEN is set, attaches embeddings. If not, writes text-only
 * (embeddings column will be NULL — semantic search degrades gracefully).
 *
 * @param {Object} transcript - { source_name, title }
 * @param {Object} classification - { topic }
 * @param {Object} extracted - { summary, key_points, claims }
 */
export async function enrichMemory(transcript, classification, extracted) {
  if (!SUPABASE_URL || !SUPABASE_SERVICE_ROLE_KEY) {
    console.log("[memory] Missing Supabase credentials — skipping memory enrichment.");
    return;
  }

  const { topic } = classification;
  const source = transcript.source_name;

  // Build chunks to store in vector memory
  const chunks = [
    // Primary summary chunk
    {
      title: `[${topic}_summary] ${transcript.title}`,
      content: extracted.summary ?? transcript.title,
    },
    // Key points (up to 3)
    ...(extracted.key_points ?? []).slice(0, 3).map(kp => ({
      title: `[key_point] ${transcript.title}`,
      content: kp,
    })),
    // High-confidence claims (up to 4)
    ...(extracted.claims ?? [])
      .filter(c => (c.confidence ?? 0) >= 0.6)
      .slice(0, 4)
      .map(c => ({
        title: `[${c.topic ?? topic}_claim] ${transcript.title}`,
        content: c.claim_text,
      })),
  ];

  let written = 0;

  for (const chunk of chunks) {
    const embedding = await getEmbedding(chunk.content);
    await writeToResearchTable(source, chunk.title, chunk.content, embedding);
    written++;
    if (HF_TOKEN) await sleep(EMBED_DELAY_MS); // respect HF rate limits
  }

  const embNote = HF_TOKEN
    ? `with embeddings (${HF_MODEL})`
    : `text-only (set HF_TOKEN for vector embeddings)`;

  console.log(`[memory] Enriched ${written} chunk(s) for "${transcript.title}" — ${embNote}.`);
}
