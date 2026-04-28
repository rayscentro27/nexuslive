#!/usr/bin/env node
// ── Opportunity Worker ────────────────────────────────────────────────────────
// Scans research_artifacts for business_opportunities + crm_automation topics,
// detects recurring niches and service gaps, scores, and surfaces opportunities.
//
// Direct run:
//   node opportunity_worker.js [--since <days>] [--min-score <n>] [--dry-run] [--quiet]
//   node opportunity_worker.js --topic crm_automation --since 14
//
// Queue mode (imported):
//   import { runOpportunityWorker } from "./opportunity_worker.js";
//   await runOpportunityWorker({ since_days: 7, min_score: 40 });
//
// RESEARCH ONLY — no trading, no broker connections.
// ─────────────────────────────────────────────────────────────────────────────

import "../env.js";
import { isTransientSupabaseError, supabaseGet, supabaseUpsert } from "../lib/supabase_rest.js";
import { normalizeOpportunity } from "./opportunity_normalizer.js";
import { scoreOpportunity, filterAndRankOpportunities } from "./opportunity_scoring.js";
import {
  generateOpportunityBrief,
  sendOpportunityBriefAlert,
} from "./opportunity_brief_generator.js";

const OPPORTUNITY_TOPICS = ["business_opportunities", "crm_automation"];

// ── Data loader ───────────────────────────────────────────────────────────────

async function loadOpportunityArtifacts(sinceDays, topicFilter) {
  const topics = topicFilter ? [topicFilter] : OPPORTUNITY_TOPICS;
  const allRows = [];

  for (const topic of topics) {
    let path = `research_artifacts?topic=eq.${topic}&order=created_at.desc&select=*`;
    if (sinceDays) {
      const since = new Date(Date.now() - sinceDays * 86400000).toISOString();
      path += `&created_at=gte.${since}`;
    }
    const rows = await supabaseGet(path);
    allRows.push(...rows);
  }

  console.log(`[opp-worker] Loaded ${allRows.length} opportunity artifact(s) from Supabase.`);
  return allRows;
}

// ── Niche pattern detection ───────────────────────────────────────────────────
// Identify repeated themes across all opportunities (signal of strong demand)
function detectRepeatedNiches(opps) {
  const nicheCounts = {};
  for (const o of opps) {
    nicheCounts[o.niche] = (nicheCounts[o.niche] ?? 0) + 1;
  }
  return Object.entries(nicheCounts)
    .filter(([, count]) => count >= 2)
    .sort((a, b) => b[1] - a[1])
    .map(([niche, count]) => ({ niche, count }));
}

// ── Write results ─────────────────────────────────────────────────────────────

async function writeBusinessOpportunities(opps, dryRun) {
  if (dryRun) {
    console.log(`[opp-worker] DRY RUN — would write ${opps.length} business_opportunities.`);
    return;
  }
  try {
    const rows = opps.map((opp) => ({
      ...opp,
      // Legacy table compatibility: older schema requires `type`
      type: opp.opportunity_type ?? "other",
    }));
    await supabaseUpsert("business_opportunities", rows);
    console.log(`[opp-worker] Wrote ${opps.length} row(s) to business_opportunities.`);
  } catch (err) {
    if (isTransientSupabaseError(err)) {
      console.warn(`[opp-worker] business_opportunities write degraded: ${err.message}`);
      return;
    }
    console.warn(`[opp-worker] business_opportunities write failed: ${err.message}`);
    console.warn(`[opp-worker] Run SQL in docs/business_opportunities.sql to create the table.`);
  }
}

// ── Console display ───────────────────────────────────────────────────────────

function displayResults(opps, repeatedNiches, quiet) {
  if (quiet) return;
  console.log(`\n╔═══════════════════════════════════════════════════════════╗`);
  console.log(`║  OPPORTUNITY WORKER RESULTS                               ║`);
  console.log(`╚═══════════════════════════════════════════════════════════╝`);

  if (repeatedNiches.length) {
    console.log(`\n  Recurring niches (signal of demand):`);
    for (const { niche, count } of repeatedNiches) {
      console.log(`    × ${count}  ${niche}`);
    }
  }

  if (!opps.length) {
    console.log("\n  No opportunities above minimum score threshold.");
    return;
  }

  console.log(`\n  Top opportunities:`);
  for (const o of opps) {
    console.log(`\n  [${o.score}/100] ${o.urgency.toUpperCase()} — ${o.title}`);
    console.log(`    Type  : ${o.opportunity_type} | Niche: ${o.niche}`);
    console.log(`    Money : ${o.monetization_hint}`);
    if (o.evidence_summary) {
      console.log(`    Evidence: ${o.evidence_summary.slice(0, 100)}…`);
    }
    console.log(`    Source: ${o.source}`);
  }
  console.log("");
}

