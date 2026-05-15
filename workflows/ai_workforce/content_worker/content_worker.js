#!/usr/bin/env node
// ── Content Worker ─────────────────────────────────────────────────────────────
// Generates content drafts (social posts + newsletter outlines) from
// research_briefs and business_opportunities. All output is DRAFT only.
// No auto-publishing. No social media API access. Human publishes.
//
// Direct run:
//   node content_worker.js [--since <days>] [--dry-run] [--quiet] [--type <social|newsletter|all>]
//
// Queue mode:
//   import { runContentWorker } from "./content_worker.js";
//   await runContentWorker({ since_days: 7, content_type: "all" });
//
// OUTPUT: console + Telegram draft summary (no writes until content_drafts table exists)
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

async function supabaseUpsert(table, rows) {
  if (!rows.length) return;
  const res = await fetch(`${SUPABASE_URL}/rest/v1/${table}`, {
    method: "POST",
    headers: {
      apikey: SUPABASE_KEY,
      Authorization: `Bearer ${SUPABASE_KEY}`,
      "Content-Type": "application/json",
      Prefer: "resolution=merge-duplicates",
    },
    body: JSON.stringify(rows),
  });
  if (!res.ok) {
    const err = await res.text();
    // Graceful failure — table may not exist yet (PGRST205 = schema cache miss)
    if (err.includes("does not exist") || err.includes("relation") || err.includes("PGRST205") || err.includes("schema cache")) {
      console.warn(`[content-worker] Table "${table}" not in schema cache — skipping write. Run docs/SUPABASE_SETUP.sql to create it.`);
      return;
    }
    throw new Error(`Supabase upsert ${table}: ${res.status} ${err}`);
  }
}

// ── Data loaders ──────────────────────────────────────────────────────────────

