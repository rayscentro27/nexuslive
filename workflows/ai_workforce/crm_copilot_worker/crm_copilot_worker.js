#!/usr/bin/env node
// ── Staff CRM Copilot Worker ──────────────────────────────────────────────────
// Analyzes CRM automation research artifacts and generates actionable
// GoHighLevel / workflow improvement suggestions for staff review.
//
// Output is DRAFT only — no auto-execution of CRM workflows.
// Human review is required before any suggestion is implemented.
//
// Direct run:
//   node crm_copilot_worker.js [--since <days>] [--dry-run] [--quiet]
//
// Queue mode (imported):
//   import { runCRMCopilotWorker } from "./crm_copilot_worker.js";
//   await runCRMCopilotWorker({ since_days: 7, dry_run: false });
//
// RESEARCH ONLY — no CRM writes, no client PII, no Oracle VM.
// ─────────────────────────────────────────────────────────────────────────────

import "../env.js";

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

async function loadCRMArtifacts(sinceDays) {
  let path = `research_artifacts?topic=eq.crm_automation&order=created_at.desc&select=*`;
  if (sinceDays) {
    const since = new Date(Date.now() - sinceDays * 86400000).toISOString();
    path += `&created_at=gte.${since}`;
  }
  return supabaseGet(path);
}

async function loadBusinessOpportunities(sinceDays) {
  let path = `business_opportunities?status=eq.new&order=score.desc&select=*&limit=20`;
  if (sinceDays) {
    const since = new Date(Date.now() - sinceDays * 86400000).toISOString();
    path += `&created_at=gte.${since}`;
  }
  try {
    return await supabaseGet(path);
  } catch {
    return [];
  }
}

// ── CRM Suggestion Generator ──────────────────────────────────────────────────

// Known CRM tools and platforms for pattern detection
const CRM_TOOL_PATTERNS = [
  [/gohighlevel|ghl\b/i, "GoHighLevel"],
  [/hubspot/i, "HubSpot"],
  [/make\.com|integromat/i, "Make.com"],
  [/zapier/i, "Zapier"],
  [/n8n\b/i, "n8n"],
  [/activecampaign/i, "ActiveCampaign"],
  [/salesforce/i, "Salesforce"],
  [/pipedrive/i, "Pipedrive"],
];

const CRM_CATEGORY_PATTERNS = [
  [/lead\s+(?:gen|generation|nurtur)/i, "Lead Generation / Nurturing"],
  [/follow[\s-]?up\s+(?:sequence|automation)/i, "Follow-Up Sequences"],
  [/pipeline\s+(?:stage|automation|management)/i, "Pipeline Automation"],
  [/appointment\s+(?:booking|scheduling)/i, "Appointment Booking"],
  [/onboarding\s+(?:flow|automation)/i, "Client Onboarding"],
  [/email\s+(?:campaign|sequence|automation)/i, "Email Campaigns"],
  [/sms\s+(?:automation|campaign|follow)/i, "SMS Automation"],
  [/webhook|api\s+integration/i, "API / Webhook Integration"],
  [/review\s+(?:request|automation)/i, "Review Requests"],
  [/reporting\s+(?:dashboard|automation)/i, "Reporting & Analytics"],
];

function detectCRMTool(text) {
  for (const [re, tool] of CRM_TOOL_PATTERNS) {
    if (re.test(text)) return tool;
  }
  return "General CRM";
}

function detectCRMCategory(text) {
  for (const [re, cat] of CRM_CATEGORY_PATTERNS) {
    if (re.test(text)) return cat;
  }
  return "Workflow Automation";
}

function extractActionableInsight(artifact) {
  const points = artifact.key_points ?? [];
  if (points.length >= 2) return points.slice(0, 2).join(" | ");
  return (artifact.summary ?? "").slice(0, 300);
}

function normalizeSuggestion(artifact) {
  const text = [
    artifact.title ?? "",
    artifact.summary ?? "",
    ...(artifact.key_points ?? []),
  ].join(" ");

  return {
    artifact_id: artifact.id,
    source: artifact.source ?? "Unknown",
    title: artifact.title ?? "Untitled",
    crm_tool: detectCRMTool(text),
    category: detectCRMCategory(text),
    insight: extractActionableInsight(artifact),
    raw_summary: (artifact.summary ?? "").slice(0, 500),
    status: "draft",
    requires_human_approval: true,
  };
}

// ── Brief generation ──────────────────────────────────────────────────────────

function generateCRMBrief(suggestions) {
  if (!suggestions.length) return null;

  // Group by category
  const byCategory = {};
  for (const s of suggestions) {
    if (!byCategory[s.category]) byCategory[s.category] = [];
    byCategory[s.category].push(s);
  }

  // Group by CRM tool
  const toolCounts = {};
  for (const s of suggestions) {
    toolCounts[s.crm_tool] = (toolCounts[s.crm_tool] ?? 0) + 1;
  }
  const topTools = Object.entries(toolCounts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 3)
    .map(([tool, count]) => `${tool} (×${count})`);

  const lines = [
    `STAFF CRM COPILOT — ${suggestions.length} suggestion(s) found`,
    `Top platforms: ${topTools.join(", ")}`,
    "",
  ];

  for (const [cat, items] of Object.entries(byCategory)) {
    lines.push(`【${cat}】`);
    for (const s of items.slice(0, 2)) {
      lines.push(`  • [${s.crm_tool}] ${s.title}`);
      lines.push(`    ${s.insight.slice(0, 150)}`);
      lines.push(`    Source: ${s.source}`);
    }
    lines.push("");
  }

  lines.push("⚠️  All suggestions are DRAFTS — human review required before any CRM changes.");

  return {
    title: `CRM Copilot Brief — ${new Date().toLocaleDateString()}`,
    body: lines.join("\n"),
    suggestions,
    tool_counts: toolCounts,
    category_groups: Object.keys(byCategory),
  };
}

