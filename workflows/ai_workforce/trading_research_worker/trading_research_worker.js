#!/usr/bin/env node
// ── Trading Research Worker ────────────────────────────────────────────────────
// Workforce dispatcher adapter for the trading_analyst pipeline.
//
// Wraps the existing trading_analyst (analyst_runner.js) so it can be
// dispatched via workforce_dispatcher.js like any other worker.
//
// Pipeline:
//   tv_normalized_signals (status=enriched)
//     → OpenClaw AI analysis (analyst_runner.js)
//     → reviewed_signal_proposals (DRAFT, status=proposed|blocked|needs_review)
//     → Telegram alert
//
// HARD LIMITS (enforced by analyst_runner.js + risk_manager):
//   - DRAFT access only — never writes to execution tables
//   - No broker API calls
//   - No live order placement
//   - All proposals require human review before RiskComplianceWorker acts
//
// Direct run:
//   node trading_research_worker.js [--dry-run] [--quiet]
//
// Queue mode:
//   import { runTradingResearchWorker } from "./trading_research_worker.js";
//   await runTradingResearchWorker({ dry_run: false });
// ─────────────────────────────────────────────────────────────────────────────

import "../env.js";
import { execFile } from "child_process";
import { fileURLToPath } from "url";
import { dirname, join, resolve } from "path";

const __dirname = dirname(fileURLToPath(import.meta.url));

const SUPABASE_URL = process.env.SUPABASE_URL;
const SUPABASE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY ?? process.env.SUPABASE_KEY;
const TELEGRAM_BOT_TOKEN = process.env.TELEGRAM_BOT_TOKEN;
const TELEGRAM_CHAT_ID   = process.env.TELEGRAM_CHAT_ID;

// ── Supabase helpers ──────────────────────────────────────────────────────────

async function supabaseGet(path) {
  const res = await fetch(`${SUPABASE_URL}/rest/v1/${path}`, {
    headers: {
      apikey: SUPABASE_KEY,
      Authorization: `Bearer ${SUPABASE_KEY}`,
      "Content-Type": "application/json",
    },
  });
  if (!res.ok) return [];
  return res.json();
}

// ── Signal queue check ────────────────────────────────────────────────────────

async function countEnrichedSignals() {
  try {
    const rows = await supabaseGet(
      "tv_normalized_signals?status=eq.enriched&select=id&limit=100"
    );
    return rows.length;
  } catch {
    return 0;
  }
}

async function countRecentProposals() {
  try {
    const since = new Date(Date.now() - 24 * 3600 * 1000).toISOString();
    const rows = await supabaseGet(
      `reviewed_signal_proposals?select=id,status&created_at=gte.${since}&limit=100`
    );
    const counts = { proposed: 0, blocked: 0, needs_review: 0 };
    for (const r of rows) counts[r.status] = (counts[r.status] ?? 0) + 1;
    return { total: rows.length, ...counts };
  } catch {
    return { total: 0, proposed: 0, blocked: 0, needs_review: 0 };
  }
}

// ── Telegram ──────────────────────────────────────────────────────────────────

async function sendTelegram(text) {
  if (!TELEGRAM_BOT_TOKEN || !TELEGRAM_CHAT_ID) return;
  try {
    await fetch(`https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        chat_id: TELEGRAM_CHAT_ID,
        text,
        parse_mode: "Markdown",
      }),
    });
  } catch {}
}

// ── Run analyst subprocess ────────────────────────────────────────────────────

function runAnalystOnce() {
  return new Promise((resolve, reject) => {
    const analystPath = join(__dirname, "../../trading_analyst/analyst_runner.js");
    const node = process.execPath;

    const child = execFile(
      node,
      ["--input-type=module", analystPath, "--once"],
      { timeout: 120_000, env: process.env },
      (err, stdout, stderr) => {
        if (err) reject(new Error(`analyst_runner failed: ${err.message}\n${stderr}`));
        else resolve(stdout);
      }
    );

    child.stdout?.pipe(process.stdout);
    child.stderr?.pipe(process.stderr);
  });
}

// ── Core worker ───────────────────────────────────────────────────────────────

/**
 * Main TradingResearchWorker execution.
 * Checks signal queue, runs analyst_runner once if signals are present.
 *
 * @param {Object} [opts]
 * @param {boolean} [opts.dry_run=false]
 * @param {boolean} [opts.quiet=false]
 * @returns {Promise<Object>}
 */
export async function runTradingResearchWorker({
  dry_run = false,
  quiet = false,
} = {}) {
  if (!quiet) {
    console.log(`\n[trading-research] Starting — dry_run=${dry_run}`);
    console.log("[trading-research] Mode: DRAFT ONLY — no broker connections");
  }

  const enrichedCount = await countEnrichedSignals();
  const recentProps   = await countRecentProposals();

  if (!quiet) {
    console.log(`[trading-research] Enriched signals pending: ${enrichedCount}`);
    console.log(`[trading-research] Proposals (last 24h): ${recentProps.total} total | ${recentProps.proposed} proposed | ${recentProps.blocked} blocked`);
  }

  if (dry_run) {
    console.log("[trading-research] DRY RUN — analyst not called.");
    return { enriched_signals: enrichedCount, recent_proposals: recentProps, ran: false };
  }

  if (enrichedCount === 0) {
    if (!quiet) console.log("[trading-research] No enriched signals — nothing to process.");
    return { enriched_signals: 0, recent_proposals: recentProps, ran: false };
  }

  if (!quiet) console.log(`[trading-research] Running analyst on ${enrichedCount} signal(s)...`);

  try {
    await runAnalystOnce();
  } catch (err) {
    console.error(`[trading-research] Analyst error: ${err.message}`);
    await sendTelegram(`⚠️ *Trading Research Worker* — analyst error:\n\`${err.message.slice(0, 200)}\``);
    return { enriched_signals: enrichedCount, recent_proposals: recentProps, ran: false, error: err.message };
  }

  const updatedProps = await countRecentProposals();
  if (!quiet) {
    console.log(`[trading-research] ✅ Done — proposals now: ${updatedProps.total} (last 24h)`);
  }

  return { enriched_signals: enrichedCount, recent_proposals: updatedProps, ran: true };
}

// ── CLI entry ─────────────────────────────────────────────────────────────────

const args = process.argv.slice(2);

if (args.includes("--help")) {
  console.log([
    "Usage: node trading_research_worker.js [options]",
    "",
    "Workforce adapter for trading_analyst pipeline.",
    "",
    "Options:",
    "  --dry-run   Check signal queue but don't run analyst",
    "  --quiet     Suppress verbose output",
    "  --help      Show this help",
    "",
    "Output: reviewed_signal_proposals (DRAFT). Human review required before execution.",
  ].join("\n"));
  process.exit(0);
}

const isDirect = process.argv[1]?.endsWith("trading_research_worker.js");
if (isDirect) {
  runTradingResearchWorker({
    dry_run: args.includes("--dry-run"),
    quiet:   args.includes("--quiet"),
  }).then((r) => {
    console.log("\n[trading-research] Result:", JSON.stringify(r, null, 2));
    process.exit(0);
  }).catch((err) => {
    console.error(`[trading-research] Fatal: ${err.message}`);
    process.exit(1);
  });
}