async function loadRecentBriefs(sinceDays) {
  let path = `research_briefs?select=*&order=created_at.desc&limit=20`;
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

async function loadTopOpportunities(sinceDays) {
  let path = `business_opportunities?status=eq.new&order=score.desc&select=*&limit=10`;
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

async function loadTopGrants(sinceDays) {
  let path = `grant_opportunities?status=eq.new&order=score.desc&select=*&limit=5`;
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

// ── Social post generator ─────────────────────────────────────────────────────

const PLATFORM_LIMITS = { linkedin: 3000, twitter: 280 };

function generateSocialPost(source, platform = "linkedin") {
  const limit = PLATFORM_LIMITS[platform] ?? 3000;
  const title   = source.title ?? source.opportunity_title ?? source.program_name ?? "Insight";
  const summary = (source.body ?? source.summary ?? source.description ?? "").slice(0, 300);
  const topic   = source.topic ?? source.opportunity_type ?? "business";

  const hooks = {
    business_opportunities: "💡 Business Opportunity Alert:",
    grant_research:         "💰 Funding Opportunity:",
    trading:                "📊 Trading Insight:",
    crm_automation:         "🤝 CRM Automation Tip:",
    credit_repair:          "💳 Credit Strategy:",
    default:                "🔍 Nexus Insight:",
  };

  const hook = hooks[topic] ?? hooks.default;

  let post = `${hook}\n\n${title}\n\n${summary}`;

  if (platform === "twitter" && post.length > limit) {
    post = post.slice(0, limit - 4) + "...";
  }

  const hashtags = {
    business_opportunities: "#BusinessGrowth #Entrepreneurship #AI",
    grant_research:         "#SmallBusiness #Grants #Funding",
    trading:                "#Trading #ForexTrading #AI",
    crm_automation:         "#CRM #Automation #GHL",
    credit_repair:          "#CreditRepair #Finance #FCRA",
    default:                "#AI #Business #NexusAI",
  };

  const tags = hashtags[topic] ?? hashtags.default;
  post = `${post}\n\n${tags}`;

  return {
    platform,
    title,
    content: post.slice(0, limit),
    source_type: source.topic ? "brief" : "opportunity",
    source_id: source.id ?? null,
    status: "draft",
    requires_human_approval: true,
  };
}

// ── Newsletter outline generator ──────────────────────────────────────────────

function generateNewsletterOutline(briefs, opportunities, grants) {
  const date = new Date().toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" });

  const sections = [];

  // Intro
  sections.push({
    section: "Subject Line (choose one)",
    content: [
      `🚀 Nexus Weekly: Top Opportunities for ${date}`,
      `💡 This Week in AI Business Intelligence — ${date}`,
      `📊 Your Nexus Brief: Grants, Opportunities & Insights`,
    ].join("\n"),
  });

  // Featured opportunity
  if (opportunities.length) {
    const top = opportunities[0];
    sections.push({
      section: "Featured Opportunity",
      content: [
        `Title: ${top.opportunity_title ?? top.title ?? "Opportunity"}`,
        `Type: ${top.opportunity_type ?? "Business"}`,
        `Score: ${top.score ?? "N/A"}/100`,
        `Why it matters: ${(top.summary ?? top.description ?? "").slice(0, 200)}`,
      ].join("\n"),
    });
  }

  // Grant spotlight
  if (grants.length) {
    const g = grants[0];
    sections.push({
      section: "Grant Spotlight",
      content: [
        `Program: ${g.program_name ?? g.title ?? "Grant"}`,
        `Amount: ${g.funding_amount ?? "See details"}`,
        `Deadline: ${g.deadline ?? "Rolling"}`,
        `Who qualifies: ${(g.eligibility_summary ?? g.description ?? "").slice(0, 150)}`,
      ].join("\n"),
    });
  }

  // Research roundup
  if (briefs.length) {
    sections.push({
      section: "Research Roundup",
      content: briefs.slice(0, 3).map((b, i) =>
        `${i + 1}. ${b.title ?? "Brief"} — ${(b.body ?? b.summary ?? "").slice(0, 100)}...`
      ).join("\n"),
    });
  }

  // CTA
  sections.push({
    section: "Call to Action",
    content: [
      "→ Review the full report at your Nexus dashboard",
      "→ Reply to this email with any questions",
      "→ Forward to a business owner who needs this",
    ].join("\n"),
  });

  return {
    date,
    title: `Nexus Weekly Brief — ${date}`,
    sections,
    opportunity_count: opportunities.length,
    grant_count: grants.length,
    brief_count: briefs.length,
    status: "draft",
    requires_human_approval: true,
  };
}

// ── Display ───────────────────────────────────────────────────────────────────

function displayResults(socialPosts, newsletter, quiet) {
  if (quiet) return;

  console.log("\n╔═══════════════════════════════════════════════════════════╗");
  console.log("║  CONTENT WORKER RESULTS                                   ║");
  console.log("╚═══════════════════════════════════════════════════════════╝");

  if (socialPosts.length) {
    console.log(`\n  📱 Social Posts (${socialPosts.length} drafts):`);
    for (const p of socialPosts.slice(0, 3)) {
      console.log(`\n  [${p.platform.toUpperCase()}] ${p.title}`);
      console.log(`  ${p.content.slice(0, 120)}...`);
    }
  }

  if (newsletter) {
    console.log(`\n  📧 Newsletter Outline: ${newsletter.title}`);
    console.log(`     Sections: ${newsletter.sections.length}`);
    console.log(`     Opportunities: ${newsletter.opportunity_count} | Grants: ${newsletter.grant_count}`);
  }

  console.log("\n  ⚠️  All content is DRAFT — human review required before publishing.\n");
}

// ── Telegram alert ────────────────────────────────────────────────────────────

async function sendContentAlert(socialPosts, newsletter) {
  if (!TELEGRAM_BOT_TOKEN || !TELEGRAM_CHAT_ID) {
    console.warn("[content-worker] Telegram not configured — skipping alert.");
    return;
  }
  if ((process.env.TELEGRAM_AUTO_REPORTS_ENABLED || "false") !== "true") {
    console.log("telegram_policy denied=true reason=manual_only_default");
    return;
  }

  const lines = [
    "📝 *Content Worker Brief*",
    `_${socialPosts.length} social draft(s) generated_`,
    "",
  ];

  if (newsletter) {
    lines.push(`📧 Newsletter outline ready: ${newsletter.title}`);
    lines.push(`   ${newsletter.sections.length} sections | ${newsletter.opportunity_count} opportunities`);
    lines.push("");
  }

  if (socialPosts.length) {
    const sample = socialPosts[0];
    lines.push(`*Sample [${sample.platform}]:*`);
    lines.push(sample.content.slice(0, 200) + "...");
    lines.push("");
  }

  lines.push("⚠️ Drafts only — review before publishing.");

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
    if (res.ok) console.log(`[content-worker] Telegram alert sent (${socialPosts.length} posts).`);
    else console.warn(`[content-worker] Telegram error: ${await res.text()}`);
  } catch (err) {
    console.warn(`[content-worker] Telegram send failed: ${err.message}`);
  }
}

// ── Core worker ───────────────────────────────────────────────────────────────

/**
 * Main ContentWorker execution.
 *
 * @param {Object} [opts]
 * @param {number|null} [opts.since_days=90]
 * @param {boolean} [opts.dry_run=false]
 * @param {boolean} [opts.quiet=false]
 * @param {"social"|"newsletter"|"all"} [opts.content_type="all"]
 * @returns {Promise<{social_posts: Array, newsletter: Object|null}>}
 */
export async function runContentWorker({
  since_days = 90,
  dry_run = false,
  quiet = false,
  content_type = "all",
} = {}) {
  if (!quiet) {
    console.log(`\n[content-worker] Starting — since_days=${since_days} type=${content_type} dry_run=${dry_run}`);
    console.log("[content-worker] Mode: DRAFT ONLY — no auto-publishing");
  }

  // Load data
  const [briefs, opportunities, grants] = await Promise.all([
    loadRecentBriefs(since_days),
    loadTopOpportunities(since_days),
    loadTopGrants(since_days),
  ]);

  if (!quiet) {
    console.log(`[content-worker] Loaded: ${briefs.length} brief(s), ${opportunities.length} opportunity(ies), ${grants.length} grant(s)`);
  }

  if (!briefs.length && !opportunities.length && !grants.length) {
    console.log("[content-worker] No source content found — run research pipeline first.");
    return { social_posts: [], newsletter: null };
  }

  // Generate social posts
  const socialPosts = [];
  if (content_type === "social" || content_type === "all") {
    const sources = [...briefs.slice(0, 3), ...opportunities.slice(0, 3), ...grants.slice(0, 2)];
    for (const src of sources) {
      socialPosts.push(generateSocialPost(src, "linkedin"));
      if (src.topic === "business_opportunities" || opportunities.includes(src)) {
        socialPosts.push(generateSocialPost(src, "twitter"));
      }
    }
    if (!quiet) console.log(`[content-worker] Generated ${socialPosts.length} social post draft(s).`);
  }

  // Generate newsletter outline
  let newsletter = null;
  if (content_type === "newsletter" || content_type === "all") {
    newsletter = generateNewsletterOutline(briefs, opportunities, grants);
    if (!quiet) console.log(`[content-worker] Generated newsletter outline: ${newsletter.sections.length} sections.`);
  }

  displayResults(socialPosts, newsletter, quiet);

  if (dry_run) {
    console.log("[content-worker] DRY RUN — no writes, no Telegram.");
    return { social_posts: socialPosts, newsletter };
  }

  // Persist to content_drafts (silently skips if table doesn't exist yet)
  const now = new Date().toISOString();
  const rows = socialPosts.map((p) => ({
    draft_type:  "social",
    platform:    p.platform,
    title:       p.title,
    content:     p.content,
    source_type: p.source_type,
    source_id:   p.source_id,
    status:      "draft",
    created_at:  now,
  }));

  if (newsletter) {
    rows.push({
      draft_type: "newsletter",
      platform:   "email",
      title:      newsletter.title,
      content:    JSON.stringify(newsletter.sections),
      source_type: "brief",
      source_id:  null,
      status:     "draft",
      created_at: now,
    });
  }

  await supabaseUpsert("content_drafts", rows);

  // Send Telegram summary
  await sendContentAlert(socialPosts, newsletter);

  return { social_posts: socialPosts, newsletter };
}

// ── CLI entry ─────────────────────────────────────────────────────────────────

const args = process.argv.slice(2);

if (args.includes("--help")) {
  console.log([
    "Usage: node content_worker.js [options]",
    "",
    "Generates content drafts from research briefs and opportunities.",
    "",
    "Options:",
    "  --since <days>             Look back N days (default: 7)",
    "  --type <social|newsletter|all>  Content type (default: all)",
    "  --dry-run                  No writes, no Telegram",
    "  --quiet                    Suppress verbose output",
    "  --help                     Show this help",
    "",
    "Output: DRAFT only. Human review and manual publishing required.",
  ].join("\n"));
  process.exit(0);
}

function getArg(flag, def) {
  const idx = args.indexOf(flag);
  return idx !== -1 ? args[idx + 1] : def;
}

const isDirect = process.argv[1]?.endsWith("content_worker.js");
if (isDirect) {
  const since = getArg("--since", "90");
  runContentWorker({
    since_days:   since === "all" ? null : parseInt(since, 10),
    dry_run:      args.includes("--dry-run"),
    quiet:        args.includes("--quiet"),
    content_type: getArg("--type", "all"),
  }).catch((err) => {
    console.error(`[content-worker] Fatal: ${err.message}`);
    process.exit(1);
  });
}
