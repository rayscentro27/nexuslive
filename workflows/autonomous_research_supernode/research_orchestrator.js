#!/usr/bin/env node
import "dotenv/config";
import { randomUUID } from "crypto";

// ── SAFETY GUARD ──────────────────────────────────────────────────────────────
// RESEARCH ONLY. No trading, no broker connections.
// ─────────────────────────────────────────────────────────────────────────────

import { loadSources, filterByLane, filterByTopic, LANE } from "./source_registry.js";
import { extractFromYoutube, loadDropIns } from "./transcript_extractor.js";
import { loadManualJson, loadManualFolder } from "./manual_source_loader.js";
import { classifyTopic } from "./topic_classifier.js";
import { extractClaims } from "./claim_extractor.js";
import { writeArtifact, writeClaims } from "./artifact_writer.js";
import { enrichMemory } from "./memory_enricher.js";
import { enrichGraph } from "./graph_enricher.js";
import { writeClusters } from "./cluster_writer.js";

import { runGrantResearch } from "./comet_grant_researcher.js";
import { runTradingResearch } from "./comet_trading_researcher.js";
import { runBusinessResearch } from "./comet_business_researcher.js";
import { runCreditPolicyResearch } from "./comet_credit_policy_researcher.js";
import { runCompetitorResearch } from "./comet_competitor_researcher.js";

import { generateBrief, writeBrief, formatBriefForLog } from "./brief_generator.js";
import { generateNextActions, formatNextActionsForLog } from "./next_action_generator.js";
import { sendResearchAlert, sendRunSummaryAlert } from "./telegram_research_alert.js";
import { sendTopicBriefAlert } from "./telegram_brief_alert.js";

// ── CLI args ──────────────────────────────────────────────────────────────────
const args = process.argv.slice(2);
const FLAG_ONCE = args.includes("--once");
const FLAG_MANUAL = args.includes("--manual");
const FLAG_BROWSER = args.includes("--browser");
const FLAG_TRANSCRIPT = args.includes("--transcript");
const TOPIC_FILTER = (() => {
  const idx = args.indexOf("--topic");
  return idx !== -1 ? args[idx + 1] : null;
})();
const SOURCE_FILE = (() => {
  const idx = args.indexOf("--sources");
  return idx !== -1 ? args[idx + 1] : "sample_sources.json";
})();
const MANUAL_FILE = (() => {
  const idx = args.indexOf("--manual-file");
  return idx !== -1 ? args[idx + 1] : null;
})();
const LIMIT = (() => {
  const idx = args.indexOf("--limit");
  return idx !== -1 ? parseInt(args[idx + 1], 10) : null;
})();

// ── Lane routing map for browser sources ─────────────────────────────────────
const BROWSER_RESEARCHERS = {
  grant_research: runGrantResearch,
  business_opportunities: runBusinessResearch,
  credit_repair: runCreditPolicyResearch,
  crm_automation: runCompetitorResearch,
  trading: runTradingResearch,
};

// ── Process a single source through the full pipeline ────────────────────────

/**
 * Process one source through the Nexus Research pipeline.
 *
 * @param {Object} source - { name, url, topic, lane, type, ... }
 * @returns {Promise<{ok: boolean, brief: Object|null, lane: string}>}
 */
