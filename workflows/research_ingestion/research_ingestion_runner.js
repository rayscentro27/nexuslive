import "dotenv/config";
import { readFileSync, existsSync } from "fs";
import { randomUUID } from "crypto";
import { processSources, processTranscript } from "./youtube_researcher.js";
import { loadDropIns } from "./transcript_extractor.js";
import { classifyTopic } from "./topic_classifier.js";
import { extractClaims } from "./claim_extractor.js";
import { writeArtifact, writeClaims } from "./artifact_writer.js";
import { enrichMemory } from "./memory_enricher.js";
import { enrichGraph } from "./graph_enricher.js";
import { writeClusters } from "./cluster_writer.js";
import { sendIngestionAlert } from "./telegram_research_ingestion_alert.js";

// ── SAFETY GUARD ──────────────────────────────────────────────────────────────
// NEXUS BRAIN RESEARCH INGESTION LAB — RESEARCH / INGESTION ONLY.
// NO LIVE TRADING. NO BROKER EXECUTION. NO ORDER PLACEMENT.
// ─────────────────────────────────────────────────────────────────────────────
console.log("[runner] Nexus Brain Research Ingestion Lab — RESEARCH ONLY MODE");

const VALID_TOPICS = [
  "trading",
  "credit_repair",
  "grant_research",
  "business_opportunities",
  "crm_automation",
  "general_business_intelligence",
];

function parseArgs(argv) {
  const args = argv.slice(2);

  const flag = (name) => args.includes(name);
  const value = (name) => {
    const i = args.indexOf(name);
    return i !== -1 ? args[i + 1] : null;
  };

  const positional = args.find(a => !a.startsWith("-")) ?? null;
  const mode = args.find(a => a.startsWith("--")) ?? "--help";

  return {
    mode,
    sourcesFile: value("--sources") ?? "sample_sources.json",
    topic: value("--topic") ?? null,
    limit: parseInt(value("--limit") ?? "10", 10),
    transcriptFile: value("--transcript") ?? null,
  };
}

function loadSources(filePath) {
  if (!existsSync(filePath)) {
    console.error(`[runner] Sources file not found: ${filePath}`);
    process.exit(1);
  }
  try {
    const parsed = JSON.parse(readFileSync(filePath, "utf8"));
    return parsed.sources ?? [];
  } catch (err) {
    console.error(`[runner] Failed to parse ${filePath}: ${err.message}`);
    process.exit(1);
  }
}

function printSummary(results) {
  const totalClaims = results.reduce((n, r) => n + (r.extracted.claims?.length ?? 0), 0);
  const totalOpps = results.reduce((n, r) => n + (r.extracted.opportunity_notes?.length ?? 0), 0);
  const totalWarns = results.reduce((n, r) => n + (r.extracted.risk_warnings?.length ?? 0), 0);
  const topics = [...new Set(results.map(r => r.classification.topic))];

  console.log("\n[runner] ─── Ingestion Summary ────────────────────────────────");
  console.log(`[runner]  Transcripts ingested : ${results.length}`);
  console.log(`[runner]  Total claims         : ${totalClaims}`);
  console.log(`[runner]  Opportunities        : ${totalOpps}`);
  console.log(`[runner]  Risk warnings        : ${totalWarns}`);
  console.log(`[runner]  Topics covered       : ${topics.join(", ") || "none"}`);
  console.log("[runner] ────────────────────────────────────────────────────────\n");
}

function printHelp() {
  console.log(`
Nexus Brain Research Ingestion Lab — Runner

SAFETY: Research ingestion only. No live trading. No broker execution.

Usage:
  node research_ingestion_runner.js --once --sources sample_sources.json
    Run full ingestion from source seed file.

  node research_ingestion_runner.js --topic credit_repair --sources sample_sources.json
    Filter to a specific topic domain.

  node research_ingestion_runner.js --topic grant_research --sources sample_sources.json
  node research_ingestion_runner.js --topic business_opportunities --sources sample_sources.json
  node research_ingestion_runner.js --topic trading --sources sample_sources.json
  node research_ingestion_runner.js --topic crm_automation --sources sample_sources.json

  node research_ingestion_runner.js --transcript /path/to/transcript.txt --topic credit_repair
    Ingest a single local transcript file.

  node research_ingestion_runner.js --drop-ins [--topic credit_repair]
    Ingest all files from the drop_in/ folder.

Supported topics:
  trading | credit_repair | grant_research | business_opportunities
  crm_automation | general_business_intelligence

drop_in/ folder:
  Place .txt, .md, or .vtt files in workflows/research_ingestion/drop_in/
  Name files with topic prefix: credit_repair_my_notes.txt
  Files are ingested as local transcripts.
`);
}

