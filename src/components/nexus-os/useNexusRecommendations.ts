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
import { useCallback } from 'react';
import { supabase } from '../../lib/supabase';
import type { RevenueCampaign, ContentItem } from './types';

export type RecIntent =
  | 'revenue_recommendation'
  | 'content_recommendation'
  | 'next_step'
  | 'blocker_diagnosis'
  | 'approval_summary'
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
  // ── graph context (optional; graceful fallback when graph is empty) ──
  graph_context_used?: boolean;
  related_sources_count?: number;
  related_content_count?: number;
  related_approvals_count?: number;
  relationship_summary?: string;
}

// ── Intent classification (keyword rules, no LLM) ──────────────────────────────

export function classifyIntent(prompt: string): RecIntent {
  const p = prompt.toLowerCase();
  if (/\b(approv|review today|sign off|pending)\b/.test(p)) return 'approval_summary';
  if (/\b(block|stuck|blocked|why can.?t|what.?s stopping)\b/.test(p)) return 'blocker_diagnosis';
  if (/\b(money|revenue|earn|monetize|income|paying|profit|cash)\b/.test(p)) return 'revenue_recommendation';
  if (/\b(content|post|draft|publish|video|newsletter|linkedin|youtube)\b/.test(p)) return 'content_recommendation';
  if (/\b(next|today|what should|priorit|focus|do now)\b/.test(p)) return 'next_step';
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

      const sources = all.filter(r => r.relationship === 'generated_from_source' || r.relationship === 'derived_from').length;
      const contentLinks = out.filter(r => r.relationship === 'belongs_to_campaign').length
        + inc.filter(r => r.relationship === 'belongs_to_campaign').length;
      const approvals = all.filter(r => r.relationship === 'requires_approval' || r.relationship === 'approved_by').length;

      return {
        ...rec,
        graph_context_used: true,
        related_sources_count: sources,
        related_content_count: contentLinks,
        related_approvals_count: approvals,
        relationship_summary: `${all.length} graph link(s): ${sources} source, ${contentLinks} content, ${approvals} approval.`,
      };
    } catch {
      return rec;
    }
  }, []);

  // Build the structured recommendation for a given intent
  const recommend = useCallback(async (intent: RecIntent): Promise<NexusRecommendation> => {
    const { campaigns, content, approvals } = await gather();
    const now = new Date().toISOString();

    // ── Approval summary ──
    if (intent === 'approval_summary') {
      const urgent = approvals.filter(a => a.priority === 'urgent');
      return {
        title: 'Pending Approvals',
        recommendation: approvals.length === 0
          ? 'Nothing needs your approval right now.'
          : `You have ${approvals.length} item${approvals.length > 1 ? 's' : ''} awaiting approval${urgent.length ? `, ${urgent.length} urgent` : ''}. Start with the urgent ones.`,
        why: approvals.length === 0
          ? 'The owner_approval_queue has no pending items.'
          : `Oldest pending: "${approvals[approvals.length - 1].action_type}" requested by ${approvals[approvals.length - 1].requested_by}.`,
        evidence_summary: `${approvals.length} pending in owner_approval_queue (${urgent.length} urgent).`,
        blockers: [],
        next_action: approvals.length === 0 ? 'No action needed.' : 'Open the Approval Center and clear urgent items first.',
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
    };

    // Enrich with graph context if this campaign is synced to the graph (graceful fallback)
    return enrichWithGraph(baseRec, 'nexus_os_revenue_campaigns', c.id);
  }, [gather, enrichWithGraph]);

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
    return block.length > 1800 ? block.slice(0, 1799) + '…' : block;
  }, []);

  return { recommend, classifyIntent, intentNeedsEvidence, buildEvidenceContext, gather, enrichWithGraph };
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
