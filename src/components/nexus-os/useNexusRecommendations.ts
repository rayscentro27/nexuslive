/**
 * useNexusRecommendations — deterministic, rules-first cross-module recommendation engine.
 *
 * Reads live state from Revenue Hub + Content Studio + approvals and produces
 * structured recommendations. No LLM required for the structure — Hermes only
 * phrases the concise evidence summary in natural language (selective retrieval,
 * not blind row dumping).
 *
 * Safety: read-only. Never executes, publishes, or schedules anything.
 */
import { useCallback, useMemo } from 'react';
import { supabase } from '../../lib/supabase';
import type { RevenueCampaign, ContentItem } from './types';

export type RecIntent =
  | 'revenue_recommendation'
  | 'content_recommendation'
  | 'next_step'
  | 'blocker_diagnosis'
  | 'approval_summary'
  | 'routing'
  | 'money_research'
  | 'general';

export interface NexusRecommendation {
  title: string;
  recommendation: string;
  why: string;
  evidence_summary: string;
  blockers: string[];
  next_action: string;
  approval_needed: boolean;
  confidence: 'high' | 'medium' | 'low';
  source_tables: string[];
  freshness: string;
  roster?: string;   // compact campaign roster (names + readiness + content) for specific Q&A
  // ── graph context (optional; graceful fallback when graph is empty) ──
  graph_context_used?: boolean;
  related_sources_count?: number;
  related_content_count?: number;
  related_approvals_count?: number;
  relationship_summary?: string;
  source_insight_summary?: string;
}

// ── System-map row shapes (read-only, from Phase 1 inventory tables) ───────────
interface RoutingRule {
  task_type: string; preferred_tool: string | null; fallback_tool: string | null;
  preferred_repo: string | null; required_context: string | null;
  safety_gate: string | null; approval_required: boolean; notes: string | null; active: boolean;
}
interface RepoRow { name: string; purpose: string | null; module: string | null; active_state: string | null; risk_level: string | null; }
interface ProcessRow { name: string; status: string | null; purpose: string | null; can_restart: boolean; approval_required: boolean; risk_level: string | null; port: string | null; }
interface CliRow { cli_key: string; command_name: string | null; description: string | null; risk_level: string | null; requires_approval: boolean; cost_risk: string | null; network_risk: string | null; can_run_locally: boolean | null; installed: boolean | null; }
interface ProviderRow { name: string; cost_tier: string | null; is_healthy: boolean | null; priority: number | null; }
interface SystemMap { rules: RoutingRule[]; repos: RepoRow[]; processes: ProcessRow[]; clis: CliRow[]; providers: ProviderRow[]; }

// ── Intent classification (keyword rules, no LLM) ──────────────────────────────

export function classifyIntent(prompt: string): RecIntent {
  const p = prompt.toLowerCase();
  // ── Routing / system-map questions (checked first so "content studio bug" routes
  // to tooling, not content recommendations). Recommend-only; never executes. ──
  if (/\b(restart|reboot|relaunch|kill|stop the|start the|turn (on|off)|bring (up|down))\b/.test(p)
      && /\b(service|process|receiver|worker|tunnel|engine|bot|gateway|trading|ollama|scheduler|router|poller)\b/.test(p)) {
    return 'routing';
  }
  if (/\b(which|what|who)\b/.test(p) && /\b(tool|cli|repo|repository|agent|provider|model|process|service|owns?)\b/.test(p)) return 'routing';
  if (/\b(which ai|what ai|cheapest|route this|handle this task|requires? approval|safe to automate|owns the|own the)\b/.test(p)) return 'routing';
  if (/\b(approv|review today|sign off|pending)\b/.test(p)) return 'approval_summary';
  // ── Money / research questions: what did we discover, what to monetize/publish,
  // is recurring research running, what should I do today to make money ──
  if (/\b(research|discover|discovered|opportunit|monetiz|make money|making money|recurring|next run|scout|topics? did|what did nexus|publish next|what should we publish|to make money)\b/.test(p)) return 'money_research';
  if (/\b(block|stuck|blocked|why can.?t|what.?s stopping|publish[- ]?ready|not ready|ready to publish)\b/.test(p)) return 'blocker_diagnosis';
  // Content questions (incl. "what content is linked to X")
  if (/\b(content|post|draft|publish|video|newsletter|linkedin|youtube|tiktok|reel|script|linked to)\b/.test(p)) return 'content_recommendation';
  // Revenue/campaign questions — incl. named starter programs and "do we have / ready / status"
  if (/\b(money|revenue|earn|monetize|income|paying|profit|cash|campaign|nav|beehiiv|legalzoom|paydex|business credit|affiliate|program|offer|do we have|ready)\b/.test(p)) return 'revenue_recommendation';
  // Source / knowledge questions (Chase source, transcripts, what supports a campaign) → next_step (graph-enriched)
  if (/\b(source|sources|transcript|insight|funding|chase|support|knowledge)\b/.test(p)) return 'next_step';
  // Graph questions route to next_step (which enriches with graph context)
  if (/\b(graph|entit|relationship|knowledge graph|connected|links?)\b/.test(p)) return 'next_step';
  if (/\b(next|today|what should|priorit|focus|do now|status|overview|summar)\b/.test(p)) return 'next_step';
  return 'general';
}

