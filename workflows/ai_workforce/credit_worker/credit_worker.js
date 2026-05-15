#!/usr/bin/env node
// ── Credit Worker ─────────────────────────────────────────────────────────────
// Analyzes credit repair research artifacts and generates PII-safe
// dispute workflow templates for human review.
//
// PII SAFETY RULES (non-negotiable):
//   - This worker operates on RESEARCH ARTIFACTS only (not client files)
//   - Research artifacts contain educational content, not client PII
//   - Client credit report processing is handled via a separate human-supervised
//     workflow (dispute_draft_workflow.js + dispute_template_reinsertion.js)
//   - No client SSN, DOB, account numbers, or addresses ever pass through this worker
//
// Direct run:
//   node credit_worker.js [--since <days>] [--dry-run] [--quiet]
//
// Queue mode (imported):
//   import { runCreditWorker } from "./credit_worker.js";
//   await runCreditWorker({ since_days: 7, dry_run: false });
//
// RESEARCH ONLY — no client PII, no broker connections, no Oracle VM.
// ─────────────────────────────────────────────────────────────────────────────

import "../env.js";
import { redactPII, classifyText } from "./credit_redaction_policy.js";

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
  if (!res.ok) throw new Error(`Supabase GET ${path}: ${res.status} ${await res.text()}`);
  return res.json();
}

// ── Data loader ───────────────────────────────────────────────────────────────

async function loadCreditArtifacts(sinceDays) {
  let path = `research_artifacts?topic=eq.credit_repair&order=created_at.desc&select=*`;
  if (sinceDays) {
    const since = new Date(Date.now() - sinceDays * 86400000).toISOString();
    path += `&created_at=gte.${since}`;
  }
  return supabaseGet(path);
}

// ── Credit research analyzer ──────────────────────────────────────────────────

const FCRA_PATTERNS = [
  [/fcra|fair\s+credit\s+reporting/i, "FCRA Reference"],
  [/cfpb|consumer\s+financial\s+protection/i, "CFPB Reference"],
  [/dispute\s+(?:letter|process|strategy)/i, "Dispute Strategy"],
  [/tradeline/i, "Tradeline Analysis"],
  [/charge.off/i, "Charge-Off Strategy"],
  [/collection\s+(?:account|agency)/i, "Collections Strategy"],
  [/pay\s+for\s+delete|pay.for.delete/i, "Pay-for-Delete"],
  [/goodwill\s+letter/i, "Goodwill Letter"],
  [/statute\s+of\s+limitations/i, "Statute of Limitations"],
  [/medical\s+debt/i, "Medical Debt Rules"],
  [/authorized\s+user/i, "Authorized User Strategy"],
  [/rapid\s+rescor/i, "Rapid Rescore"],
  [/section\s+609|§\s*609/i, "Section 609 Method"],
  [/credit\s+utilization/i, "Utilization Strategy"],
];

const URGENCY_PATTERNS = [
  [/2026|2025/i, "high"],
  [/new\s+rule|updated\s+rule|recent\s+change/i, "high"],
  [/cfpb\s+(?:rule|guidance|update)/i, "high"],
  [/medical\s+debt\s+removal/i, "high"],
];

function analyzeArtifact(artifact) {
  const text = [
    artifact.title ?? "",
    artifact.summary ?? "",
    ...(artifact.key_points ?? []),
  ].join(" ");

  // Run PII check — educational content should have none
  const { redacted, replacements, pii_types_found } = redactPII(text);
  const classification = classifyText(text);

  // Detect strategies/references mentioned
  const strategies = FCRA_PATTERNS
    .filter(([re]) => re.test(text))
    .map(([, name]) => name);

  // Detect urgency
  let urgency = "low";
  for (const [re, level] of URGENCY_PATTERNS) {
    if (re.test(text)) { urgency = level; break; }
  }

  return {
    artifact_id:      artifact.id,
    source:           artifact.source ?? "Unknown",
    title:            artifact.title ?? "Untitled",
    strategies_found: strategies,
    urgency,
    classification,  // A, B, or C
    pii_detected:     replacements > 0,
    pii_types:        pii_types_found,
    summary:          redacted.slice(0, 400),  // always use redacted version
    evidence:         (artifact.key_points ?? []).slice(0, 3).join(" | "),
    status:           "research",
  };
}

// ── Brief generator ───────────────────────────────────────────────────────────

function generateCreditBrief(analyses) {
  if (!analyses.length) return null;

  // Group by strategy type
  const strategyFreq = {};
  for (const a of analyses) {
    for (const s of a.strategies_found) {
      strategyFreq[s] = (strategyFreq[s] ?? 0) + 1;
    }
  }
  const topStrategies = Object.entries(strategyFreq)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5)
    .map(([s, n]) => `${s} (×${n})`);

  const highUrgency = analyses.filter((a) => a.urgency === "high");

  const lines = [
    `CREDIT WORKER RESEARCH BRIEF — ${new Date().toLocaleDateString()}`,
    `${analyses.length} artifact(s) analyzed`,
    "",
  ];

  if (topStrategies.length) {
    lines.push("Top strategies in research:");
    topStrategies.forEach((s) => lines.push(`  • ${s}`));
    lines.push("");
  }

  if (highUrgency.length) {
    lines.push("⚡ High-urgency findings:");
    highUrgency.slice(0, 3).forEach((a) => {
      lines.push(`  [${a.source}] ${a.title}`);
      lines.push(`  ${a.summary.slice(0, 120)}`);
    });
    lines.push("");
  }

  // Flag any PII detected in research content (should be zero)
  const piiDetected = analyses.filter((a) => a.pii_detected);
  if (piiDetected.length) {
    lines.push(`⚠️  PII detected in ${piiDetected.length} artifact(s) — review and sanitize source content.`);
    lines.push("");
  }

  lines.push("Note: These are research findings only. Dispute templates require human advisor review.");

  return {
    title: `Credit Research Brief — ${new Date().toLocaleDateString()}`,
    body: lines.join("\n"),
    analyses,
    strategy_frequency: strategyFreq,
    high_urgency_count: highUrgency.length,
    pii_flagged_count: piiDetected.length,
  };
}

