#!/usr/bin/env node
// -- Autonomous Opportunity Engine -------------------------------------------
// Scans Nexus Brain research tables and generates prioritized opportunities.
// Supports direct-run and queue-style invocation.
// RESEARCH ONLY - no live trading, no broker execution.
// -----------------------------------------------------------------------------

import "../env.js";
import { randomUUID } from "crypto";
import { detectOpportunities } from "./opportunity_detector.js";
import { rankOpportunities } from "./opportunity_ranker.js";
import { attachRoutingAndActions } from "./opportunity_action_generator.js";
import {
  generateOpportunityBrief,
  formatBriefForLog,
  sendOpportunityBriefAlert,
} from "./opportunity_brief_generator.js";

const SUPABASE_URL = process.env.SUPABASE_URL;
const SUPABASE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY ?? process.env.SUPABASE_KEY;

const DEFAULT_LIMITS = Object.freeze({
  artifacts: 120,
  claims: 120,
  clusters: 40,
  hypotheses: 60,
  gaps: 60,
});

function headers() {
  return {
    apikey: SUPABASE_KEY,
    Authorization: `Bearer ${SUPABASE_KEY}`,
    "Content-Type": "application/json",
  };
}

function decodeBody(body) {
  try {
    return JSON.parse(body);
  } catch {
    return null;
  }
}

async function supabaseGet(path, { optional = false } = {}) {
  const res = await fetch(`${SUPABASE_URL}/rest/v1/${path}`, { headers: headers() });
  if (res.ok) return res.json();

  const body = await res.text();
  const parsed = decodeBody(body);
  const missing = res.status === 404 || parsed?.code === "42P01";

  if (optional && missing) return [];
  throw new Error(`Supabase GET ${path} failed: ${res.status} ${body}`);
}

async function supabaseInsert(table, rows, { optional = false } = {}) {
  if (!rows.length) return { inserted: 0 };

  const res = await fetch(`${SUPABASE_URL}/rest/v1/${table}`, {
    method: "POST",
    headers: {
      ...headers(),
      Prefer: "resolution=merge-duplicates",
    },
    body: JSON.stringify(rows),
  });

  if (res.ok) return { inserted: rows.length };

  const body = await res.text();
  const parsed = decodeBody(body);
  const missing = res.status === 404 || parsed?.code === "42P01";
  if (optional && missing) return { inserted: 0, skipped: true };

  throw new Error(`Supabase INSERT ${table} failed: ${res.status} ${body}`);
}

function sinceFilter(field, sinceDays) {
  if (!sinceDays) return "";
  const since = new Date(Date.now() - sinceDays * 86_400_000).toISOString();
  return `&${field}=gte.${since}`;
}

async function loadOpportunityEngineInputs({ since_days = 30, limits = DEFAULT_LIMITS } = {}) {
  const dataset = {};

  dataset.research_artifacts = await supabaseGet(
    `research_artifacts?select=id,source,topic,title,summary,content,key_points,action_items,opportunity_notes,trace_id,created_at&order=created_at.desc&limit=${limits.artifacts}${sinceFilter("created_at", since_days)}`,
    { optional: true }
  );

  dataset.research_claims = await supabaseGet(
    `research_claims?select=id,source,topic,subtheme,claim_text,claim_type,confidence,trace_id,created_at&order=created_at.desc&limit=${limits.claims}${sinceFilter("created_at", since_days)}`,
    { optional: true }
  );

  dataset.research_clusters = await supabaseGet(
    `research_clusters?select=id,cluster_name,theme,source_count,summary,key_terms,confidence,created_at&order=created_at.desc&limit=${limits.clusters}${sinceFilter("created_at", since_days)}`,
    { optional: true }
  );

  dataset.research_hypotheses = await supabaseGet(
    `research_hypotheses?select=id,hypothesis_title,asset_type,market_type,hypothesis_text,supporting_evidence,novelty_score,plausibility_score,priority_score,trace_id,created_at&order=created_at.desc&limit=${limits.hypotheses}${sinceFilter("created_at", since_days)}`,
    { optional: true }
  );

  dataset.coverage_gaps = await supabaseGet(
    `coverage_gaps?select=id,gap_type,asset_type,description,severity,notes,created_at&order=created_at.desc&limit=${limits.gaps}${sinceFilter("created_at", since_days)}`,
    { optional: true }
  );

  return dataset;
}

function mapToGrantRows(opportunities) {
  return opportunities
    .filter((o) => o.opportunity_type === "grant_opportunity")
    .map((o) => ({
      source: o.source,
      title: o.title,
      program_name: o.title,
      funding_amount: o.monetization_hint,
      geography: o.niche,
      eligibility_notes: o.evidence_summary,
      deadline: o.urgency === "high" ? "Time-sensitive" : "Rolling / unknown",
      confidence: o.confidence,
      score: o.score,
      status: "new",
      trace_id: o.trace_id ?? randomUUID(),
    }));
}

function mapBusinessType(opportunityType) {
  switch (opportunityType) {
    case "saas_idea":
      return "saas";
    case "automation_idea":
      return "automation_agency";
    case "product_improvement":
      return "ai_product";
    case "service_gap":
      return "service_business";
    default:
      return "other";
  }
}

function mapToBusinessRows(opportunities) {
  return opportunities
    .filter((o) => ["business_opportunity", "saas_idea", "automation_idea", "product_improvement", "service_gap", "niche_alert"].includes(o.opportunity_type))
    .map((o) => ({
      source: o.source,
      title: o.title,
      opportunity_type: mapBusinessType(o.opportunity_type),
      niche: o.niche,
      description: o.description,
      evidence_summary: o.evidence_summary,
      monetization_hint: o.monetization_hint,
      urgency: o.urgency,
      confidence: o.confidence,
      score: o.score,
      status: "new",
      trace_id: o.trace_id ?? randomUUID(),
    }));
}

