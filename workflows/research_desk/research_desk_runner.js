import "dotenv/config";
import { pollResearchInputs } from "./research_poll.js";
import { clusterResearch } from "./research_clusterer.js";
import { generateHypotheses } from "./hypothesis_generator.js";
import { rankHypotheses } from "./hypothesis_ranker.js";
import { linkHypothesesToStrategies } from "./strategy_linker.js";
import { detectCoverageGaps } from "./coverage_gap_detector.js";
import { generateBriefs } from "./research_brief_generator.js";
import { sendResearchAlert } from "./telegram_research_alert.js";

// ── SAFETY GUARD ─────────────────────────────────────────────────────────────
// This system is RESEARCH ONLY. It reads from Supabase, generates hypotheses,
// and writes research artifacts. It does NOT place trades, connect to brokers,
// or execute orders of any kind.
// ─────────────────────────────────────────────────────────────────────────────
console.log("[runner] Nexus Research Desk — RESEARCH ONLY MODE");

const SUPABASE_URL = process.env.SUPABASE_URL;
const SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;

function serviceHeaders() {
  return {
    apikey: SUPABASE_SERVICE_ROLE_KEY,
    Authorization: `Bearer ${SUPABASE_SERVICE_ROLE_KEY}`,
    "Content-Type": "application/json",
    Prefer: "resolution=merge-duplicates,return=representation",
  };
}

function parseArgs(argv) {
  const args = argv.slice(2);
  const mode = args[0] ?? null;
  const limitIdx = args.indexOf("--limit");
  const limit = limitIdx !== -1 ? parseInt(args[limitIdx + 1], 10) || 20 : 20;
  return { mode, limit };
}

// ── Supabase write helpers ────────────────────────────────────────────────────

async function writeRows(table, rows, conflictCol) {
  if (!SUPABASE_URL || !SUPABASE_SERVICE_ROLE_KEY) {
    console.warn(`[runner] Service role key not set — skipping write to ${table}.`);
    return;
  }
  if (!rows || rows.length === 0) {
    console.log(`[runner] No rows to write for ${table}.`);
    return;
  }

  const url = conflictCol
    ? `${SUPABASE_URL}/rest/v1/${table}?on_conflict=${conflictCol}`
    : `${SUPABASE_URL}/rest/v1/${table}`;

  try {
    const res = await fetch(url, {
      method: "POST",
      headers: serviceHeaders(),
      body: JSON.stringify(rows),
    });

    if (!res.ok) {
      const body = await res.text();
      // Gracefully handle missing tables
      if (res.status === 404 || body.includes("does not exist") || body.includes("relation")) {
        console.warn(`[runner] Table "${table}" does not exist yet — skipping. (Create via SQL docs.)`);
        return;
      }
      console.warn(`[runner] Write to ${table} failed (${res.status}): ${body}`);
      return;
    }

    console.log(`[runner] Wrote ${rows.length} row(s) to ${table}.`);
  } catch (err) {
    console.warn(`[runner] Write to ${table} error: ${err.message}`);
  }
}

// ── Full pipeline ─────────────────────────────────────────────────────────────

async function runFullPipeline(limit) {
  // 1. Poll
  const inputs = await pollResearchInputs(limit);

  // 2. Cluster
  const clusters = clusterResearch(inputs);

  // 3. Write clusters (append-only, no unique constraint required)
  await writeRows("research_clusters", clusters);

  // 4. Generate hypotheses
  let hypotheses = generateHypotheses(clusters, inputs);

  // 5. Rank
  hypotheses = rankHypotheses(hypotheses, inputs);

  // 6. Link to strategies
  hypotheses = await linkHypothesesToStrategies(hypotheses, inputs);

  // 7. Write hypotheses (append-only, no unique constraint required)
  await writeRows("research_hypotheses", hypotheses);

  // 8. Detect gaps
  const gaps = detectCoverageGaps(inputs, hypotheses);

  // 9. Write gaps — severity column is numeric in DB (low=1, medium=2, high=3)
  const SEVERITY_NUM = { low: 1, medium: 2, high: 3 };
  const gapsForDb = gaps.map((g) => ({
    ...g,
    severity: SEVERITY_NUM[g.severity] ?? 1,
  }));
  await writeRows("coverage_gaps", gapsForDb);

  // 10. Generate briefs
  const briefs = generateBriefs(hypotheses, gaps, inputs);

  // 11. Write briefs
  await writeRows("research_briefs", briefs);

  return { inputs, clusters, hypotheses, gaps, briefs };
}

// ── Print helpers ─────────────────────────────────────────────────────────────