// ── Telegram alert ────────────────────────────────────────────────────────────

async function sendCreditAlert(brief) {
  if (!TELEGRAM_BOT_TOKEN || !TELEGRAM_CHAT_ID) {
    console.warn("[credit-worker] Telegram not configured — skipping alert.");
    return;
  }
  if ((process.env.TELEGRAM_AUTO_REPORTS_ENABLED || "false") !== "true") {
    console.log("telegram_policy denied=true reason=manual_only_default");
    return;
  }

  const lines = [
    "💳 *Credit Research Brief*",
    `_${brief.analyses.length} artifact(s) analyzed_`,
    "",
  ];

  if (brief.high_urgency_count > 0) {
    lines.push(`⚡ ${brief.high_urgency_count} high\\-urgency finding(s)`);
  }

  if (brief.pii_flagged_count > 0) {
    lines.push(`⚠️ PII detected in ${brief.pii_flagged_count} source(s) — review needed`);
  }

  lines.push("", "Research only — dispute templates require advisor review\\.");

  try {
    const res = await fetch(`https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        chat_id: TELEGRAM_CHAT_ID,
        text: lines.join("\n"),
        parse_mode: "Markdown",
      }),
    });
    if (res.ok) console.log(`[credit-worker] Telegram alert sent (${brief.analyses.length} artifacts).`);
    else console.warn(`[credit-worker] Telegram error: ${await res.text()}`);
  } catch (err) {
    console.warn(`[credit-worker] Telegram send failed: ${err.message}`);
  }
}

// ── Core worker ───────────────────────────────────────────────────────────────

/**
 * Main CreditWorker execution.
 * Analyzes credit repair research artifacts — NOT client credit files.
 *
 * @param {Object} [opts]
 * @param {number|null} [opts.since_days=30]
 * @param {boolean} [opts.dry_run=false]
 * @param {boolean} [opts.quiet=false]
 * @returns {Promise<{analyses: Array, brief: Object|null}>}
 */
export async function runCreditWorker({
  since_days = 90,
  dry_run = false,
  quiet = false,
} = {}) {
  if (!quiet) {
    console.log(`\n[credit-worker] Starting — since_days=${since_days} dry_run=${dry_run}`);
    console.log("[credit-worker] Mode: RESEARCH ANALYSIS ONLY — no client PII");
  }

  const artifacts = await loadCreditArtifacts(since_days);
  if (!quiet) console.log(`[credit-worker] Loaded ${artifacts.length} credit repair artifact(s).`);

  if (!artifacts.length) {
    console.log("[credit-worker] No artifacts found — run research pipeline with topic=credit_repair first.");
    return { analyses: [], brief: null };
  }

  const analyses = artifacts.map(analyzeArtifact);

  // Flag any PII found in research content (advisory warning)
  const piiArtifacts = analyses.filter((a) => a.pii_detected);
  if (piiArtifacts.length && !quiet) {
    console.warn(`[credit-worker] ⚠️ PII detected in ${piiArtifacts.length} research artifact(s). Source content should be sanitized.`);
  }

  const brief = generateCreditBrief(analyses);

  if (!quiet) {
    console.log(`\n[credit-worker] ${analyses.length} artifact(s) analyzed.`);
    if (brief) console.log("\n" + brief.body);
  }

  if (dry_run) {
    console.log("[credit-worker] DRY RUN — no Telegram.");
    return { analyses, brief };
  }

  if (brief) await sendCreditAlert(brief);

  return { analyses, brief };
}

// ── CLI entry ─────────────────────────────────────────────────────────────────

const args = process.argv.slice(2);
if (args.includes("--help")) {
  console.log([
    "Usage: node credit_worker.js [options]",
    "",
    "Analyzes credit repair RESEARCH ARTIFACTS — not client credit files.",
    "",
    "Options:",
    "  --since <days>  Look back N days (default: 30)",
    "  --dry-run       No Telegram, analysis only",
    "  --quiet         Suppress verbose output",
    "  --help          Show this help",
    "",
    "For dispute draft workflow, see: dispute_draft_workflow.js",
    "For PII redaction, see: credit_redaction_policy.js",
  ].join("\n"));
  process.exit(0);
}

function getArg(f, d) { const i = args.indexOf(f); return i !== -1 ? args[i + 1] : d; }

const isDirect = process.argv[1]?.endsWith("credit_worker.js");
if (isDirect) {
  const since = getArg("--since", "90");
  runCreditWorker({
    since_days: since === "all" ? null : parseInt(since, 10),
    dry_run: args.includes("--dry-run"),
    quiet: args.includes("--quiet"),
  }).catch((err) => {
    console.error(`[credit-worker] Fatal: ${err.message}`);
    process.exit(1);
  });
}
