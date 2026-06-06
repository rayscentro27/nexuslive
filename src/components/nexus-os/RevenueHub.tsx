import React, { useEffect, useState, useCallback } from 'react';
import {
  DollarSign, TrendingUp, Users, Target, AlertTriangle,
  CheckCircle2, Clock, Loader2, Plus, Edit2, Archive,
  RefreshCw, Zap, ShieldCheck, ChevronDown, ChevronUp,
  Info, BookOpen, BarChart3,
} from 'lucide-react';
import { supabase } from '../../lib/supabase';
import { OSSection, OSCard, Badge, timeAgo, EmptyState } from './shared';
import { CampaignModal } from './CampaignModal';
import { useCampaignActions } from './useCampaignActions';
import type { RevenueCampaign, CampaignFormData, RevenueRecommendation, Lead, RevenueEvent } from './types';

// ── Rules-based Next Best Revenue Action engine ────────────────────────────

function scoreCampaign(c: RevenueCampaign): number {
  let s = 0;
  // Application progress
  s += { not_applied: 0, applied: 10, pending: 15, approved: 25, rejected: 0, paused: 5 }[c.application_status] ?? 0;
  // Affiliate link
  s += { none: 0, pending: 8, active: 20, expired: 2 }[c.link_status] ?? 0;
  // Landing page
  s += { none: 0, draft: 5, review: 10, ready: 20 }[c.landing_page_status] ?? 0;
  // Compliance
  if (c.compliance_ok) s += 10;
  if (c.disclosure_ok) s += 8;
  // Content
  s += Math.min(c.content_queue_count * 3, 12);
  // Priority
  s += { high: 5, medium: 3, low: 1 }[c.priority] ?? 0;
  return Math.min(s, 100);
}