// Whether this intent needs internal evidence at all
export function intentNeedsEvidence(intent: RecIntent): boolean {
  return intent !== 'general';
}

// ── Scoring (mirrors Revenue/Content engines, kept local to avoid coupling) ────

function scoreCampaignReadiness(c: RevenueCampaign): number {
  let s = 0;
  s += { not_applied: 0, applied: 10, pending: 15, approved: 25, rejected: 0, paused: 5 }[c.application_status] ?? 0;
  s += { none: 0, pending: 8, active: 20, expired: 2 }[c.link_status] ?? 0;
  s += { none: 0, draft: 5, review: 10, ready: 20 }[c.landing_page_status] ?? 0;
  if (c.compliance_ok) s += 10;
  if (c.disclosure_ok) s += 8;
  s += Math.min(c.content_queue_count * 3, 12);
  s += { high: 5, medium: 3, low: 1 }[c.priority] ?? 0;
  return Math.min(s, 100);
}

// ── Engine ─────────────────────────────────────────────────────────────────────

export function useNexusRecommendations() {
  // Read minimal slices — selective, not SELECT *
  const gather = useCallback(async () => {
    const [campaignsRes, contentRes, approvalsRes] = await Promise.all([
      supabase
        .from('nexus_os_revenue_campaigns')
        .select('id,program_name,niche,priority,application_status,link_status,landing_page_status,compliance_ok,disclosure_ok,content_queue_count,next_action,archived')
        .eq('archived', false),
      supabase
        .from('nexus_os_content_items')
        .select('id,title,content_type,status,related_campaign_id,priority,compliance_status,disclosure_required,disclosure_added,platform_targets,archived')
        .eq('archived', false),
      supabase
        .from('owner_approval_queue')
        .select('id,action_type,description,priority,status,requested_by,created_at')
        .eq('status', 'pending')
        .order('created_at', { ascending: false })
        .limit(20),
    ]);

    return {
      campaigns: (campaignsRes.data ?? []) as RevenueCampaign[],
      content: (contentRes.data ?? []) as ContentItem[],
      approvals: approvalsRes.data ?? [],
    };
  }, []);

  // Enrich a recommendation with graph context for a specific source row.
  // Graceful: if the graph is empty or the entity isn't synced, returns unchanged.
  const enrichWithGraph = useCallback(async (
    rec: NexusRecommendation,
    sourceTable: string,
    sourceId: string,
  ): Promise<NexusRecommendation> => {
    try {
      const { data: ent } = await supabase
        .from('nexus_os_entities')
        .select('id')
        .eq('source_table', sourceTable)
        .eq('source_id', sourceId)
        .maybeSingle();
      if (!ent) return rec; // not synced to graph yet — fall back silently

      const entId = (ent as { id: string }).id;
      const [outRes, inRes] = await Promise.all([
        supabase.from('nexus_os_relationships').select('relationship,to_entity_id').eq('from_entity_id', entId),
        supabase.from('nexus_os_relationships').select('relationship,from_entity_id').eq('to_entity_id', entId),
      ]);
      const out = outRes.data ?? [];
      const inc = inRes.data ?? [];
      const all = [...out, ...inc];
      if (all.length === 0) return rec;

      const sources = all.filter(r => r.relationship === 'generated_from_source' || r.relationship === 'derived_from' || r.relationship === 'supports').length;
      const contentLinks = out.filter(r => r.relationship === 'belongs_to_campaign').length
        + inc.filter(r => r.relationship === 'belongs_to_campaign').length;
      const approvals = all.filter(r => r.relationship === 'requires_approval' || r.relationship === 'approved_by').length;
      const supportingSourceIds = inc
        .filter(r => r.relationship === 'supports')
        .map(r => r.from_entity_id)
        .filter(Boolean)
        .slice(0, 4);
      let sourceInsightSummary = '';
      if (supportingSourceIds.length > 0) {
        const { data: sourceEntities } = await supabase
          .from('nexus_os_entities')
          .select('name,title,summary')
          .in('id', supportingSourceIds);
        const labels = (sourceEntities ?? [])
          .map(r => {
            const name = String((r as { title?: string | null; name?: string | null }).title || (r as { name?: string | null }).name || '').trim();
            const summary = String((r as { summary?: string | null }).summary || '').trim();
            return summary ? `${name}: ${summary}` : name;
          })
          .filter(Boolean)
          .slice(0, 3);
        if (labels.length > 0) {
          sourceInsightSummary = labels.join('; ');
        }
      }

      return {
        ...rec,
        graph_context_used: true,
        related_sources_count: sources,
        related_content_count: contentLinks,
        related_approvals_count: approvals,
        relationship_summary: `${all.length} graph link(s): ${sources} source, ${contentLinks} content, ${approvals} approval.`,
        source_insight_summary: sourceInsightSummary || undefined,
      };
    } catch {
      return rec;
    }
  }, []);

  // Read compact slices of the system-map tables (read-only) for routing answers.
  // Reuses existing model_providers for AI cost ranking. Graceful: returns empty
  // arrays if a table is unavailable so routing never blocks the chat.
  const gatherSystemMap = useCallback(async (): Promise<SystemMap> => {
    const [rulesRes, reposRes, procRes, cliRes, provRes] = await Promise.all([
      supabase.from('nexus_task_routing_rules')
        .select('task_type,preferred_tool,fallback_tool,preferred_repo,required_context,safety_gate,approval_required,notes,active')
        .eq('active', true),
      supabase.from('nexus_system_repos').select('name,purpose,module,active_state,risk_level'),
      supabase.from('nexus_system_processes').select('name,status,purpose,can_restart,approval_required,risk_level,port'),
      supabase.from('nexus_cli_tools').select('cli_key,command_name,description,risk_level,requires_approval,cost_risk,network_risk,can_run_locally,installed'),
      supabase.from('model_providers').select('name,cost_tier,is_healthy,priority').order('priority', { ascending: true }),
    ]);
    return {
      rules: (rulesRes.data ?? []) as RoutingRule[],
      repos: (reposRes.data ?? []) as RepoRow[],
      processes: (procRes.data ?? []) as ProcessRow[],
      clis: (cliRes.data ?? []) as CliRow[],
      providers: (provRes.data ?? []) as ProviderRow[],
    };
  }, []);

  // Read compact slices of the research pipeline + money loop (read-only).
  // Proposed/draft = NOT approved/published — clearly labeled as such.
  const gatherMoneyResearch = useCallback(async () => {
    const [kiRes, seRes, wrRes, draftRes, campRes, apprRes] = await Promise.all([
      supabase.from('knowledge_items')
        .select('title,quality_score,quality_label,source_url,metadata,created_at')
        .eq('domain', 'monetization').eq('status', 'proposed')
        .order('quality_score', { ascending: false }).limit(8),
      supabase.from('source_extractions')
        .select('video_title,confidence_score,created_at', { count: 'exact', head: false })
        .eq('scout_id', 'monetization_search_scout')
        .order('created_at', { ascending: false }).limit(1),
      supabase.from('worker_recommendations')
        .select('title,category,priority,estimated_value,status')
        .eq('status', 'open').order('created_at', { ascending: false }).limit(5),
      supabase.from('nexus_os_content_items')
        .select('id,title,content_type,status,related_campaign_id', { count: 'exact', head: false })
        .eq('status', 'needs_review').eq('archived', false).limit(8),
      supabase.from('nexus_os_revenue_campaigns')
        .select('program_name,priority,affiliate_link,link_status,disclosure_ok').eq('archived', false),
      supabase.from('owner_approval_queue')
        .select('action_type', { count: 'exact', head: true }).eq('status', 'pending'),
    ]);
    return {
      proposed: kiRes.data ?? [],
      latestDiscovery: (seRes.data?.[0] as { created_at?: string } | undefined)?.created_at ?? null,
      extractionCount: seRes.count ?? null,
      workerRecs: wrRes.data ?? [],
      drafts: draftRes.data ?? [],
      draftCount: draftRes.count ?? (draftRes.data?.length ?? 0),
      campaigns: campRes.data ?? [],
      pendingApprovals: apprRes.count ?? 0,
    };
  }, []);

  // Build the structured recommendation for a given intent.
  // `prompt` is used only by the routing intent for keyword matching.
  const recommend = useCallback(async (intent: RecIntent, prompt = ''): Promise<NexusRecommendation> => {
    const now = new Date().toISOString();

    // ── Routing: recommend tool / repo / CLI / AI provider, recommend-only ──
    if (intent === 'routing') {
      const map = await gatherSystemMap();
      return buildRoutingRec(prompt, map, now);
    }

    // ── Money / research: what did Nexus discover + what to do next ──
    if (intent === 'money_research') {
      const m = await gatherMoneyResearch();
      const topTopics = m.proposed.slice(0, 5)
        .map(t => `${String(t.title).replace(/^\[Proposed\]\s*/, '').slice(0, 60)} (${t.quality_label ?? '?'})`)
        .join('; ');
      const discoveryAge = m.latestDiscovery
        ? `last discovery ${timeAgoShort(m.latestDiscovery)}` : 'no discovery runs yet';
      const navCamp = m.campaigns.find(c => /nav/i.test(String(c.program_name)) && c.affiliate_link);
      const recParts: string[] = [];
      if (m.draftCount > 0) recParts.push(`review the ${m.draftCount} draft${m.draftCount > 1 ? 's' : ''} in Content Studio (none are published)`);
      if (navCamp) recParts.push('Nav has its affiliate link stored — add disclosure, then approve Nav content');
      const recommendation = recParts.length
        ? `Fastest money move: ${recParts.join('; then ')}.`
        : 'Run a research cycle, then review the proposed topics in Content Studio.';
      return {
        title: 'Monetization Research',
        recommendation,
        why: `Recurring research is scheduled every 6h (free YouTube discovery); ${discoveryAge}. `
          + `${m.extractionCount ?? 0} discovery extractions and ${m.proposed.length} proposed topics are waiting for review — all proposed/draft, nothing published.`,
        evidence_summary: `Proposed topics: ${m.proposed.length}; drafts needing review: ${m.draftCount}; `
          + `pending approvals: ${m.pendingApprovals}; open worker recs: ${m.workerRecs.length}.`,
        roster: topTopics ? `Top discovered topics (PROPOSED, not approved): ${topTopics}` : undefined,
        blockers: m.proposed.length === 0 ? ['No proposed research yet — run a cycle'] : [],
        next_action: m.draftCount > 0
          ? 'Open Content Studio, review the strongest 3 drafts, add disclosure, then approve publishing.'
          : 'Open Content Studio and turn the top proposed topics into drafts.',
        approval_needed: true,
        confidence: 'high',
        source_tables: ['knowledge_items', 'source_extractions', 'worker_recommendations', 'nexus_os_content_items', 'owner_approval_queue'],
        freshness: now,
      };
    }

    const { campaigns, content, approvals } = await gather();

    // ── Approval summary (reads REAL owner_approval_queue records) ──
    if (intent === 'approval_summary') {
      if (approvals.length === 0) {
        return {
          title: 'Pending Approvals',
          recommendation: 'No pending approval records right now.',
          why: 'The owner_approval_queue has no pending items.',
          evidence_summary: 'owner_approval_queue: 0 pending.',
          blockers: [],
          next_action: 'If you want to move on revenue, the next item to create is publishing approval for reviewed drafts.',
          approval_needed: false,
          confidence: 'high',
          source_tables: ['owner_approval_queue'],
          freshness: now,
        };
      }
      const urgent = approvals.filter(a => a.priority === 'urgent');
      // Real, itemized list with an approve command per item (id shortened for readability).
      const list = approvals.slice(0, 6).map((a, i) => {
        const id = String(a.id);
        return `${i + 1}. ${a.action_type} — ${String(a.description || '').slice(0, 90)} `
          + `[approve: "Approve approval_id ${id.slice(0, 8)}"]`;
      }).join(' || ');
      return {
        title: 'Pending Approvals',
        recommendation: `You have ${approvals.length} real pending approval${approvals.length > 1 ? 's' : ''}`
          + `${urgent.length ? `, ${urgent.length} urgent` : ''}. Top: ${approvals[0].action_type}.`,
        why: `These are actual owner_approval_queue records — internal/free items are safe to approve; `
          + `publishing, affiliate submission, and credential changes carry external/real-world impact.`,
        evidence_summary: `${approvals.length} pending in owner_approval_queue (${urgent.length} urgent).`,
        roster: `PENDING APPROVALS: ${list}`,
        blockers: [],
        next_action: 'Approve the internal/free items first (e.g. recurring research, draft review); '
          + 'keep publishing/affiliate/credential items pending until you decide. Reply "Approve approval_id <id>".',
        approval_needed: false,
        confidence: 'high',
        source_tables: ['owner_approval_queue'],
        freshness: now,
      };
    }

    // ── Revenue / next-step / content all rank campaigns + content together ──
    const ranked = campaigns
      .map(c => ({ c, score: scoreCampaignReadiness(c), contentCount: content.filter(i => i.related_campaign_id === c.id).length }))
      .sort((a, b) => {
        // priority weight then readiness
        const pw = { high: 2, medium: 1, low: 0 };
        const pd = (pw[b.c.priority] ?? 0) - (pw[a.c.priority] ?? 0);
        return pd !== 0 ? pd : b.score - a.score;
      });

    const top = ranked[0] ?? null;

    // Compact campaign roster (names + readiness + content + status) so specific
    // questions like "do we have Nav ready?" / "what content is linked to Nav?"
    // can be answered precisely from VERIFIED Nexus data.
    const roster = ranked.slice(0, 6)
      .map(r => `${r.c.program_name} [${r.score}% ready, ${r.contentCount} content, ${r.c.application_status}]`)
      .join('; ');

    // ── Content recommendation ──
    if (intent === 'content_recommendation') {
      // Highest-priority campaign with the least content
      const needsContent = [...ranked].sort((a, b) => a.contentCount - b.contentCount)[0];
      if (!needsContent) {
        return emptyRec('No campaigns yet — create one in Revenue Hub first.', now);
      }
      const c = needsContent.c;
      const blockers: string[] = [];
      if (needsContent.contentCount === 0) blockers.push(`Zero content items linked to ${c.program_name}`);
      if (!c.disclosure_ok) blockers.push('Campaign disclosure not confirmed');
      return {
        title: `Content for ${c.program_name}`,
        recommendation: needsContent.contentCount === 0
          ? `${c.program_name} needs content first — it's ${c.priority} priority with zero linked drafts.`
          : `${c.program_name} has ${needsContent.contentCount} draft${needsContent.contentCount > 1 ? 's' : ''}; expand into the platforms it's missing.`,
        why: `${c.program_name} is a ${c.priority}-priority ${c.niche} campaign. Content is the traffic layer that turns it into revenue.`,
        evidence_summary: `${campaigns.length} active campaigns; ${c.program_name} has ${needsContent.contentCount} linked content item(s).`,
        blockers,
        next_action: needsContent.contentCount === 0
          ? `Draft a LinkedIn post, a YouTube Short script, and a newsletter blurb for ${c.program_name}.`
          : `Add the missing platform variations for ${c.program_name}.`,
        approval_needed: true,
        confidence: blockers.length <= 1 ? 'high' : 'medium',
        source_tables: ['nexus_os_revenue_campaigns', 'nexus_os_content_items'],
        freshness: now,
        roster,
      };
    }

    // ── Blocker diagnosis ──
    if (intent === 'blocker_diagnosis') {
      const allBlockers: string[] = [];
      for (const { c, contentCount } of ranked) {
        if (c.application_status === 'not_applied') allBlockers.push(`${c.program_name}: not yet applied`);
        else if (!c.compliance_ok) allBlockers.push(`${c.program_name}: compliance not reviewed`);
        else if (!c.disclosure_ok) allBlockers.push(`${c.program_name}: disclosure not added`);
        else if (contentCount === 0) allBlockers.push(`${c.program_name}: no content drafted`);
      }
      return {
        title: 'Revenue Blockers',
        recommendation: allBlockers.length === 0
          ? 'No structural blockers — campaigns are progressing.'
          : `The top blocker is: ${allBlockers[0]}. Clear it to move the closest campaign forward.`,
        why: allBlockers.length === 0
          ? 'All active campaigns have passed their early gates.'
          : `${allBlockers.length} blocker${allBlockers.length > 1 ? 's' : ''} across ${campaigns.length} campaign${campaigns.length > 1 ? 's' : ''} are slowing revenue.`,
        evidence_summary: allBlockers.slice(0, 5).join('; ') || 'No blockers found.',
        blockers: allBlockers,
        next_action: allBlockers.length === 0 ? 'Keep advancing the top campaign.' : `Resolve: ${allBlockers[0]}`,
        approval_needed: false,
        confidence: 'high',
        source_tables: ['nexus_os_revenue_campaigns', 'nexus_os_content_items'],
        freshness: now,
      };
    }

    // ── Revenue recommendation + next_step (default cross-module) ──
    if (!top) {
      return emptyRec(
        intent === 'revenue_recommendation'
          ? 'No revenue campaigns yet. Create your first campaign in Revenue Hub (Nav, Beehiiv, LegalZoom) to start the engine.'
          : 'No campaigns or content yet. Start in Revenue Hub by creating a campaign, then draft content for it.',
        now,
      );
    }

    const c = top.c;
    const blockers: string[] = [];
    if (c.application_status === 'not_applied') blockers.push('Affiliate application not submitted');
    if (!c.compliance_ok) blockers.push('Compliance not reviewed');
    if (!c.disclosure_ok) blockers.push('Disclosure not added');
    if (top.contentCount === 0) blockers.push('No content drafted');

    let next_action: string;
    let approval_needed = false;
    if (c.application_status === 'not_applied') next_action = `Apply to the ${c.program_name} program.`;
    else if (!c.compliance_ok) next_action = `Complete compliance review for ${c.program_name}.`;
    else if (!c.disclosure_ok) next_action = `Add affiliate disclosure for ${c.program_name}.`;
    else if (top.contentCount === 0) next_action = `Draft 3 content pieces for ${c.program_name} (LinkedIn, YouTube Short, newsletter).`;
    else { next_action = `Request approval to publish ${c.program_name} content.`; approval_needed = true; }

    const baseRec: NexusRecommendation = {
      title: intent === 'revenue_recommendation' ? 'Next Revenue Move' : 'Highest-Impact Next Step',
      recommendation: `${c.program_name} is the strongest next move${blockers.length ? `, but it is blocked by: ${blockers[0]}` : ' — it is ready to push'}.`,
      why: `${c.program_name} is a ${c.priority}-priority ${c.niche} campaign at ${top.score}% launch readiness with ${top.contentCount} linked content item(s). It's the closest safe path to revenue.`,
      evidence_summary: `${campaigns.length} active campaigns, ${content.length} content items, ${approvals.length} pending approvals. Top campaign: ${c.program_name} (${top.score}% ready).`,
      blockers,
      next_action,
      approval_needed,
      confidence: blockers.length <= 1 ? 'high' : blockers.length <= 2 ? 'medium' : 'low',
      source_tables: ['nexus_os_revenue_campaigns', 'nexus_os_content_items', 'owner_approval_queue'],
      freshness: now,
      roster,
    };

    // Enrich with graph context if this campaign is synced to the graph (graceful fallback)
    return enrichWithGraph(baseRec, 'nexus_os_revenue_campaigns', c.id);
  }, [gather, enrichWithGraph, gatherSystemMap, gatherMoneyResearch]);

  // Build a concise evidence string to hand to Hermes (no raw rows, no secrets).
  // Strict budget: each section capped, whole block capped ~1800 chars.
  const buildEvidenceContext = useCallback((rec: NexusRecommendation): string => {
    const cap = (s: string, n: number) => (s && s.length > n ? s.slice(0, n - 1) + '…' : s || '');
    const block = [
      `NEXUS OS EVIDENCE (selective, summarized — not raw rows):`,
      `- Topic: ${cap(rec.title, 80)}`,
      `- Recommendation: ${cap(rec.recommendation, 300)}`,
      `- Reasoning: ${cap(rec.why, 320)}`,
      `- Evidence: ${cap(rec.evidence_summary, 300)}`,
      rec.roster ? `- Campaigns (VERIFIED from Revenue Hub): ${cap(rec.roster, 420)}` : '',
      rec.source_insight_summary ? `- Source insights: ${cap(rec.source_insight_summary, 320)}` : '',
      rec.blockers.length ? `- Blockers: ${cap(rec.blockers.slice(0, 4).join('; '), 300)}` : `- Blockers: none`,
      `- Next action: ${cap(rec.next_action, 200)}`,
      `- Approval needed: ${rec.approval_needed ? 'yes' : 'no'} · Confidence: ${rec.confidence}`,
      rec.graph_context_used
        ? `- Graph: ${cap(rec.relationship_summary ?? '', 200)}`
        : `- Graph: not synced`,
      ``,
      `Treat as VERIFIED internal evidence. Answer in the Hermes voice: recommendation first, then why, then blocker, then approval. No raw rows, no "Supabase", no invented numbers.`,
    ].join('\n');
    // Hard ceiling so a recommendation request never balloons the context budget.
    return block.length > 2400 ? block.slice(0, 2399) + '…' : block;
  }, []);

  // Memoized so consumer effects don't re-run every render (stuck-spinner / loop fix).
  return useMemo(() => ({ recommend, classifyIntent, intentNeedsEvidence, buildEvidenceContext, gather, gatherSystemMap, gatherMoneyResearch, enrichWithGraph }),
    [recommend, buildEvidenceContext, gather, gatherSystemMap, gatherMoneyResearch, enrichWithGraph]);
}

