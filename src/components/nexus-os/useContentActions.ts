/**
 * useContentActions — CRUD for nexus_os_content_items + nexus_os_sources,
 * with approval/notification flow reusing the existing pattern.
 *
 * Safety contract:
 *   - Does NOT publish to any platform.
 *   - Does NOT send newsletters/emails.
 *   - Does NOT schedule social posts.
 *   - Risky publishing actions insert into owner_approval_queue only.
 *   - Affiliate CTAs require disclosure_added=true before requestApproval.
 */
import { useCallback } from 'react';
import { supabase } from '../../lib/supabase';
import { useApprovalNotifier } from './useApprovalNotifier';
import type { ContentItem, ContentItemFormData, ContentSource, ContentRecommendation, RevenueCampaign } from './types';

const RISKY_CONTENT_ACTIONS = new Set([
  'publish_content',
  'schedule_content',
  'send_newsletter',
  'post_to_social',
  'public_affiliate_cta',
  'public_claim',
  'landing_page_copy_publication',
]);

// ── Scoring engine ────────────────────────────────────────────────────────────

export function scoreContentItem(
  item: ContentItem,
  campaign?: RevenueCampaign | null,
): number {
  let s = 0;
  // Title
  if (item.title?.trim()) s += 10;
  // Status progress
  s += { idea: 0, draft: 8, needs_review: 15, approval_requested: 18, approved: 22, scheduled: 25, published: 30, archived: 0 }[item.status] ?? 0;
  // Global draft written
  if (item.global_draft?.trim()) s += 10;
  // Platform variations
  const vars = Array.isArray(item.platform_variations) ? item.platform_variations : [];
  s += Math.min(vars.length * 5, 15);
  // Compliance
  if (item.compliance_status === 'approved') s += 15;
  else if (item.compliance_status === 'in_review') s += 5;
  // Disclosure
  if (item.disclosure_required && item.disclosure_added) s += 8;
  if (item.no_earnings_claims) s += 4;
  if (item.no_guarantees) s += 3;
  // Campaign linked
  if (item.related_campaign_id) s += 5;
  // Campaign priority boost
  if (campaign) {
    s += { high: 10, medium: 5, low: 2 }[campaign.priority] ?? 0;
  }
  // Own priority
  s += { high: 5, medium: 3, low: 1 }[item.priority] ?? 0;
  return Math.min(s, 100);
}

export function buildContentRecommendation(
  item: ContentItem,
  campaign?: RevenueCampaign | null,
): ContentRecommendation {
  const blockers: string[] = [];
  let next_action = item.next_action || 'Define the next content action.';
  let approval_needed = false;
  let approval_action: string | undefined;

  if (!item.global_draft?.trim()) blockers.push('No global draft written');
  if (item.compliance_status === 'not_reviewed') blockers.push('Compliance review not started');
  if (item.disclosure_required && !item.disclosure_added) blockers.push('Affiliate disclosure not added');
  if (!item.no_earnings_claims) blockers.push('Earnings claims check not confirmed');
  if (!item.no_guarantees) blockers.push('No-guarantees check not confirmed');
  const vars = Array.isArray(item.platform_variations) ? item.platform_variations : [];
  if (vars.length === 0) blockers.push('No platform variations drafted');
  if (campaign && campaign.application_status === 'not_applied') {
    blockers.push(`Linked campaign "${campaign.program_name}" not yet applied`);
  }

  // Derive specific next_action
  if (!item.global_draft?.trim()) {
    next_action = `Write the global draft for "${item.title}"`;
  } else if (item.compliance_status === 'not_reviewed') {
    next_action = `Complete compliance review — confirm no earnings claims, no guarantees, disclosure added`;
  } else if (item.disclosure_required && !item.disclosure_added) {
    next_action = `Add affiliate/sponsored disclosure to all variations of "${item.title}"`;
  } else if (vars.length === 0) {
    const targets = Array.isArray(item.platform_targets) ? item.platform_targets : [];
    next_action = `Draft platform variations for: ${targets.slice(0, 3).join(', ') || 'YouTube Shorts, LinkedIn'}`;
  } else if (item.status === 'draft') {
    next_action = `Submit "${item.title}" for review — mark as needs_review`;
  } else if (item.status === 'needs_review' || item.status === 'approval_requested') {
    next_action = `Request approval to publish "${item.title}"`;
    approval_needed = true;
    approval_action = 'publish_content';
  } else if (item.status === 'approved') {
    next_action = `Schedule or publish "${item.title}" — approval required`;
    approval_needed = true;
    approval_action = 'schedule_content';
  }

  const score = scoreContentItem(item, campaign);
  const confidence: ContentRecommendation['confidence'] =
    blockers.length === 0 ? 'high' : blockers.length <= 2 ? 'medium' : 'low';

  const campaignNote = campaign ? ` (linked to ${campaign.program_name}, ${campaign.priority} priority)` : '';
  const why = blockers.length === 0
    ? `"${item.title}" is fully prepared and ready for approval to publish.`
    : `"${item.title}" is ${score}% ready${campaignNote}. ${blockers.length} blocker${blockers.length > 1 ? 's' : ''}: ${blockers.slice(0, 2).join('; ')}.`;

  return {
    item_id: item.id,
    item_title: item.title,
    score,
    next_action,
    why,
    blockers,
    approval_needed,
    approval_action,
    confidence,
    source: 'rules_engine',
    freshness: new Date().toISOString(),
  };
}