async function processSource(source) {
  const trace_id = randomUUID();
  const lane = source.lane;

  const sourceName = source.name ?? source.source_name ?? "unknown";
  console.log(`\n[orchestrator] ── Processing: ${sourceName} (${lane}) ──`);

  try {
    let normalizedSource;

    // ── STEP 1: Acquire content based on lane ────────────────────────────────
    if (lane === LANE.TRANSCRIPT) {
      // YouTube / local file transcript extraction
      const results = await extractFromYoutube(source);
      if (!results?.length) {
        console.warn(`[orchestrator] Transcript unavailable for: ${sourceName} — skipping.`);
        return { ok: false, brief: null, lane };
      }
      // Process the first transcript from this source
      normalizedSource = { ...results[0], trace_id };
    } else if (lane === LANE.MANUAL) {
      // Already loaded by loadManualSources — source IS the normalized payload
      normalizedSource = {
        source_name: source.source_name ?? source.name ?? "Manual Source",
        source_type: source.type ?? "manual",
        source_url: source.url ?? source.source_url ?? null,
        topic: source.topic,
        title: source.title ?? source.source_name ?? source.name ?? "Untitled",
        content_text: source.content_text ?? source.text ?? "",
        published_at: source.published_at ?? null,
        trace_id,
      };
    } else if (lane === LANE.BROWSER) {
      // Comet browser research
      const researcher = BROWSER_RESEARCHERS[source.topic];
      if (!researcher) {
        console.warn(`[orchestrator] No browser researcher for topic: ${source.topic} — skipping.`);
        return { ok: false, brief: null, lane };
      }
      const cometResult = await researcher(source, trace_id);
      normalizedSource = {
        source_name: cometResult.source_name,
        source_type: cometResult.source_type,
        source_url: cometResult.source_url,
        topic: cometResult.topic,
        title: cometResult.title,
        content_text: cometResult.content_text,
        extracted_fields: cometResult.extracted_fields ?? {},
        trace_id: cometResult.trace_id ?? trace_id,
        adapter_mode: cometResult.adapter_mode,
      };
    } else {
      console.warn(`[orchestrator] Unknown lane: ${lane} — skipping.`);
      return { ok: false, brief: null, lane };
    }

    if (!normalizedSource.content_text?.trim()) {
      console.warn(`[orchestrator] Empty content for: ${sourceName} — skipping.`);
      return { ok: false, brief: null, lane };
    }

    // ── STEP 2: Classify topic ───────────────────────────────────────────────
    const transcript_compat = {
      ...normalizedSource,
      transcript_text: normalizedSource.content_text,
    };

    const classification = classifyTopic(normalizedSource.content_text ?? "");
    // Allow source-declared topic to override low-confidence classification
    if (source.topic && classification.confidence < 0.4) {
      classification.topic = source.topic;
    }

    console.log(`[orchestrator] Classified: ${classification.topic} (conf=${classification.confidence.toFixed(2)}) | subthemes: ${classification.subthemes.join(", ")}`);

    // ── STEP 3: Extract claims ───────────────────────────────────────────────
    const extracted = await extractClaims(transcript_compat, classification);

    // ── STEP 4: Write to Supabase ────────────────────────────────────────────
    await writeArtifact(transcript_compat, classification, extracted);
    await writeClaims(transcript_compat, classification, extracted);
    await enrichMemory(transcript_compat, classification, extracted);
    await enrichGraph(transcript_compat, classification, extracted);
    await writeClusters(transcript_compat, classification, extracted);

    // ── STEP 5: Generate brief and next actions ──────────────────────────────
    const brief = generateBrief(transcript_compat, classification, extracted, lane);
    await writeBrief(brief);

    const nextActions = generateNextActions(brief);

    // Log to console
    console.log(formatBriefForLog(brief));
    console.log(formatNextActionsForLog(nextActions, classification.topic));

    // ── STEP 6: Telegram per-source alert ───────────────────────────────────
    await sendResearchAlert(brief, nextActions);

    return { ok: true, brief, lane };

  } catch (err) {
    console.error(`[orchestrator] Error processing ${sourceName}: ${err.message}`);
    if (process.env.DEBUG) console.error(err.stack);
    return { ok: false, brief: null, lane };
  }
}

// ── Main run function ─────────────────────────────────────────────────────────