// ── Routing recommendation (read-only; recommends tool/repo/CLI/AI, never executes) ──

const RULE_HINTS: Array<[RegExp, string]> = [
  [/\b(migrat|schema|sql|db table|database table)\b/, 'supabase_migration'],
  [/\b(bug|fix|broken|error|crash|spinner|not working|render|blank)\b/, 'frontend_ui_fix'],
  [/\b(deploy|ship it|go live|netlify|publish (the )?(site|app|nexus))\b/, 'design_polish'],
  [/\b(source intake|intake|transcript)\b/, 'source_intake'],
  [/\b(draft|write.*content|caption|post copy|content piece)\b/, 'content_draft'],
  [/\b(classif|categor|tag|label|cheap)\b/, 'cheap_classification'],
  [/\byoutube\b/, 'youtube_research'],
  [/\b(research|scrape|web search)\b/, 'web_research'],
  [/\b(backtest|strategy test|paper trade)\b/, 'trading_strategy_backtest'],
  [/\b(live trad|real trad|place (a )?trade|broker order)\b/, 'live_trading'],
  [/\b(trading status|receiver status|trade status)\b/, 'trading_status'],
  [/\b(ui|frontend|component|page|react|typescript|css|design)\b/, 'frontend_ui_fix'],
];

function tok(s: string): string[] {
  return (s || '').toLowerCase().split(/[^a-z0-9]+/).filter(Boolean);
}