async function persistResearchBrief(brief, { dry_run = false, persist_brief = true } = {}) {
  if (dry_run || !persist_brief) return { inserted: 0, skipped: true };

  const row = {
    title: brief.title,
    summary: brief.summary,
    priority: 1,
    brief_type: "autonomous_opportunity_engine",
  };

  return supabaseInsert("research_briefs", [row], { optional: true });
}

async function persistOpportunityOutputs(opportunities, { dry_run = false, persist_outputs = false } = {}) {
  if (dry_run || !persist_outputs) {
    return {
      business_written: 0,
      grant_written: 0,
      skipped: true,
    };
  }

  const grantRows = mapToGrantRows(opportunities);
  const businessRows = mapToBusinessRows(opportunities);

  const grantWrite = await supabaseInsert("grant_opportunities", grantRows, { optional: true });
  const businessWrite = await supabaseInsert("business_opportunities", businessRows, { optional: true });

  return {
    business_written: businessWrite.inserted ?? 0,
    grant_written: grantWrite.inserted ?? 0,
    skipped: false,
  };
}

export async function runAutonomousOpportunityEngine({
  since_days = 30,
  min_score = 45,
  limit = 20,
  job_type = "opportunity_scan",
  dry_run = false,
  persist_outputs = false,
  persist_brief = true,
  send_telegram = false,
  quiet = false,
} = {}) {
  if (!SUPABASE_URL || !SUPABASE_KEY) {
    throw new Error("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY/SUPABASE_KEY");
  }

  if (!quiet) {
    console.log(
      `[autonomous-opportunity-engine] start job_type=${job_type} since_days=${since_days} min_score=${min_score} limit=${limit} dry_run=${dry_run}`
    );
  }

  const dataset = await loadOpportunityEngineInputs({ since_days });

  const detected = detectOpportunities(dataset, { job_type });
  const ranked = rankOpportunities(detected, { min_score, limit });
  const routed = attachRoutingAndActions(ranked);

  const brief = generateOpportunityBrief(routed, { job_type, top_n: Math.min(limit, 10) });
  const briefWrite = await persistResearchBrief(brief, { dry_run, persist_brief });
  const outputWrite = await persistOpportunityOutputs(routed, { dry_run, persist_outputs });

  let telegram_sent = false;
  if (!dry_run && send_telegram) {
    telegram_sent = await sendOpportunityBriefAlert(brief);
  }

  if (!quiet) {
    console.log(formatBriefForLog(brief));
  }

  return {
    stats: {
      artifacts: dataset.research_artifacts.length,
      claims: dataset.research_claims.length,
      clusters: dataset.research_clusters.length,
      hypotheses: dataset.research_hypotheses.length,
      coverage_gaps: dataset.coverage_gaps.length,
      detected: detected.length,
      ranked: ranked.length,
    },
    opportunities: routed,
    brief,
    writes: {
      brief: briefWrite,
      outputs: outputWrite,
    },
    telegram_sent,
  };
}

export async function runOpportunityEngineJob(payload = {}) {
  return runAutonomousOpportunityEngine(payload);
}

function getArg(args, flag, fallback) {
  const idx = args.indexOf(flag);
  return idx === -1 ? fallback : args[idx + 1];
}

function hasFlag(args, flag) {
  return args.includes(flag);
}

const args = process.argv.slice(2);
const isDirect = process.argv[1]?.endsWith("autonomous_opportunity_engine.js");

if (args.includes("--help")) {
  console.log([
    "Usage: node autonomous_opportunity_engine.js [options]",
    "",
    "Options:",
    "  --since <days>            Lookback window (default: 30)",
    "  --min-score <n>           Minimum score threshold (default: 45)",
    "  --limit <n>               Max opportunities returned (default: 20)",
    "  --job-type <name>         opportunity_scan | grant_opportunity_scan | service_gap_scan | automation_idea_scan | opportunity_brief_generation",
    "  --dry-run                 No writes, no Telegram",
    "  --persist                 Persist business/grant opportunity rows",
    "  --no-brief                Skip writing research_briefs row",
    "  --telegram                Send brief to Telegram",
    "  --quiet                   Reduce console output",
    "  --json                    Output final result as JSON",
    "  --help                    Show this help",
  ].join("\n"));
  process.exit(0);
}

if (isDirect) {
  const sinceRaw = getArg(args, "--since", "30");
  const minScore = Number(getArg(args, "--min-score", "45"));
  const limit = Number(getArg(args, "--limit", "20"));
  const jobType = getArg(args, "--job-type", "opportunity_scan");

  runAutonomousOpportunityEngine({
    since_days: sinceRaw === "all" ? null : Number(sinceRaw),
    min_score: Number.isNaN(minScore) ? 45 : minScore,
    limit: Number.isNaN(limit) ? 20 : limit,
    job_type: jobType,
    dry_run: hasFlag(args, "--dry-run"),
    persist_outputs: hasFlag(args, "--persist"),
    persist_brief: !hasFlag(args, "--no-brief"),
    send_telegram: hasFlag(args, "--telegram"),
    quiet: hasFlag(args, "--quiet"),
  })
    .then((result) => {
      if (hasFlag(args, "--json")) {
        console.log(JSON.stringify(result, null, 2));
      }
    })
    .catch((err) => {
      console.error(`[autonomous-opportunity-engine] fatal: ${err.message}`);
      if (process.env.DEBUG) console.error(err.stack);
      process.exit(1);
    });
}