function buildRecommendation(c: RevenueCampaign): RevenueRecommendation {
  const blockers: string[] = [];
  let next_action = c.next_action || 'Define next action for this campaign.';
  let approval_needed = false;
  let approval_action: string | undefined;

  if (c.application_status === 'not_applied') blockers.push('Affiliate application not submitted');
  if (!c.compliance_ok) blockers.push('Compliance review not complete');
  if (!c.disclosure_ok) blockers.push('Affiliate disclosure not added');
  if (c.landing_page_status === 'none') blockers.push('No landing page exists');
  if (c.link_status === 'none' && c.application_status === 'approved') blockers.push('Affiliate link not obtained');
  if (c.content_queue_count === 0) blockers.push('No content in queue');

  // Derive specific recommended action
  if (c.application_status === 'not_applied') {
    next_action = `Apply to the ${c.program_name} affiliate program`;
  } else if (!c.compliance_ok) {
    next_action = `Complete compliance review for ${c.program_name}`;
  } else if (!c.disclosure_ok) {
    next_action = `Add affiliate disclosure to all ${c.program_name} content and pages`;
  } else if (c.landing_page_status === 'none') {
    next_action = `Create a landing page draft for ${c.program_name}`;
    approval_needed = true;
    approval_action = 'publish_landing_page';
  } else if (c.landing_page_status === 'draft') {
    next_action = `Finish the landing page and submit for compliance review`;
    approval_needed = true;
    approval_action = 'publish_landing_page';
  } else if (c.link_status === 'none' && c.application_status === 'approved') {
    next_action = `Obtain affiliate link for ${c.program_name} — requires approval to activate`;
    approval_needed = true;
    approval_action = 'activate_affiliate_link';
  } else if (c.content_queue_count === 0) {
    next_action = `Queue at least 3 content pieces for ${c.program_name}`;
  } else if (c.link_status === 'active' && c.landing_page_status === 'ready') {
    next_action = `Campaign ready — request approval to publish and distribute`;
    approval_needed = true;
    approval_action = 'publish_content';
  }

  const score = scoreCampaign(c);
  const confidence: RevenueRecommendation['confidence'] =
    blockers.length === 0 ? 'high' : blockers.length <= 2 ? 'medium' : 'low';

  const why = blockers.length === 0
    ? `${c.program_name} has all prerequisites met and is ready to launch.`
    : `${c.program_name} is ${score}% ready. ${blockers.length} blocker${blockers.length > 1 ? 's' : ''} remain: ${blockers.slice(0, 2).join('; ')}.`;

  return {
    campaign_id: c.id,
    campaign_name: c.program_name,
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

// ── Component ─────────────────────────────────────────────────────────────────

export function RevenueHub() {
  const [campaigns, setCampaigns] = useState<RevenueCampaign[]>([]);
  const [leads, setLeads] = useState<Lead[]>([]);
  const [revenueEvents, setRevenueEvents] = useState<RevenueEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [showArchived, setShowArchived] = useState(false);
  const [modal, setModal] = useState<{ mode: 'create' | 'edit'; campaign?: RevenueCampaign } | null>(null);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [approvalLoading, setApprovalLoading] = useState<string | null>(null);
  const [approvalFeedback, setApprovalFeedback] = useState<Record<string, string>>({});
  const [seeding, setSeeding] = useState(false);
  const [seedResult, setSeedResult] = useState<string | null>(null);

  const actions = useCampaignActions();

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [campaigns, leadsRes, revenueRes] = await Promise.all([
        actions.fetchCampaigns(showArchived),
        supabase.from('leads').select('id,name,business_name,status,lead_score,estimated_value,created_at')
          .order('created_at', { ascending: false }).limit(8),
        supabase.from('revenue_events').select('id,event_type,amount,currency,created_at')
          .order('created_at', { ascending: false }).limit(20),
      ]);
      setCampaigns(campaigns);
      if (leadsRes.data) setLeads(leadsRes.data as Lead[]);
      if (revenueRes.data) setRevenueEvents(revenueRes.data as RevenueEvent[]);
    } catch (err) {
      console.error('[RevenueHub] load error:', err);
    } finally {
      setLoading(false);
    }
  }, [showArchived, actions]);

  useEffect(() => { load(); }, [load]);

  // Build recommendations ranked by score desc
  const recommendations = campaigns
    .filter(c => !c.archived)
    .map(buildRecommendation)
    .sort((a, b) => b.score - a.score);

  const topRec = recommendations[0] ?? null;

  // KPIs
  const totalRevenue = revenueEvents.reduce((s, e) => s + (e.amount ?? 0), 0);
  const activeCampaigns = campaigns.filter(c => c.application_status === 'approved' && !c.archived).length;
  const pendingApprovals = campaigns.filter(c => c.approval_status === 'pending_review').length;
  const hotLeads = leads.filter(l => l.lead_score >= 70).length;

  async function handleSave(data: CampaignFormData) {
    if (modal?.mode === 'create') {
      const created = await actions.createCampaign(data);
      setCampaigns(prev => [created, ...prev]);
    } else if (modal?.campaign) {
      const updated = await actions.updateCampaign(modal.campaign.id, data);
      setCampaigns(prev => prev.map(c => c.id === updated.id ? updated : c));
    }
  }

  async function handleArchive(id: string) {
    if (!confirm('Archive this campaign? It can be restored by enabling "Show archived".')) return;
    await actions.archiveCampaign(id);
    setCampaigns(prev => prev.filter(c => c.id !== id));
  }

  async function handleRequestApproval(campaign: RevenueCampaign, rec: RevenueRecommendation) {
    if (!rec.approval_action) return;
    setApprovalLoading(campaign.id);
    try {
      const approvalId = await actions.requestApproval(
        campaign,
        rec.approval_action,
        `${rec.campaign_name}: ${rec.next_action}`,
        campaign.priority === 'high' ? 'urgent' : 'normal',
      );
      setApprovalFeedback(prev => ({
        ...prev,
        [campaign.id]: approvalId
          ? `Approval request created (ID: ${approvalId.slice(0, 8)}) — check Approval Center`
          : 'Approval request failed — check logs',
      }));
      // Update local state
      setCampaigns(prev => prev.map(c =>
        c.id === campaign.id ? { ...c, approval_status: 'pending_review' } : c,
      ));
    } catch (err) {
      setApprovalFeedback(prev => ({ ...prev, [campaign.id]: `Error: ${String(err)}` }));
    } finally {
      setApprovalLoading(null);
    }
  }

  async function handleSeedStarters() {
    if (!confirm('Create starter campaigns (Nav, Beehiiv, LegalZoom, etc.)? Duplicates will be skipped.')) return;
    setSeeding(true);
    try {
      const { inserted, skipped } = await actions.seedStarterCampaigns();
      setSeedResult(`${inserted} created, ${skipped} skipped (already existed)`);
      await load();
    } catch (err) {
      setSeedResult(`Error: ${String(err)}`);
    } finally {
      setSeeding(false);
    }
  }

  function toggleExpand(id: string) {
    setExpanded(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h2 className="text-xl font-black text-[#1A2244]">
            Revenue <span className="text-[#5B7CFA]">Hub</span>
          </h2>
          <p className="text-slate-400 text-xs mt-0.5">
            Live from Supabase · nexus_os_revenue_campaigns · {campaigns.length} campaigns
          </p>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <button onClick={load} disabled={loading}
            className="flex items-center gap-1 px-3 py-1.5 rounded-xl bg-white border border-slate-200 text-slate-500 text-xs font-bold hover:bg-slate-50 disabled:opacity-50 transition-all">
            {loading ? <Loader2 className="w-3 h-3 animate-spin" /> : <RefreshCw className="w-3 h-3" />}
          </button>
          <label className="flex items-center gap-1.5 text-xs text-slate-500 cursor-pointer select-none">
            <input type="checkbox" checked={showArchived} onChange={e => setShowArchived(e.target.checked)} className="w-3 h-3 rounded accent-[#5B7CFA]" />
            Show archived
          </label>
          {campaigns.length === 0 && !loading && (
            <button onClick={handleSeedStarters} disabled={seeding}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-100 text-slate-600 text-xs font-bold hover:bg-slate-200 disabled:opacity-50 transition-all">
              {seeding ? <Loader2 className="w-3 h-3 animate-spin" /> : <BookOpen className="w-3 h-3" />}
              Create starter campaigns
            </button>
          )}
          <button onClick={() => setModal({ mode: 'create' })}
            className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-[#5B7CFA] text-white text-xs font-black hover:bg-[#4A6BEB] transition-all shadow">
            <Plus className="w-3.5 h-3.5" />
            Add Campaign
          </button>
        </div>
      </div>

      {seedResult && (
        <p className="text-xs text-slate-500 italic px-1">{seedResult}</p>
      )}

      {/* Safety guardrail */}
      <div className="flex items-start gap-2 p-3 rounded-xl bg-amber-50 border border-amber-200">
        <AlertTriangle className="w-4 h-4 text-amber-500 shrink-0 mt-0.5" />
        <p className="text-xs text-amber-700 font-medium">
          No publishing, link activation, email/outreach, or ad spend without explicit approval.
          Affiliate disclosure required. No earnings claims. Risky actions create an approval request only.
        </p>
      </div>

      {/* KPI row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <KPICard icon={Target} label="Campaigns" value={String(campaigns.filter(c => !c.archived).length)} sub="Active in pipeline" color="blue" />
        <KPICard icon={CheckCircle2} label="Approved" value={String(activeCampaigns)} sub="Application approved" color="green" />
        <KPICard icon={DollarSign} label="Revenue Events" value={`$${totalRevenue.toFixed(0)}`} sub={`${revenueEvents.length} events`} color="green" />
        <KPICard icon={Users} label="Hot Leads" value={String(hotLeads)} sub="Score ≥ 70" color="amber"
          onClick={() => {}} />
      </div>

      {/* Main grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Campaign list — 2/3 width */}
        <div className="lg:col-span-2 space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-black text-[#1A2244] uppercase tracking-widest">Campaigns</h3>
            {pendingApprovals > 0 && (
              <Badge label={`${pendingApprovals} awaiting approval`} variant="warn" />
            )}
          </div>

          {loading ? (
            <div className="flex items-center justify-center py-16">
              <Loader2 className="w-6 h-6 animate-spin text-slate-300" />
            </div>
          ) : campaigns.length === 0 ? (
            <EmptyState icon={Target} message="No campaigns yet — add one or create starter campaigns" />
          ) : (
            campaigns.map(c => (
              <CampaignCard
                key={c.id}
                campaign={c}
                recommendation={recommendations.find(r => r.campaign_id === c.id)}
                expanded={expanded.has(c.id)}
                onToggle={() => toggleExpand(c.id)}
                onEdit={() => setModal({ mode: 'edit', campaign: c })}
                onArchive={() => handleArchive(c.id)}
                onRequestApproval={rec => handleRequestApproval(c, rec)}
                approvalLoading={approvalLoading === c.id}
                approvalFeedback={approvalFeedback[c.id]}
              />
            ))
          )}
        </div>

        {/* Right sidebar — 1/3 width */}
        <div className="space-y-4">
          {/* Next Best Revenue Action */}
          <OSSection title="Next Best Action" icon={Zap}>
            {!topRec ? (
              <EmptyState icon={Zap} message="Add campaigns to get recommendations" />
            ) : (
              <NextBestAction rec={topRec} campaigns={campaigns}
                onRequestApproval={rec => {
                  const c = campaigns.find(x => x.id === rec.campaign_id);
                  if (c) handleRequestApproval(c, rec);
                }}
                approvalLoading={approvalLoading !== null} />
            )}
          </OSSection>

          {/* Revenue events */}
          <OSSection title="Revenue Events" icon={DollarSign} action={
            <Badge label={`${revenueEvents.length}`} variant="success" />
          }>
            {revenueEvents.length === 0 ? (
              <EmptyState icon={DollarSign} message="No revenue events yet" />
            ) : (
              <div className="space-y-2">
                {revenueEvents.slice(0, 5).map(e => (
                  <div key={e.id} className="flex items-center justify-between gap-2 py-1">
                    <div>
                      <p className="text-xs font-semibold text-[#1A2244]">{e.event_type}</p>
                      <p className="text-[10px] text-slate-400">{timeAgo(e.created_at)}</p>
                    </div>
                    <span className="text-sm font-black text-green-600">
                      ${(e.amount ?? 0).toFixed(2)}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </OSSection>

          {/* Lead pipeline */}
          <OSSection title="Lead Pipeline" icon={Users} action={
            <Badge label={`${leads.length}`} variant="info" />
          }>
            {leads.length === 0 ? (
              <EmptyState icon={Users} message="No leads yet" />
            ) : (
              <div className="space-y-1.5">
                {leads.slice(0, 5).map(l => (
                  <div key={l.id} className="flex items-center gap-2">
                    <div className={`w-2 h-2 rounded-full shrink-0 ${
                      l.lead_score >= 70 ? 'bg-green-500' : l.lead_score >= 40 ? 'bg-amber-400' : 'bg-slate-300'
                    }`} />
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-semibold text-[#1A2244] truncate">
                        {l.name ?? l.business_name ?? 'Unnamed'}
                      </p>
                      <p className="text-[10px] text-slate-400">{l.status} · score {l.lead_score}</p>
                    </div>
                    {l.estimated_value && (
                      <span className="text-xs font-bold text-green-600 shrink-0">
                        ${l.estimated_value.toLocaleString()}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            )}
          </OSSection>
        </div>
      </div>

      {/* Create/Edit Modal */}
      {modal && (
        <CampaignModal
          mode={modal.mode}
          initial={modal.campaign ?? null}
          onSave={handleSave}
          onClose={() => setModal(null)}
        />
      )}
    </div>
  );
}

// ── Campaign card ─────────────────────────────────────────────────────────────

function CampaignCard({
  campaign: c, recommendation: rec, expanded, onToggle,
  onEdit, onArchive, onRequestApproval, approvalLoading, approvalFeedback,
}: {
  campaign: RevenueCampaign;
  recommendation?: RevenueRecommendation;
  expanded: boolean;
  onToggle: () => void;
  onEdit: () => void;
  onArchive: () => void;
  onRequestApproval: (rec: RevenueRecommendation) => void;
  approvalLoading: boolean;
  approvalFeedback?: string;
}) {
  const score = rec?.score ?? 0;
  const barColor = score >= 70 ? 'bg-green-500' : score >= 40 ? 'bg-amber-400' : 'bg-slate-300';

  return (
    <div className={`bg-white border rounded-2xl shadow-sm overflow-hidden ${
      c.archived ? 'border-slate-100 opacity-60' : 'border-slate-200'
    }`}>
      <button onClick={onToggle} className="w-full flex items-center gap-3 px-5 py-4 text-left hover:bg-slate-50/50 transition-colors">
        {/* Score ring */}
        <div className="relative w-10 h-10 shrink-0">
          <svg className="w-10 h-10 -rotate-90" viewBox="0 0 36 36">
            <circle cx="18" cy="18" r="15.5" fill="none" stroke="#eaebf6" strokeWidth="3" />
            <circle cx="18" cy="18" r="15.5" fill="none"
              stroke={score >= 70 ? '#22c55e' : score >= 40 ? '#f59e0b' : '#cbd5e1'}
              strokeWidth="3"
              strokeDasharray={`${(score / 100) * 97.4} 97.4`}
              strokeLinecap="round" />
          </svg>
          <span className="absolute inset-0 flex items-center justify-center text-[10px] font-black text-[#1A2244]">
            {score}
          </span>
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <p className="text-sm font-black text-[#1A2244]">{c.program_name}</p>
            <PriorityPill priority={c.priority} />
            <ApplicationPill status={c.application_status} />
            {c.archived && <Badge label="Archived" variant="default" />}
            {c.approval_status === 'pending_review' && <Badge label="Approval pending" variant="warn" />}
          </div>
          <p className="text-xs text-slate-500 mt-0.5">{c.niche} · {c.campaign_type}</p>
          {rec && (
            <p className="text-[10px] text-[#5B7CFA] mt-1 font-semibold line-clamp-1">→ {rec.next_action}</p>
          )}
        </div>

        {expanded ? <ChevronUp className="w-4 h-4 text-slate-400 shrink-0" /> : <ChevronDown className="w-4 h-4 text-slate-400 shrink-0" />}
      </button>

      {expanded && (
        <div className="px-5 pb-5 border-t border-slate-100 pt-4 space-y-4">
          {/* Status grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            <StatusChipFull label="Application" value={c.application_status} />
            <StatusChipFull label="Link" value={c.link_status} />
            <StatusChipFull label="Landing Page" value={c.landing_page_status} />
            <StatusChipFull label="Approval" value={c.approval_status} />
          </div>

          {/* Compliance checklist */}
          <ComplianceChecklist campaign={c} />

          {/* Metrics */}
          {(c.clicks !== null || c.conversions !== null || c.revenue_usd !== null) && (
            <div className="grid grid-cols-3 gap-3">
              <MetricCell label="Clicks" value={c.clicks?.toLocaleString() ?? '—'} />
              <MetricCell label="Conversions" value={c.conversions?.toLocaleString() ?? '—'} />
              <MetricCell label="Revenue" value={c.revenue_usd != null ? `$${c.revenue_usd.toFixed(2)}` : '—'} />
            </div>
          )}

          {/* Notes */}
          {c.notes && (
            <div>
              <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">Notes</p>
              <p className="text-xs text-slate-600">{c.notes}</p>
            </div>
          )}

          {/* Recommendation detail */}
          {rec && rec.blockers.length > 0 && (
            <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 space-y-1.5">
              <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Blockers</p>
              {rec.blockers.map((b, i) => (
                <div key={i} className="flex items-center gap-2 text-xs text-slate-600">
                  <div className="w-1.5 h-1.5 rounded-full bg-amber-400 shrink-0" />
                  {b}
                </div>
              ))}
            </div>
          )}

          {/* Actions */}
          <div className="flex items-center gap-2 flex-wrap">
            <button onClick={onEdit}
              className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-white border border-slate-200 text-slate-600 text-xs font-bold hover:bg-slate-50 transition-all">
              <Edit2 className="w-3 h-3" />
              Edit
            </button>
            {rec?.approval_needed && rec.approval_action && c.approval_status !== 'pending_review' && (
              <button onClick={() => onRequestApproval(rec)} disabled={approvalLoading}
                className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-[#5B7CFA] text-white text-xs font-bold hover:bg-[#4A6BEB] disabled:opacity-50 transition-all">
                {approvalLoading ? <Loader2 className="w-3 h-3 animate-spin" /> : <ShieldCheck className="w-3 h-3" />}
                Request Approval
              </button>
            )}
            {!c.archived && (
              <button onClick={onArchive}
                className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-white border border-slate-200 text-slate-400 text-xs font-bold hover:bg-red-50 hover:text-red-500 hover:border-red-200 transition-all">
                <Archive className="w-3 h-3" />
                Archive
              </button>
            )}
          </div>

          {approvalFeedback && (
            <p className="text-[10px] text-slate-500 italic">{approvalFeedback}</p>
          )}

          {/* Source/freshness label */}
          <p className="text-[10px] text-slate-400">
            Source: Supabase nexus_os_revenue_campaigns · Updated {timeAgo(c.updated_at)}
          </p>
        </div>
      )}
    </div>
  );
}

// ── Next Best Revenue Action panel ────────────────────────────────────────────

function NextBestAction({
  rec, campaigns, onRequestApproval, approvalLoading,
}: {
  rec: RevenueRecommendation;
  campaigns: RevenueCampaign[];
  onRequestApproval: (rec: RevenueRecommendation) => void;
  approvalLoading: boolean;
}) {
  const campaign = campaigns.find(c => c.id === rec.campaign_id);
  const confColor = rec.confidence === 'high' ? 'text-green-600' : rec.confidence === 'medium' ? 'text-amber-500' : 'text-slate-400';

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-xs font-black text-[#1A2244]">{rec.campaign_name}</p>
        <span className={`text-[10px] font-bold uppercase ${confColor}`}>{rec.confidence} confidence</span>
      </div>

      {/* Score bar */}
      <div>
        <div className="flex items-center justify-between text-[10px] text-slate-400 mb-1">
          <span>Launch readiness</span>
          <span>{rec.score}/100</span>
        </div>
        <div className="w-full h-2 rounded-full bg-slate-100 overflow-hidden">
          <div
            className={`h-full rounded-full ${rec.score >= 70 ? 'bg-green-500' : rec.score >= 40 ? 'bg-amber-400' : 'bg-slate-300'}`}
            style={{ width: `${rec.score}%` }}
          />
        </div>
      </div>

      <div className="p-3 rounded-xl bg-blue-50 border border-blue-100">
        <p className="text-[10px] font-black text-blue-700 uppercase tracking-widest mb-1">Recommended Action</p>
        <p className="text-xs text-blue-800 font-semibold">{rec.next_action}</p>
      </div>

      <div>
        <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">Why</p>
        <p className="text-xs text-slate-600">{rec.why}</p>
      </div>

      {rec.blockers.length > 0 && (
        <div>
          <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">
            {rec.blockers.length} Blocker{rec.blockers.length > 1 ? 's' : ''}
          </p>
          {rec.blockers.slice(0, 3).map((b, i) => (
            <p key={i} className="text-xs text-slate-500 flex items-start gap-1.5 py-0.5">
              <span className="text-amber-400 shrink-0">•</span>{b}
            </p>
          ))}
        </div>
      )}

      <div className="flex items-center justify-between text-[10px] text-slate-400">
        <span>Approval needed: <strong className={rec.approval_needed ? 'text-amber-600' : 'text-green-600'}>{rec.approval_needed ? 'YES' : 'No'}</strong></span>
        <span>Source: rules engine</span>
      </div>

      {rec.approval_needed && rec.approval_action && campaign?.approval_status !== 'pending_review' && (
        <button onClick={() => onRequestApproval(rec)} disabled={approvalLoading}
          className="w-full flex items-center justify-center gap-1.5 px-3 py-2 rounded-xl bg-[#5B7CFA] text-white text-xs font-bold hover:bg-[#4A6BEB] disabled:opacity-50 transition-all">
          {approvalLoading ? <Loader2 className="w-3 h-3 animate-spin" /> : <ShieldCheck className="w-3 h-3" />}
          Request Approval for This Action
        </button>
      )}
      {campaign?.approval_status === 'pending_review' && (
        <p className="text-[10px] text-amber-600 text-center font-semibold">Approval request pending — check Approval Center</p>
      )}
    </div>
  );
}

// ── Compliance checklist ──────────────────────────────────────────────────────

function ComplianceChecklist({ campaign: c }: { campaign: RevenueCampaign }) {
  const checks = [
    { label: 'Compliance reviewed', ok: c.compliance_ok },
    { label: 'Affiliate disclosure added', ok: c.disclosure_ok },
    { label: 'No earnings claims in copy', ok: c.compliance_ok && c.disclosure_ok },
    { label: 'Landing page status not hidden', ok: c.landing_page_status !== 'none' || c.landing_page_url == null },
    { label: 'Application submitted', ok: c.application_status !== 'not_applied' },
  ];
  const passed = checks.filter(x => x.ok).length;

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Compliance Checklist</p>
        <span className="text-[10px] font-bold text-slate-500">{passed}/{checks.length}</span>
      </div>
      <div className="space-y-1">
        {checks.map((item, i) => (
          <div key={i} className="flex items-center gap-2">
            <div className={`w-4 h-4 rounded-full flex items-center justify-center shrink-0 ${
              item.ok ? 'bg-green-50' : 'bg-slate-100'
            }`}>
              {item.ok
                ? <CheckCircle2 className="w-3 h-3 text-green-500" />
                : <Clock className="w-3 h-3 text-slate-400" />}
            </div>
            <span className={`text-xs ${item.ok ? 'text-slate-600' : 'text-slate-400'}`}>{item.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Small helpers ─────────────────────────────────────────────────────────────

function KPICard({ icon: Icon, label, value, sub, color = 'blue', onClick }: {
  icon: React.ElementType; label: string; value: string; sub?: string;
  color?: string; onClick?: () => void;
}) {
  const colorMap: Record<string, string> = {
    green: 'bg-green-50 text-green-600',
    blue: 'bg-blue-50 text-[#5B7CFA]',
    amber: 'bg-amber-50 text-amber-600',
    purple: 'bg-purple-50 text-purple-600',
  };
  return (
    <OSCard className="p-4 flex items-center gap-3" onClick={onClick}>
      <div className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ${colorMap[color] ?? colorMap.blue}`}>
        <Icon className="w-5 h-5" />
      </div>
      <div className="min-w-0">
        <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest">{label}</p>
        <p className="text-lg font-black text-[#1A2244] leading-tight">{value}</p>
        {sub && <p className="text-[9px] text-slate-400 mt-0.5 truncate">{sub}</p>}
      </div>
    </OSCard>
  );
}

function PriorityPill({ priority }: { priority: string }) {
  const s = priority === 'high' ? 'bg-red-50 text-red-600' : priority === 'medium' ? 'bg-amber-50 text-amber-600' : 'bg-slate-100 text-slate-500';
  return <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${s}`}>{priority}</span>;
}

function ApplicationPill({ status }: { status: string }) {
  const s: Record<string, string> = {
    not_applied: 'bg-slate-100 text-slate-500',
    applied: 'bg-blue-50 text-blue-600',
    pending: 'bg-amber-50 text-amber-600',
    approved: 'bg-green-50 text-green-600',
    rejected: 'bg-red-50 text-red-500',
    paused: 'bg-slate-100 text-slate-500',
  };
  return <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${s[status] ?? s.not_applied}`}>{status.replace('_', ' ')}</span>;
}

function StatusChipFull({ label, value }: { label: string; value: string }) {
  return (
    <div className="text-center p-2 rounded-xl bg-slate-50 border border-slate-100">
      <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest">{label}</p>
      <p className="text-xs font-bold text-[#1A2244] mt-0.5">{value.replace(/_/g, ' ')}</p>
    </div>
  );
}

function MetricCell({ label, value }: { label: string; value: string }) {
  return (
    <div className="text-center p-2 rounded-xl bg-slate-50 border border-slate-100">
      <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest">{label}</p>
      <p className="text-sm font-black text-[#1A2244] mt-0.5">{value}</p>
    </div>
  );
}