async function run() {
  const startTime = Date.now();
  console.log(`\n╔══════════════════════════════════════════════════════════════╗`);
  console.log(`║     NEXUS AUTONOMOUS RESEARCH SUPERNODE                      ║`);
  console.log(`║     RESEARCH ONLY — NO TRADING — NO BROKER CONNECTIONS       ║`);
  console.log(`╚══════════════════════════════════════════════════════════════╝`);
  console.log(`[orchestrator] Start: ${new Date().toISOString()}`);
  if (TOPIC_FILTER) console.log(`[orchestrator] Topic filter: ${TOPIC_FILTER}`);

  // ── Determine active lane flags ──────────────────────────────────────────
  // Default (no flags): run all lanes
  const runAll = !FLAG_MANUAL && !FLAG_BROWSER && !FLAG_TRANSCRIPT;
  const runTranscript = runAll || FLAG_TRANSCRIPT;
  const runManual = runAll || FLAG_MANUAL;
  const runBrowser = runAll || FLAG_BROWSER;

  const allSources = [];

  // ── Load transcript/YouTube sources ─────────────────────────────────────
  if (runTranscript) {
    try {
      let transcriptSources = filterByLane(loadSources(SOURCE_FILE), LANE.TRANSCRIPT);
      if (TOPIC_FILTER) transcriptSources = filterByTopic(transcriptSources, TOPIC_FILTER);
      console.log(`[orchestrator] Transcript sources loaded: ${transcriptSources.length}`);
      allSources.push(...transcriptSources);
    } catch (err) {
      console.warn(`[orchestrator] Could not load transcript sources: ${err.message}`);
    }
  }

  // ── Load manual sources ──────────────────────────────────────────────────
  if (runManual) {
    try {
      const manualFile = MANUAL_FILE ?? "sample_manual_research.json";
      const manualSources = [
        ...loadManualJson(manualFile, TOPIC_FILTER),
        ...loadManualFolder(TOPIC_FILTER),
      ];
      console.log(`[orchestrator] Manual sources loaded: ${manualSources.length}`);
      // Tag each manual source with lane
      allSources.push(...manualSources.map((s) => ({ ...s, lane: LANE.MANUAL })));
    } catch (err) {
      console.warn(`[orchestrator] Could not load manual sources: ${err.message}`);
    }
  }

  // ── Load browser/website sources ─────────────────────────────────────────
  if (runBrowser) {
    try {
      let browserSources = filterByLane(loadSources(SOURCE_FILE), LANE.BROWSER);
      if (TOPIC_FILTER) browserSources = filterByTopic(browserSources, TOPIC_FILTER);
      console.log(`[orchestrator] Browser sources loaded: ${browserSources.length}`);
      allSources.push(...browserSources);
    } catch (err) {
      console.warn(`[orchestrator] Could not load browser sources: ${err.message}`);
    }
  }

  if (!allSources.length) {
    console.warn(`[orchestrator] No sources to process. Check source files and lane flags.`);
    process.exit(0);
  }

  // Apply global limit
  const sourcesToProcess = LIMIT ? allSources.slice(0, LIMIT) : allSources;
  console.log(`[orchestrator] Processing ${sourcesToProcess.length} source(s) total.`);

  // ── Process all sources ──────────────────────────────────────────────────
  const results = [];
  for (const source of sourcesToProcess) {
    const result = await processSource(source);
    results.push(result);
  }

  // ── Aggregate stats ──────────────────────────────────────────────────────
  const successCount = results.filter((r) => r.ok).length;
  const failCount = results.filter((r) => !r.ok).length;
  const briefs = results.filter((r) => r.ok && r.brief).map((r) => r.brief);

  const laneCounts = results.reduce((acc, r) => {
    if (r.ok) acc[r.lane] = (acc[r.lane] ?? 0) + 1;
    return acc;
  }, {});

  // ── Topic brief digest (group by topic) ─────────────────────────────────
  if (briefs.length > 1) {
    const briefsByTopic = briefs.reduce((acc, b) => {
      if (!acc[b.topic]) acc[b.topic] = [];
      acc[b.topic].push(b);
      return acc;
    }, {});

    for (const [topic, topicBriefs] of Object.entries(briefsByTopic)) {
      if (topicBriefs.length >= 2) {
        await sendTopicBriefAlert(topicBriefs, topic);
      }
    }
  }

  // ── Run summary alert ────────────────────────────────────────────────────
  const elapsedMs = Date.now() - startTime;
  await sendRunSummaryAlert({
    topic: TOPIC_FILTER ?? "all",
    totalSources: sourcesToProcess.length,
    successCount,
    failCount,
    lanes: laneCounts,
    elapsedMs,
  });

  // ── Final console summary ────────────────────────────────────────────────
  console.log(`\n╔══════════════════════════════════════════════════════════════╗`);
  console.log(`║  RUN COMPLETE                                                 ║`);
  console.log(`╟──────────────────────────────────────────────────────────────╢`);
  console.log(`║  Sources processed : ${sourcesToProcess.length}`);
  console.log(`║  Success           : ${successCount}`);
  console.log(`║  Failed            : ${failCount}`);
  console.log(`║  Elapsed           : ${(elapsedMs / 1000).toFixed(1)}s`);
  console.log(`╚══════════════════════════════════════════════════════════════╝`);

  if (failCount > 0 && successCount === 0) {
    process.exit(1);
  }
}

// ── Entry point ──────────────────────────────────────────────────────────────
run().catch((err) => {
  console.error(`[orchestrator] Fatal error: ${err.message}`);
  if (process.env.DEBUG) console.error(err.stack);
  process.exit(1);
});
