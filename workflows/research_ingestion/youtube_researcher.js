import "dotenv/config";
import { extractFromYoutube, loadDropIns } from "./transcript_extractor.js";
import { classifyTopic } from "./topic_classifier.js";
import { extractClaims } from "./claim_extractor.js";
import { writeArtifact, writeClaims } from "./artifact_writer.js";
import { enrichMemory } from "./memory_enricher.js";
import { enrichGraph } from "./graph_enricher.js";

// ── SAFETY GUARD ──────────────────────────────────────────────────────────────
// RESEARCH / INGESTION ONLY. No trading, no broker connections.
// This module coordinates transcript ingestion from YouTube and local files.
// ─────────────────────────────────────────────────────────────────────────────

const MAX_SOURCES = parseInt(process.env.MAX_RESEARCH_SOURCES ?? "10", 10);

/**
 * Process a single transcript through the full ingestion pipeline:
 *   classify → extract claims → write artifact + claims → enrich memory → enrich graph
 *
 * @param {Object} transcript - normalized transcript payload
 * @param {string|null} topicOverride - force a specific topic (from source seed)
 * @returns {Promise<{transcript, classification, extracted}|null>}
 */
export async function processTranscript(transcript, topicOverride = null) {
  try {
    // 1. Classify topic and subthemes
    const classification = classifyTopic(transcript.transcript_text);
    if (topicOverride) classification.topic = topicOverride;

    console.log(
      `[researcher] Classified: topic=${classification.topic}, ` +
      `subthemes=[${classification.subthemes.join(", ")}], ` +
      `confidence=${classification.confidence}`
    );

    // 2. Extract claims via OpenClaw (or fallback)
    let extracted;
    try {
      extracted = await extractClaims(transcript, classification.topic);
    } catch (err) {
      console.warn(`[researcher] Claim extraction error: ${err.message} — using empty fallback.`);
      extracted = {
        summary: transcript.title,
        claims: [],
        key_points: [],
        action_items: [],
        risk_warnings: [],
        opportunity_notes: [],
      };
    }

    // 3. Write research artifact and claims to Supabase
    await writeArtifact(transcript, classification, extracted);
    await writeClaims(transcript, classification, extracted);

    // 4. Enrich vector memory (existing research table)
    await enrichMemory(transcript, classification, extracted);

    // 5. Enrich graph relationships
    await enrichGraph(transcript, classification, extracted);

    return { transcript, classification, extracted };

  } catch (err) {
    console.warn(`[researcher] Failed to process "${transcript.title}": ${err.message}`);
    return null;
  }
}

/**
 * Process a list of source seeds — extract transcripts and run the full pipeline.
 *
 * @param {Array} sources - array of source seed objects from sample_sources.json
 * @param {string|null} topicFilter - only process sources matching this topic
 * @returns {Promise<Array>} array of successful ingestion results
 */
export async function processSources(sources, topicFilter = null) {
  const filtered = topicFilter
    ? sources.filter(s => s.topic === topicFilter)
    : sources;

  const limited = filtered.slice(0, MAX_SOURCES);

  console.log(
    `[researcher] Processing ${limited.length} source(s)` +
    (topicFilter ? ` filtered to topic="${topicFilter}"` : "") +
    "..."
  );

  const results = [];

  for (const source of limited) {
    console.log(`\n[researcher] Source: ${source.name} (${source.topic}) → ${source.url}`);

    let transcripts = [];

    if (source.type === "youtube_channel" || source.type === "youtube_video") {
      transcripts = await extractFromYoutube(source);
    } else if (source.type === "local_file") {
      // local_file sources point directly to a file path in source.url
      transcripts = loadDropIns(topicFilter);
    } else {
      console.warn(`[researcher] Unknown source type "${source.type}" — skipping.`);
      continue;
    }

    if (!transcripts.length) {
      console.log(`[researcher] No transcripts extracted from ${source.name}.`);
      continue;
    }

    for (const transcript of transcripts) {
      console.log(`\n[researcher] ── Processing: "${transcript.title}"`);
      const result = await processTranscript(transcript, source.topic);
      if (result) results.push(result);
    }
  }

  return results;
}