// ── Core worker ───────────────────────────────────────────────────────────────

/**
 * Main OpportunityWorker execution.
 * @param {Object} [opts]
 * @param {number|null} [opts.since_days=30] - Look back N days (null = all time)
 * @param {number} [opts.min_score=35]       - Minimum score to surface/write
 * @param {string|null} [opts.topic=null]    - Filter to specific topic
 * @param {boolean} [opts.dry_run=false]     - Skip Supabase writes and Telegram
 * @param {boolean} [opts.quiet=false]       - Suppress console output
 * @returns {Promise<{opps: Array, brief: Object, repeated_niches: Array}>}
 */
export async function runOpportunityWorker({
  since_days = 90,
  min_score = 35,
  topic = null,
  dry_run = false,
  quiet = false,
} = {}) {
  if (!quiet) {
    console.log(
      `\n[opp-worker] Starting — since_days=${since_days} min_score=${min_score} topic=${topic ?? "all"} dry_run=${dry_run}`
    );
  }

  // 1. Load artifacts
  let artifacts;
  try {
    artifacts = await loadOpportunityArtifacts(since_days, topic);
  } catch (err) {
    if (isTransientSupabaseError(err)) {
      console.warn(`[opp-worker] artifact load degraded: ${err.message}`);
      return { opps: [], brief: null, repeated_niches: [] };
    }
    throw err;
  }
  if (!artifacts.length) {
    console.log("[opp-worker] No opportunity artifacts found — nothing to score.");
    return { opps: [], brief: null, repeated_niches: [] };
  }

  // 2. Normalize
  const normalized = artifacts.map(normalizeOpportunity);

  // 3. Score
  const scored = normalized.map((o) => ({ ...o, score: scoreOpportunity(o) }));

  // 4. Filter and rank
  const ranked = filterAndRankOpportunities(scored, min_score);
  if (!quiet) {
    console.log(`[opp-worker] ${scored.length} normalized → ${ranked.length} above score ${min_score}`);
  }

  // 5. Detect repeated niches across ALL scored opps (not just above threshold)
  const repeatedNiches = detectRepeatedNiches(scored);
  if (!quiet && repeatedNiches.length) {
    console.log(`[opp-worker] Repeated niches: ${repeatedNiches.map((n) => n.niche).join(", ")}`);
  }

  // 6. Write to business_opportunities
  await writeBusinessOpportunities(ranked, dry_run);

  // 7. Generate brief
  const brief = generateOpportunityBrief(ranked);
  if (!quiet) displayResults(ranked, repeatedNiches, quiet);
  if (!quiet && ranked.length) {
    console.log("\n" + brief.body);
  }

  // 8. Telegram alert
  if (!dry_run && ranked.length) {
    await sendOpportunityBriefAlert(brief);
  }

  return { opps: ranked, brief, repeated_niches: repeatedNiches };
}

// ── CLI entry point ───────────────────────────────────────────────────────────

const args = process.argv.slice(2);
if (args.includes("--help")) {
  console.log([
    "Usage: node opportunity_worker.js [options]",
    "",
    "Options:",
    "  --since <days>     Look back N days (default: 30, use 'all' for all time)",
    "  --min-score <n>    Minimum opportunity score 0-100 (default: 35)",
    "  --topic <topic>    Filter to specific topic (business_opportunities|crm_automation)",
    "  --dry-run          Skip Supabase writes and Telegram",
    "  --quiet            Suppress detailed console output",
    "  --help             Show this help",
  ].join("\n"));
  process.exit(0);
}

function getArg(flag, defaultVal) {
  const idx = args.indexOf(flag);
  return idx !== -1 ? args[idx + 1] : defaultVal;
}

const isDirect = process.argv[1]?.endsWith("opportunity_worker.js");
if (isDirect) {
  const since = getArg("--since", "90");
  const minScore = getArg("--min-score", "35");
  const topic = getArg("--topic", null);
  const dryRun = args.includes("--dry-run");
  const quiet = args.includes("--quiet");

  runOpportunityWorker({
    since_days: since === "all" ? null : parseInt(since, 10),
    min_score: parseInt(minScore, 10),
    topic,
    dry_run: dryRun,
    quiet,
  }).catch((err) => {
    console.error(`[opp-worker] Fatal: ${err.message}`);
    if (process.env.DEBUG) console.error(err.stack);
    process.exit(1);
  });
}