function printSummary(inputs, clusters, hypotheses, gaps, briefs) {
  console.log("\n[runner] ─── Research Desk Summary ────────────────────────────");
  console.log(`[runner]  Artifacts polled : ${inputs.artifacts.length}`);
  console.log(`[runner]  Claims polled    : ${inputs.claims.length}`);
  console.log(`[runner]  Clusters         : ${clusters.length}`);
  console.log(`[runner]  Hypotheses       : ${hypotheses.length}`);
  console.log(`[runner]  Gaps detected    : ${gaps.length}`);
  console.log(`[runner]  Briefs generated : ${briefs.length}`);
  console.log("[runner] ────────────────────────────────────────────────────────\n");
}

function printHypothesesTable(hypotheses) {
  console.log("\n[runner] ─── Hypotheses ────────────────────────────────────────");
  if (!hypotheses.length) {
    console.log("[runner]  (none)");
  }
  for (const h of hypotheses) {
    console.log(
      `[runner]  [${h.asset_type ?? "all"}] ${h.hypothesis_title}\n` +
      `          priority=${h.priority_score} plausibility=${h.plausibility_score} novelty=${h.novelty_score}\n` +
      `          status=${h.status} linked=${h.linked_strategy_id ?? "none"}\n` +
      `          trace=${h.trace_id}`
    );
  }
  console.log("[runner] ────────────────────────────────────────────────────────\n");
}

function printGaps(gaps) {
  console.log("\n[runner] ─── Coverage Gaps ─────────────────────────────────────");
  if (!gaps.length) {
    console.log("[runner]  (none detected)");
  }
  for (const g of gaps) {
    console.log(`[runner]  [${g.severity}] ${g.gap_type}: ${g.description}`);
  }
  console.log("[runner] ────────────────────────────────────────────────────────\n");
}

function printBriefs(briefs) {
  console.log("\n[runner] ─── Research Briefs ───────────────────────────────────");
  for (const b of briefs) {
    console.log(`[runner]  [${b.priority}] ${b.title}`);
    console.log(`          ${b.summary.split("\n").join("\n          ")}`);
  }
  console.log("[runner] ────────────────────────────────────────────────────────\n");
}

function printHelp() {
  console.log(`
Nexus Research Desk — Runner

Usage:
  node research_desk_runner.js --once [--limit N]
      Full pipeline: poll → cluster → hypothesize → rank → link → detect gaps → briefs → Telegram

  node research_desk_runner.js --briefs [--limit N]
      Full pipeline, print and send briefs only.

  node research_desk_runner.js --gaps [--limit N]
      Poll inputs and run gap detection only.

  node research_desk_runner.js --hypotheses [--limit N]
      Full pipeline, print hypotheses table.

  node research_desk_runner.js --help
      Show this help message.

SAFETY: This system is RESEARCH ONLY. No live trading. No broker connections.
`);
}

// ── MAIN ──────────────────────────────────────────────────────────────────────
const { mode, limit } = parseArgs(process.argv);

switch (mode) {
  case "--once": {
    const { inputs, clusters, hypotheses, gaps, briefs } = await runFullPipeline(limit);
    printSummary(inputs, clusters, hypotheses, gaps, briefs);
    printBriefs(briefs);
    await sendResearchAlert(briefs, hypotheses, gaps);
    console.log("[runner] Full pipeline complete.");
    break;
  }

  case "--briefs": {
    const { inputs, clusters, hypotheses, gaps, briefs } = await runFullPipeline(limit);
    printSummary(inputs, clusters, hypotheses, gaps, briefs);
    printBriefs(briefs);
    await sendResearchAlert(briefs, hypotheses, gaps);
    console.log("[runner] Briefs run complete.");
    break;
  }

  case "--gaps": {
    const inputs = await pollResearchInputs(limit);
    // Minimal cluster + hypothesize pass to power gap detector
    const clusters = clusterResearch(inputs);
    const hypotheses = generateHypotheses(clusters, inputs);
    const gaps = detectCoverageGaps(inputs, hypotheses);
    printGaps(gaps);
    console.log("[runner] Gaps run complete.");
    break;
  }

  case "--hypotheses": {
    const { inputs, clusters, hypotheses, gaps, briefs } = await runFullPipeline(limit);
    printSummary(inputs, clusters, hypotheses, gaps, briefs);
    printHypothesesTable(hypotheses);
    console.log("[runner] Hypotheses run complete.");
    break;
  }

  case "--help":
  case "-h":
    printHelp();
    break;

  default:
    console.error(
      `[runner] Unknown mode: "${mode ?? "(none)"}". Run with --help for usage.`
    );
    printHelp();
    process.exit(1);
}
