/**
 * useCampaignActions — CRUD for nexus_os_revenue_campaigns + approval/notification flow.
 *
 * Safety contract:
 *   - Does NOT activate affiliate links automatically.
 *   - Does NOT publish landing pages.
 *   - Does NOT send email/outreach.
 *   - Does NOT spend money.
 *   - Risky actions (publish, activate link, run ads) insert into owner_approval_queue
 *     and call the approval-notify Netlify function. Nothing executes.
 */
import { useCallback } from 'react';
import { supabase } from '../../lib/supabase';
import { useAuth } from '../AuthProvider';
import { useApprovalNotifier } from './useApprovalNotifier';
import type { RevenueCampaign, CampaignFormData } from './types';

// Actions that require an approval request before any execution
const RISKY_ACTIONS = new Set([
  'publish_landing_page',
  'activate_affiliate_link',
  'send_outreach',
  'launch_ads',
  'publish_content',
  'public_claim',
  'client_facing_message',
]);

export function useCampaignActions() {
  const { user } = useAuth();
  const { notify } = useApprovalNotifier();

  // ── Read ────────────────────────────────────────────────────────────────────
  const fetchCampaigns = useCallback(async (includeArchived = false): Promise<RevenueCampaign[]> => {
    let q = supabase
      .from('nexus_os_revenue_campaigns')
      .select('*')
      .order('priority', { ascending: false })
      .order('created_at', { ascending: false });

    if (!includeArchived) {
      q = q.eq('archived', false);
    }

    const { data, error } = await q;
    if (error) throw error;
    return (data ?? []) as RevenueCampaign[];
  }, []);

  // ── Create ──────────────────────────────────────────────────────────────────
  const createCampaign = useCallback(async (form: CampaignFormData): Promise<RevenueCampaign> => {
    // Never store affiliate_link if it came in blank
    const payload = {
      ...form,
      affiliate_link: form.affiliate_link?.trim() || null,
      content_queue_count: form.content_queue_count ?? 0,
      archived: false,
    };

    const { data, error } = await supabase
      .from('nexus_os_revenue_campaigns')
      .insert(payload)
      .select()
      .single();

    if (error) throw error;
    return data as RevenueCampaign;
  }, []);

  // ── Update ──────────────────────────────────────────────────────────────────
  const updateCampaign = useCallback(
    async (id: string, changes: Partial<CampaignFormData>): Promise<RevenueCampaign> => {
      const safe = { ...changes };
      // Never overwrite affiliate_link with empty string
      if ('affiliate_link' in safe && !safe.affiliate_link?.trim()) {
        safe.affiliate_link = null;
      }

      const { data, error } = await supabase
        .from('nexus_os_revenue_campaigns')
        .update(safe)
        .eq('id', id)
        .select()
        .single();

      if (error) throw error;
      return data as RevenueCampaign;
    },
    [],
  );

  // ── Archive (soft delete) ───────────────────────────────────────────────────
  const archiveCampaign = useCallback(async (id: string): Promise<void> => {
    const { error } = await supabase
      .from('nexus_os_revenue_campaigns')
      .update({ archived: true })
      .eq('id', id);
    if (error) throw error;
  }, []);

  // ── Request approval for a risky action ────────────────────────────────────
  // Inserts into owner_approval_queue and fires notification. Does NOT execute.
  const requestApproval = useCallback(
    async (
      campaign: RevenueCampaign,
      actionType: string,
      description: string,
      priority: 'urgent' | 'normal' | 'low' = 'normal',
    ): Promise<string | null> => {
      if (!RISKY_ACTIONS.has(actionType)) {
        console.warn('[useCampaignActions] Non-risky action sent to requestApproval:', actionType);
      }

      // Insert into owner_approval_queue
      const { data, error } = await supabase
        .from('owner_approval_queue')
        .insert({
          action_type: actionType,
          description,
          payload: {
            campaign_id: campaign.id,
            campaign_name: campaign.program_name,
            niche: campaign.niche,
          },
          requested_by: 'revenue_hub',
          priority,
          status: 'pending',
          expires_at: null,
        })
        .select('id')
        .single();

      if (error) {
        console.error('[useCampaignActions] Failed to insert approval:', error);
        return null;
      }

      const approvalId = data.id as string;

      // Mark campaign as pending_review
      await supabase
        .from('nexus_os_revenue_campaigns')
        .update({ approval_status: 'pending_review' })
        .eq('id', campaign.id);

      // Notify via approval-notify function (Telegram + Supabase notification)
      await notify({
        approval_id: approvalId,
        action_type: actionType,
        description,
        priority,
        status: 'pending',
        requested_by: 'revenue_hub',
      });

      return approvalId;
    },
    [notify],
  );

  // ── Seed starter campaigns (admin only, triggered by Ray explicitly) ────────
  const seedStarterCampaigns = useCallback(async (): Promise<{ inserted: number; skipped: number }> => {
    const starters: Array<Partial<RevenueCampaign>> = [
      {
        program_name: 'Nav Business Credit',
        niche: 'Business Credit & Funding',
        campaign_type: 'affiliate',
        priority: 'high',
        application_status: 'not_applied',
        link_status: 'none',
        landing_page_status: 'none',
        compliance_ok: false,
        disclosure_ok: false,
        traffic_source: 'Content / SEO / YouTube',
        offer_url: 'https://nav.com',
        next_action: 'Apply to Nav affiliate program, add disclosure page, draft 3 content pieces',
        notes: 'High relevance. Affiliate disclosure required. No earnings claims.',
        approval_status: 'not_required',
        content_queue_count: 0,
        archived: false,
      },
      {
        program_name: 'Beehiiv Newsletter Platform',
        niche: 'Creator / Newsletter Tools',
        campaign_type: 'affiliate',
        priority: 'medium',
        application_status: 'not_applied',
        link_status: 'none',
        landing_page_status: 'none',
        compliance_ok: false,
        disclosure_ok: false,
        traffic_source: 'YouTube / Social',
        offer_url: 'https://beehiiv.com',
        next_action: 'Apply to Beehiiv affiliate program',
        notes: 'Good fit for content-first strategy.',
        approval_status: 'not_required',
        content_queue_count: 0,
        archived: false,
      },
      {
        program_name: 'LegalZoom Business Formation',
        niche: 'Business Formation & Legal',
        campaign_type: 'affiliate',
        priority: 'medium',
        application_status: 'not_applied',
        link_status: 'none',
        landing_page_status: 'none',
        compliance_ok: false,
        disclosure_ok: false,
        traffic_source: 'Content / SEO',
        offer_url: 'https://legalzoom.com',
        next_action: 'Research affiliate terms, verify commission, apply',
        notes: 'Natural pairing with LLC content. Compliance review required.',
        approval_status: 'not_required',
        content_queue_count: 0,
        archived: false,
      },
      {
        program_name: 'Business Credit Builder Tools',
        niche: 'Business Credit / Paydex',
        campaign_type: 'affiliate',
        priority: 'high',
        application_status: 'not_applied',
        link_status: 'none',
        landing_page_status: 'draft',
        compliance_ok: false,
        disclosure_ok: false,
        traffic_source: 'YouTube / Email',
        next_action: 'Identify top program, verify compliance, apply',
        notes: 'High-intent audience. No score claims. Disclosure required.',
        approval_status: 'not_required',
        content_queue_count: 0,
        archived: false,
      },
      {
        program_name: 'Paydex / Business Credit Education',
        niche: 'Business Credit Education',
        campaign_type: 'content',
        priority: 'high',
        application_status: 'not_applied',
        link_status: 'none',
        landing_page_status: 'none',
        compliance_ok: false,
        disclosure_ok: false,
        traffic_source: 'YouTube / SEO',
        next_action: 'Create educational content series. Identify monetization path.',
        notes: 'Educational content first. No score guarantees. No financial outcome claims.',
        approval_status: 'not_required',
        content_queue_count: 0,
        archived: false,
      },
    ];

    let inserted = 0;
    let skipped = 0;

    for (const s of starters) {
      const { error } = await supabase
        .from('nexus_os_revenue_campaigns')
        .insert(s);

      if (error) {
        // Duplicate or constraint — skip silently
        skipped++;
      } else {
        inserted++;
      }
    }

    return { inserted, skipped };
  }, []);

  return {
    fetchCampaigns,
    createCampaign,
    updateCampaign,
    archiveCampaign,
    requestApproval,
    seedStarterCampaigns,
  };
}