// ── Hook ──────────────────────────────────────────────────────────────────────

export function useContentActions() {
  const { notify } = useApprovalNotifier();

  // ── Fetch content items ──────────────────────────────────────────────────
  const fetchItems = useCallback(async (includeArchived = false): Promise<ContentItem[]> => {
    let q = supabase
      .from('nexus_os_content_items')
      .select('*')
      .order('priority', { ascending: false })
      .order('created_at', { ascending: false });

    if (!includeArchived) q = q.eq('archived', false);

    const { data, error } = await q;
    if (error) throw error;

    return (data ?? []).map(row => ({
      ...row,
      platform_variations: Array.isArray(row.platform_variations) ? row.platform_variations : [],
      platform_targets: Array.isArray(row.platform_targets) ? row.platform_targets : [],
    })) as ContentItem[];
  }, []);

  // ── Fetch sources ────────────────────────────────────────────────────────
  const fetchSources = useCallback(async (): Promise<ContentSource[]> => {
    const { data, error } = await supabase
      .from('nexus_os_sources')
      .select('*')
      .neq('status', 'archived')
      .order('created_at', { ascending: false })
      .limit(30);
    if (error) throw error;
    return (data ?? []).map(row => ({
      ...row,
      ideas: Array.isArray(row.ideas) ? row.ideas : [],
      tags: Array.isArray(row.tags) ? row.tags : [],
    })) as ContentSource[];
  }, []);

  // ── Fetch campaigns for the campaign selector ─────────────────────────────
  const fetchCampaigns = useCallback(async (): Promise<Array<{ id: string; program_name: string; priority: string }>> => {
    const { data } = await supabase
      .from('nexus_os_revenue_campaigns')
      .select('id, program_name, priority')
      .eq('archived', false)
      .order('priority', { ascending: false })
      .limit(50);
    return data ?? [];
  }, []);

  // ── Create content item ──────────────────────────────────────────────────
  const createItem = useCallback(async (form: ContentItemFormData): Promise<ContentItem> => {
    const payload = {
      ...form,
      type: form.content_type || form.type || 'other',  // keep legacy column in sync
      platform_variations: form.platform_variations ?? [],
      platform_targets: form.platform_targets ?? [],
      archived: false,
    };

    const { data, error } = await supabase
      .from('nexus_os_content_items')
      .insert(payload)
      .select()
      .single();

    if (error) throw error;
    const row = data as Record<string, unknown>;
    return {
      ...row,
      platform_variations: Array.isArray(row.platform_variations) ? row.platform_variations : [],
      platform_targets: Array.isArray(row.platform_targets) ? row.platform_targets : [],
    } as ContentItem;
  }, []);

  // ── Update content item ──────────────────────────────────────────────────
  const updateItem = useCallback(async (id: string, changes: Partial<ContentItemFormData>): Promise<ContentItem> => {
    const safe: Record<string, unknown> = { ...changes };
    // Keep legacy 'type' in sync if content_type changes
    if (changes.content_type) safe.type = changes.content_type;

    const { data, error } = await supabase
      .from('nexus_os_content_items')
      .update(safe)
      .eq('id', id)
      .select()
      .single();

    if (error) throw error;
    const row = data as Record<string, unknown>;
    return {
      ...row,
      platform_variations: Array.isArray(row.platform_variations) ? row.platform_variations : [],
      platform_targets: Array.isArray(row.platform_targets) ? row.platform_targets : [],
    } as ContentItem;
  }, []);

  // ── Archive (soft delete) ────────────────────────────────────────────────
  const archiveItem = useCallback(async (id: string): Promise<void> => {
    const { error } = await supabase
      .from('nexus_os_content_items')
      .update({ archived: true, status: 'archived' })
      .eq('id', id);
    if (error) throw error;
  }, []);

  // ── Create source ────────────────────────────────────────────────────────
  const createSource = useCallback(async (source: {
    title: string;
    type: string;
    content_url?: string;
    summary?: string;
    tags?: string[];
  }): Promise<ContentSource> => {
    const { data, error } = await supabase
      .from('nexus_os_sources')
      .insert({
        ...source,
        status: 'ingested',
        ideas: [],
        tags: source.tags ?? [],
        created_by: 'ray',
      })
      .select()
      .single();

    if (error) throw error;
    const row = data as Record<string, unknown>;
    return {
      ...row,
      ideas: Array.isArray(row.ideas) ? row.ideas : [],
      tags: Array.isArray(row.tags) ? row.tags : [],
    } as ContentSource;
  }, []);

  // ── Request approval for a risky publishing action ────────────────────────
  const requestApproval = useCallback(async (
    item: ContentItem,
    actionType: string,
    description: string,
    priority: 'urgent' | 'normal' | 'low' = 'normal',
  ): Promise<string | null> => {
    if (!RISKY_CONTENT_ACTIONS.has(actionType)) {
      console.warn('[useContentActions] Non-risky action:', actionType);
    }

    const { data, error } = await supabase
      .from('owner_approval_queue')
      .insert({
        action_type: actionType,
        description,
        payload: {
          content_item_id: item.id,
          title: item.title,
          platforms: item.platform_targets,
          related_campaign_id: item.related_campaign_id ?? null,
          compliance_status: item.compliance_status,
          disclosure_added: item.disclosure_added,
          no_earnings_claims: item.no_earnings_claims,
        },
        requested_by: 'content_studio',
        priority,
        status: 'pending',
        expires_at: null,
      })
      .select('id')
      .single();

    if (error) {
      console.error('[useContentActions] Approval insert failed:', error);
      return null;
    }

    const approvalId = data.id as string;

    // Mark item as pending_review + store approval_id
    await supabase
      .from('nexus_os_content_items')
      .update({ approval_status: 'pending_review', approval_id: approvalId, status: 'approval_requested' })
      .eq('id', item.id);

    // If related campaign exists, bump its content_queue_count (read-then-update)
    if (item.related_campaign_id) {
      try {
        const { data: c } = await supabase
          .from('nexus_os_revenue_campaigns')
          .select('content_queue_count')
          .eq('id', item.related_campaign_id)
          .single();
        if (c) {
          const current = (c as { content_queue_count: number }).content_queue_count ?? 0;
          await supabase
            .from('nexus_os_revenue_campaigns')
            .update({ content_queue_count: current + 1 })
            .eq('id', item.related_campaign_id);
        }
      } catch (e) {
        console.warn('[useContentActions] content_queue_count update skipped:', e);
      }
    }

    // Fire notification
    await notify({
      approval_id: approvalId,
      action_type: actionType,
      description,
      priority,
      status: 'pending',
      requested_by: 'content_studio',
    });

    return approvalId;
  }, [notify]);

  return {
    fetchItems,
    fetchSources,
    fetchCampaigns,
    createItem,
    updateItem,
    archiveItem,
    createSource,
    requestApproval,
    buildContentRecommendation,
    scoreContentItem,
  };
}