// ── Telegram alert ────────────────────────────────────────────────────────────

async function sendCRMAlert(brief) {
  if (!TELEGRAM_BOT_TOKEN || !TELEGRAM_CHAT_ID) {
    console.warn("[crm-copilot] Telegram not configured — skipping alert.");
    return;
  }
  if ((process.env.TELEGRAM_AUTO_REPORTS_ENABLED || "false") !== "true") {
    console.log("telegram_policy denied=true reason=manual_only_default");
    return;
  }

  const top3 = brief.suggestions.slice(0, 3);
  const lines = [
    "🤝 *CRM Copilot Brief*",
    `_${top3.length} top suggestions_`,
    "",
  ];

  for (const s of top3) {
    lines.push(`*${s.title.replace(/[_*[\]()~`>#+=|{}.!-]/g, "\\$&")}*`);
    lines.push(`Tool: ${s.crm_tool} | ${s.category}`);
    lines.push(`Source: ${s.source}`);
    lines.push("");
  }

  lines.push("⚠️ Drafts only — review required before implementation\\.");

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
    if (res.ok) console.log(`[crm-copilot] Telegram alert sent (${brief.suggestions.length} suggestions).`);
    else {
      const err = await res.text();
      console.warn(`[crm-copilot] Telegram error: ${err}`);
    }
  } catch (err) {
    console.warn(`[crm-copilot] Telegram send failed: ${err.message}`);
  }
}

// ── Display ───────────────────────────────────────────────────────────────────

function displayResults(suggestions, quiet) {
  if (quiet) return;
  console.log("\n╔═══════════════════════════════════════════════════════════╗");
  console.log("║  STAFF CRM COPILOT RESULTS                                ║");
  console.log("╚═══════════════════════════════════════════════════════════╝");
  if (!suggestions.length) {
    console.log("  No CRM suggestions generated.");
    return;
  }
  for (const s of suggestions) {
    console.log(`\n  [${s.crm_tool}] ${s.title}`);
    console.log(`    Category: ${s.category}`);
    console.log(`    Insight : ${s.insight.slice(0, 120)}`);
    console.log(`    Source  : ${s.source}`);
  }
  console.log("\n  ⚠️  All outputs are DRAFT — human review required.\n");
}

// ── Core worker ───────────────────────────────────────────────────────────────

/**
 * Main CRMCopilotWorker execution.
 * @param {Object} [opts]
 * @param {number|null} [opts.since_days=30]
 * @param {boolean} [opts.dry_run=false]
 * @param {boolean} [opts.quiet=false]
 * @returns {Promise<{suggestions: Array, brief: Object|null}>}
 */
export async function runCRMCopilotWorker({
  since_days = 90,
  dry_run = false,
  quiet = false,
} = {}) {
  if (!quiet) {
    console.log(`\n[crm-copilot] Starting — since_days=${since_days} dry_run=${dry_run}`);
    console.log("[crm-copilot] Mode: DRAFT ONLY — no CRM writes, no automation execution");
  }

  const artifacts = await loadCRMArtifacts(since_days);
  if (!quiet) console.log(`[crm-copilot] Loaded ${artifacts.length} CRM automation artifact(s).`);

  if (!artifacts.length) {
    console.log("[crm-copilot] No CRM artifacts found — run research pipeline with topic=crm_automation first.");
    return { suggestions: [], brief: null };
  }

  // Normalize into suggestions
  const suggestions = artifacts.map(normalizeSuggestion);

  if (!quiet) {
    console.log(`[crm-copilot] Generated ${suggestions.length} draft suggestion(s).`);
  }

  // Generate brief
  const brief = generateCRMBrief(suggestions);
  if (!quiet) displayResults(suggestions, quiet);
  if (!quiet && brief) console.log("\n" + brief.body);

  if (dry_run) {
    console.log("[crm-copilot] DRY RUN — no writes, no Telegram.");
    return { suggestions, brief };
  }

  // Send Telegram
  if (brief) await sendCRMAlert(brief);

  return { suggestions, brief };
}

// ── CLI entry ─────────────────────────────────────────────────────────────────

const args = process.argv.slice(2);
if (args.includes("--help")) {
  console.log([
    "Usage: node crm_copilot_worker.js [options]",
    "",
    "Options:",
    "  --since <days>  Look back N days (default: 30)",
    "  --dry-run       Skip Telegram, outputs only",
    "  --quiet         Suppress verbose console output",
    "  --help          Show this help",
    "",
    "Output: DRAFT suggestions only. All require human review before implementation.",
  ].join("\n"));
  process.exit(0);
}

function getArg(flag, def) {
  const idx = args.indexOf(flag);
  return idx !== -1 ? args[idx + 1] : def;
}

const isDirect = process.argv[1]?.endsWith("crm_copilot_worker.js");
if (isDirect) {
  const since = getArg("--since", "90");
  runCRMCopilotWorker({
    since_days: since === "all" ? null : parseInt(since, 10),
    dry_run: args.includes("--dry-run"),
    quiet: args.includes("--quiet"),
  }).catch((err) => {
    console.error(`[crm-copilot] Fatal: ${err.message}`);
    if (process.env.DEBUG) console.error(err.stack);
    process.exit(1);
  });
}
