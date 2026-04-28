#!/usr/bin/env node
// ── Grant Worker ──────────────────────────────────────────────────────────────
// Scans research_artifacts for grant_research topic, normalizes, scores, and
// surfaces top grant opportunities.
//
// Direct run:
//   node grant_worker.js [--since <days>] [--min-score <n>] [--dry-run] [--quiet]
//
// Queue mode (imported):
//   import { runGrantWorker } from "./grant_worker.js";
//   await runGrantWorker({ since_days: 7, min_score: 40 });
//
// RESEARCH ONLY — no trading, no broker connections.
// ─────────────────────────────────────────────────────────────────────────────

import "../env.js";
import { isTransientSupabaseError, supabaseGet, supabaseUpsert } from "../lib/supabase_rest.js";
import { normalizeGrant } from "./grant_normalizer.js";
import { scoreGrant, filterAndRankGrants } from "./grant_scoring.js";
import { generateGrantBrief, sendGrantBriefAlert, formatGrantBriefForTelegram } from "./grant_brief_generator.js";

// ── Data loader ───────────────────────────────────────────────────────────────

async function loadGrantArtifacts(sinceDays) {
  let path = `research_artifacts?topic=eq.grant_research&order=created_at.desc&select=*`;
  if (sinceDays) {
    const since = new Date(Date.now() - sinceDays * 86400000).toISOString();
    path += `&created_at=gte.${since}`;
  }
  const rows = await supabaseGet(path);
  console.log(`[grant-worker] Loaded ${rows.length} grant artifact(s) from Supabase.`);
  return rows;
}

// ── Write results ─────────────────────────────────────────────────────────────

async function writeGrantOpportunities(grants, dryRun) {
  if (dryRun) {
    console.log(`[grant-worker] DRY RUN — would write ${grants.length} grant_opportunities.`);
    return;
  }
  try {
    await supabaseUpsert("grant_opportunities", grants);
    console.log(`[grant-worker] Wrote ${grants.length} row(s) to grant_opportunities.`);
  } catch (err) {
    if (isTransientSupabaseError(err)) {
      console.warn(`[grant-worker] grant_opportunities write degraded: ${err.message}`);
      return;
    }
    // Fail silently if table doesn't exist yet (consistent with rest of system)
    console.warn(`[grant-worker] grant_opportunities write failed: ${err.message}`);
    console.warn(`[grant-worker] Run SQL in docs/grant_opportunities.sql to create the table.`);
  }
}

// ── Console display ───────────────────────────────────────────────────────────

function displayResults(grants, quiet) {
  if (quiet) return;
  console.log(`\n╔═══════════════════════════════════════════════════════════╗`);
  console.log(`║  GRANT WORKER RESULTS                                     ║`);
  console.log(`╚═══════════════════════════════════════════════════════════╝`);
  if (!grants.length) {
    console.log("  No grants above minimum score threshold.");
    return;
  }
  for (const g of grants) {
    console.log(`\n  [${g.score}/100] ${g.title}`);
    if (g.program_name) console.log(`    Program : ${g.program_name}`);
    if (g.funding_amount) console.log(`    Funding : ${g.funding_amount}`);
    if (g.deadline)      console.log(`    Deadline: ${g.deadline}`);
    if (g.geography)     console.log(`    Geo     : ${g.geography}`);
    if (g.target_business_type) console.log(`    For     : ${g.target_business_type}`);
    console.log(`    Source  : ${g.source}`);
  }
  console.log("");
}

// ── Core worker ───────────────────────────────────────────────────────────────

/**
 * Main GrantWorker execution.
 * @param {Object} [opts]
 * @param {number} [opts.since_days=30] - Look back N days (null = all time)
 * @param {number} [opts.min_score=30]  - Minimum score to surface/write
 * @param {boolean} [opts.dry_run=false] - Skip Supabase writes and Telegram
 * @param {boolean} [opts.quiet=false]  - Suppress console output
 * @returns {Promise<{grants: Array, brief: Object}>}
 */
export async function runGrantWorker({
  since_days = 90,
  min_score = 30,
  dry_run = false,
  quiet = false,
} = {}) {
  if (!quiet) {
    console.log(`\n[grant-worker] Starting — since_days=${since_days} min_score=${min_score} dry_run=${dry_run}`);
  }

  // 1. Load grant artifacts from Supabase
  let artifacts;
  try {
    artifacts = await loadGrantArtifacts(since_days);
  } catch (err) {
    if (isTransientSupabaseError(err)) {
      console.warn(`[grant-worker] artifact load degraded: ${err.message}`);
      return { grants: [], brief: null };
    }
    throw err;
  }
  if (!artifacts.length) {
    console.log("[grant-worker] No grant artifacts found — nothing to score.");
    return { grants: [], brief: null };
  }

  // 2. Normalize
  const normalized = artifacts.map(normalizeGrant);

  // 3. Score
  const scored = normalized.map((g) => ({ ...g, score: scoreGrant(g) }));

  // 4. Filter and rank
  const ranked = filterAndRankGrants(scored, min_score);
  if (!quiet) {
    console.log(`[grant-worker] ${scored.length} normalized → ${ranked.length} above score ${min_score}`);
  }

  // 5. Write to grant_opportunities
  await writeGrantOpportunities(ranked, dry_run);

  // 6. Generate brief
  const brief = generateGrantBrief(ranked);
  if (!quiet) displayResults(ranked, quiet);
  if (!quiet && ranked.length) {
    console.log("\n" + brief.body);
  }

  // 7. Send Telegram alert
  if (!dry_run && ranked.length) {
    await sendGrantBriefAlert(brief);
  }

  return { grants: ranked, brief };
}

// ── CLI entry point ───────────────────────────────────────────────────────────

const args = process.argv.slice(2);
if (args.includes("--help")) {
  console.log([
    "Usage: node grant_worker.js [options]",
    "",
    "Options:",
    "  --since <days>     Look back N days (default: 30)",
    "  --min-score <n>    Minimum grant score 0-100 (default: 30)",
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

const isDirect = process.argv[1]?.endsWith("grant_worker.js");
if (isDirect) {
  const since = getArg("--since", "90");
  const minScore = getArg("--min-score", "30");
  const dryRun = args.includes("--dry-run");
  const quiet = args.includes("--quiet");

  runGrantWorker({
    since_days: since === "all" ? null : parseInt(since, 10),
    min_score: parseInt(minScore, 10),
    dry_run: dryRun,
    quiet,
  }).catch((err) => {
    console.error(`[grant-worker] Fatal: ${err.message}`);
    if (process.env.DEBUG) console.error(err.stack);
    process.exit(1);
  });
}