function timeAgoShort(iso: string): string {
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return 'recently';
  const mins = Math.max(0, Math.round((Date.now() - then) / 60000));
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.round(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.round(hrs / 24)}d ago`;
}

function buildRoutingRec(prompt: string, map: SystemMap, now: string): NexusRecommendation {
  const p = prompt.toLowerCase();
  const ptoks = new Set(tok(prompt));
  const ruleByType = (t: string) => map.rules.find(r => r.task_type === t) || null;
  const gateLine = (r: RoutingRule | null) =>
    r ? `${r.approval_required ? 'Requires your approval' : 'No approval needed'}${r.safety_gate ? ` (${r.safety_gate})` : ''}` : '';

  // ── A. Restart / start / stop a service → recommend only, never execute ──
  if (/\b(restart|reboot|relaunch|kill|stop|start|turn (on|off)|bring (up|down))\b/.test(p)) {
    let best: ProcessRow | null = null, bestScore = 0;
    for (const pr of map.processes) {
      const score = tok(`${pr.name} ${pr.purpose ?? ''}`).filter(t => ptoks.has(t)).length;
      if (score > bestScore) { bestScore = score; best = pr; }
    }
    if (best && bestScore > 0) {
      const proc = best;
      return {
        title: `Service control: ${proc.name}`,
        recommendation: `I won't restart ${proc.name} myself — I only recommend service actions, I don't execute them. It's a ${proc.risk_level ?? 'medium'}-risk process, so you (or an approved operator) should run the restart.`,
        why: `${proc.name} — ${proc.purpose ?? 'service'}. Current status: ${proc.status ?? 'unknown'}${proc.port ? `, port ${proc.port}` : ''}. Restart policy: ${proc.can_restart ? 'auto-allowed' : 'recommend-only'}, approval ${proc.approval_required ? 'required' : 'not required'}.`,
        evidence_summary: `From nexus_system_processes: ${proc.name} (${proc.status ?? 'unknown'}), risk=${proc.risk_level ?? 'medium'}, can_restart=${proc.can_restart}.`,
        blockers: ['Service restarts are recommend-only — I never execute service control, deploys, or trading actions'],
        next_action: `If you want it restarted, run the restart yourself and I'll confirm status. I will not execute it.`,
        approval_needed: true,
        confidence: 'high',
        source_tables: ['nexus_system_processes'],
        freshness: now,
      };
    }
    return {
      title: 'Service control',
      recommendation: `I can tell you a service's status and the safe restart command, but I won't restart, deploy, or run trading actions myself — those are recommend-only.`,
      why: 'Service control is gated for safety; Hermes recommends, you execute.',
      evidence_summary: 'No specific process matched the request in nexus_system_processes.',
      blockers: ['Recommend-only — no execution'],
      next_action: 'Tell me which service (e.g. trading engine, gateway, scheduler) and I\'ll give its status + safe command.',
      approval_needed: true,
      confidence: 'medium',
      source_tables: ['nexus_system_processes'],
      freshness: now,
    };
  }

  // ── B. Cheapest AI / provider / model ──
  if ((/\b(cheap|cheapest|low ?cost|free|local|inexpensive)\b/.test(p) && /\b(ai|model|provider|llm|classif|inference|categor)\b/.test(p))
      || /\b(which ai|what ai|which provider|which model)\b/.test(p)) {
    const order: Record<string, number> = { free: 0, low: 1, medium: 2, high: 3 };
    const ranked = [...map.providers].sort((a, b) => (order[a.cost_tier ?? ''] ?? 9) - (order[b.cost_tier ?? ''] ?? 9));
    const rule = ruleByType('cheap_classification');
    const preferred = rule?.preferred_tool || (ranked[0] ? ranked[0].name : 'Ollama (local)');
    const fallback = rule?.fallback_tool || (ranked[1]?.name ?? 'Groq');
    const tierList = ranked.slice(0, 3).map(r => `${r.name}(${r.cost_tier ?? '?'})`).join(', ') || 'Ollama(free), Groq(low)';
    return {
      title: 'Cheapest AI route',
      recommendation: `Use ${preferred} for the cheapest path — it's local/free and ideal for classification-style work. ${fallback} is the cloud fallback if you need more capability.`,
      why: `Routing rule "cheap_classification" prefers local Ollama, then Groq (low cost). Keeping it local means zero cost and no network risk.`,
      evidence_summary: `nexus_task_routing_rules + model_providers cheapest-first: ${tierList}.`,
      blockers: [],
      next_action: `Run it on ${preferred} locally; only escalate to ${fallback} if quality needs it. No approval needed for local inference.`,
      approval_needed: false,
      confidence: 'high',
      source_tables: ['nexus_task_routing_rules', 'model_providers'],
      freshness: now,
    };
  }

  // ── C. Deploy CLI question → netlify, approval-gated ──
  if (/\b(deploy|ship it|go live|netlify|publish (the )?(site|app|nexus))\b/.test(p) && /\b(cli|tool|command|how do i|which)\b/.test(p)) {
    const cli = map.clis.find(c => c.cli_key === 'netlify');
    const rule = ruleByType('design_polish');
    return {
      title: 'Deploy route',
      recommendation: `Use the ${cli?.cli_key ?? 'netlify'} CLI to deploy the web app (\`netlify deploy --prod\`). I'll recommend it but won't run a production deploy without your approval.`,
      why: `Deploying is a network/prod action (cost=${cli?.cost_risk ?? 'free'}, network=${cli?.network_risk ?? 'high'}); the routing rule gates it behind approval. Build first, then deploy.`,
      evidence_summary: `nexus_cli_tools: netlify (deploy, approval required). For DB changes, supabase CLI is the counterpart (also approval-gated).`,
      blockers: ['Production deploy requires your approval — recommend-only'],
      next_action: `npm run build, then (with your go-ahead) netlify deploy --prod. ${gateLine(rule)}.`,
      approval_needed: true,
      confidence: 'high',
      source_tables: ['nexus_cli_tools', 'nexus_task_routing_rules'],
      freshness: now,
    };
  }

  // ── D. Which repo owns X ──
  if (/\b(repo|repository|owns?|which (project|codebase)|where (is|does|do)|lives?)\b/.test(p)) {
    let best: RepoRow | null = null, bestScore = 0;
    for (const r of map.repos) {
      const score = tok(`${r.name} ${r.purpose ?? ''} ${r.module ?? ''}`).filter(t => ptoks.has(t)).length;
      if (score > bestScore) { bestScore = score; best = r; }
    }
    if (!best || bestScore === 0) {
      if (/\b(intake|router|worker|trading|telegram|migration|scanner|python|signal|research|bot|gateway)\b/.test(p)) best = map.repos.find(r => r.name === 'nexus-ai') ?? best;
      else if (/\b(ui|frontend|page|component|content studio|revenue hub|dashboard|web|react|nexus os)\b/.test(p)) best = map.repos.find(r => r.name === 'nexuslive') ?? best;
      else if (/\b(mobile|expo|app store)\b/.test(p)) best = map.repos.find(r => r.name === 'nexus-mobile') ?? best;
    }
    if (best) {
      const repo = best;
      return {
        title: `Repo owner: ${repo.name}`,
        recommendation: `That lives in **${repo.name}** (${repo.module ?? 'module'}). ${repo.purpose ?? ''}`.trim(),
        why: `Matched against nexus_system_repos by purpose/module. ${repo.name} is ${repo.active_state ?? 'active'} (risk: ${repo.risk_level ?? 'low'}).`,
        evidence_summary: `nexus_system_repos: ${repo.name} — ${repo.purpose ?? 'n/a'} [${repo.active_state ?? 'active'}].`,
        blockers: repo.risk_level === 'secrets-present' ? ['Repo holds secrets — never commit .env/credentials'] : [],
        next_action: `Work in ${repo.name}. Changes that deploy or migrate still need your approval.`,
        approval_needed: false,
        confidence: bestScore > 0 ? 'high' : 'medium',
        source_tables: ['nexus_system_repos'],
        freshness: now,
      };
    }
  }

  // ── E. Default: match a task routing rule for "which tool / CLI / agent" ──
  let matchedType: string | null = null;
  for (const [re, t] of RULE_HINTS) { if (re.test(p)) { matchedType = t; break; } }
  const rule = matchedType ? ruleByType(matchedType) : null;
  if (rule) {
    return {
      title: `Routing: ${rule.task_type.replace(/_/g, ' ')}`,
      recommendation: `I'd route this to ${rule.preferred_tool}${rule.preferred_repo ? ` in ${rule.preferred_repo}` : ''}. ${rule.fallback_tool && rule.fallback_tool !== 'none' ? `Fallback: ${rule.fallback_tool}.` : ''}`.trim(),
      why: `Task type "${rule.task_type}" — ${rule.notes ?? 'matched by routing rules'}.${rule.required_context ? ` Needs: ${rule.required_context}.` : ''}`,
      evidence_summary: `nexus_task_routing_rules: ${rule.task_type} → ${rule.preferred_tool} (fallback ${rule.fallback_tool ?? 'none'}, repo ${rule.preferred_repo ?? 'n/a'}).`,
      blockers: rule.task_type === 'live_trading' ? ['Live trading is DISABLED by default — explicit approval required, nothing executes'] : [],
      next_action: `Use ${rule.preferred_tool}. ${gateLine(rule)}.`,
      approval_needed: rule.approval_required,
      confidence: 'high',
      source_tables: ['nexus_task_routing_rules'],
      freshness: now,
    };
  }

  // ── Fallback: general routing guidance ──
  const examples = map.rules.slice(0, 4).map(r => `${r.task_type}→${r.preferred_tool}`).join('; ');
  return {
    title: 'Task routing',
    recommendation: `Tell me the task and I'll route it to the right tool/repo with its approval gate. I recommend only — I don't execute, deploy, or trade.`,
    why: 'Routing is rules-based from the system map (repos, processes, CLIs, AI providers).',
    evidence_summary: `nexus_task_routing_rules available${examples ? `: ${examples}` : ''}.`,
    blockers: [],
    next_action: 'Describe the task (e.g. "fix a UI bug", "apply a migration", "cheap classification") for a specific route.',
    approval_needed: false,
    confidence: 'medium',
    source_tables: ['nexus_task_routing_rules'],
    freshness: now,
  };
}

// ── helper ────────────────────────────────────────────────────────────────────

function emptyRec(message: string, now: string): NexusRecommendation {
  return {
    title: 'Getting Started',
    recommendation: message,
    why: 'No live campaign or content data exists yet to analyze.',
    evidence_summary: 'No active records found in revenue or content tables.',
    blockers: ['No data yet'],
    next_action: message,
    approval_needed: false,
    confidence: 'medium',
    source_tables: ['nexus_os_revenue_campaigns', 'nexus_os_content_items'],
    freshness: now,
  };
}