// ── MAIN ──────────────────────────────────────────────────────────────────────

const { mode, sourcesFile, topic, limit, transcriptFile } = parseArgs(process.argv);

// Validate topic if provided
if (topic && !VALID_TOPICS.includes(topic)) {
  console.error(`[runner] Unknown topic: "${topic}". Valid topics: ${VALID_TOPICS.join(", ")}`);
  process.exit(1);
}

// ── --help ────────────────────────────────────────────────────────────────────
if (mode === "--help" || mode === "-h") {
  printHelp();
  process.exit(0);
}

// ── --transcript: ingest single file ─────────────────────────────────────────
if (mode === "--transcript") {
  if (!transcriptFile) {
    console.error("[runner] --transcript requires a file path: --transcript /path/to/file.txt");
    process.exit(1);
  }

  if (!existsSync(transcriptFile)) {
    console.error(`[runner] Transcript file not found: ${transcriptFile}`);
    process.exit(1);
  }

  const transcriptText = readFileSync(transcriptFile, "utf8");
  const effectiveTopic = topic ?? "general_business_intelligence";

  const transcriptObj = {
    source_name: transcriptFile.split("/").pop(),
    source_type: "local_file",
    source_url: transcriptFile,
    topic: effectiveTopic,
    title: transcriptFile.split("/").pop().replace(/\.[^.]+$/, "").replace(/_/g, " "),
    transcript_text: transcriptText,
    published_at: new Date().toISOString().slice(0, 10),
    trace_id: randomUUID(),
  };

  console.log(`[runner] Ingesting transcript: "${transcriptObj.title}" (topic=${effectiveTopic})`);

  const classification = classifyTopic(transcriptText);
  if (topic) classification.topic = topic;

  const extracted = await extractClaims(transcriptObj, classification.topic);
  await writeArtifact(transcriptObj, classification, extracted);
  await writeClaims(transcriptObj, classification, extracted);
  await enrichMemory(transcriptObj, classification, extracted);
  await enrichGraph(transcriptObj, classification, extracted);

  const results = [{ transcript: transcriptObj, classification, extracted }];
  await writeClusters(results);
  await sendIngestionAlert(results);

  printSummary(results);
  console.log("[runner] Manual transcript ingestion complete.");
  process.exit(0);
}

// ── --drop-ins: ingest all files from drop_in/ ───────────────────────────────
if (mode === "--drop-ins") {
  const dropIns = loadDropIns(topic ?? null);

  if (!dropIns.length) {
    console.log("[runner] No transcript files found in drop_in/.");
    console.log("[runner] Place .txt / .md / .vtt files in workflows/research_ingestion/drop_in/");
    console.log("[runner] Name them with topic prefix: credit_repair_my_notes.txt");
    process.exit(0);
  }

  console.log(`[runner] Found ${dropIns.length} drop-in transcript(s).`);

  const results = [];
  for (const transcriptObj of dropIns) {
    const classification = classifyTopic(transcriptObj.transcript_text);
    if (topic) classification.topic = topic;

    const extracted = await extractClaims(transcriptObj, classification.topic);
    await writeArtifact(transcriptObj, classification, extracted);
    await writeClaims(transcriptObj, classification, extracted);
    await enrichMemory(transcriptObj, classification, extracted);
    await enrichGraph(transcriptObj, classification, extracted);
    results.push({ transcript: transcriptObj, classification, extracted });
  }

  await writeClusters(results);
  await sendIngestionAlert(results);
  printSummary(results);
  console.log("[runner] Drop-in ingestion complete.");
  process.exit(0);
}

// ── --once / --topic: ingest from source seed file ───────────────────────────
if (mode === "--once" || mode === "--topic") {
  const sources = loadSources(sourcesFile);

  if (!sources.length) {
    console.error(`[runner] No sources found in ${sourcesFile}.`);
    process.exit(1);
  }

  const topicLabel = topic ? `topic="${topic}"` : "all topics";
  console.log(`[runner] Loaded ${sources.length} source(s) from ${sourcesFile} (${topicLabel}).`);

  const results = await processSources(sources, topic ?? null);

  if (!results.length) {
    console.log("[runner] No transcripts were successfully ingested.");
    console.log("[runner] This is normal if yt-dlp is not installed or sources have no auto-captions.");
    console.log("[runner] Use --drop-ins or --transcript to ingest local files instead.");
  } else {
    await writeClusters(results);
    await sendIngestionAlert(results);
    printSummary(results);
  }

  console.log("[runner] Source ingestion complete.");
  process.exit(0);
}

// ── Unknown mode ──────────────────────────────────────────────────────────────
console.error(`[runner] Unknown mode: "${mode}". Run with --help for usage.`);
printHelp();
process.exit(1);
