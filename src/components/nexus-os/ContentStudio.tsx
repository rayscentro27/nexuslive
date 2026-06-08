import React, { useEffect, useState, useCallback } from 'react';
import {
  Video, FileText, Instagram, Linkedin, Globe, Mail,
  CheckCircle2, Clock, AlertTriangle, Sparkles, Plus,
  Loader2, RefreshCw, Edit2, Archive, ShieldCheck, Zap,
  ChevronDown, ChevronUp, Link2, BookOpen,
} from 'lucide-react';
import { OSSection, OSCard, Badge, timeAgo, EmptyState } from './shared';
import { ContentModal } from './ContentModal';
import { SourceModal } from './SourceModal';
import { useContentActions } from './useContentActions';
import type { ContentItem, ContentItemFormData, ContentSource, ContentRecommendation, RevenueCampaign } from './types';

const CONTENT_TYPE_ICON: Record<string, React.ElementType> = {
  short_video: Video, youtube_short: Video, tiktok: Video,
  linkedin_post: Linkedin, instagram: Instagram, facebook: Globe,
  newsletter: Mail, blog: Globe, x_thread: FileText,
  script: FileText, landing_page_copy: FileText, other: FileText,
};

const STATUS_VARIANT: Record<string, 'default' | 'warn' | 'success' | 'info' | 'danger'> = {
  idea: 'default',
  draft: 'default',
  needs_review: 'warn',
  approval_requested: 'warn',
  approved: 'success',
  scheduled: 'info',
  published: 'success',
  archived: 'default',
};

export function ContentStudio() {
  const [items, setItems] = useState<ContentItem[]>([]);
  const [sources, setSources] = useState<ContentSource[]>([]);
  const [campaigns, setCampaigns] = useState<Array<{ id: string; program_name: string; priority: string }>>([]);
  const [loading, setLoading] = useState(true);
  const [showArchived, setShowArchived] = useState(false);
  const [modal, setModal] = useState<{ mode: 'create' | 'edit'; item?: ContentItem } | null>(null);
  const [sourceModal, setSourceModal] = useState(false);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [approvalLoading, setApprovalLoading] = useState<string | null>(null);
  const [approvalFeedback, setApprovalFeedback] = useState<Record<string, string>>({});

  const actions = useContentActions();

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [items, sources, campaigns] = await Promise.all([
        actions.fetchItems(showArchived),
        actions.fetchSources().catch(() => []),
        actions.fetchCampaigns().catch(() => []),
      ]);
      setItems(items);
      setSources(sources);
      setCampaigns(campaigns);
    } catch (err) {
      console.error('[ContentStudio] load error:', err);
    } finally {
      setLoading(false);
    }
  }, [showArchived, actions]);

  useEffect(() => { load(); }, [load]);

  // Campaign lookup for recommendations
  type CampaignStub = { id: string; program_name: string; priority: string };
  const campaignMap = new Map<string, CampaignStub>(campaigns.map(c => [c.id, c] as const));

  const recommendations = items
    .filter(i => !i.archived && i.status !== 'published')
    .map(i => {
      const c = i.related_campaign_id ? campaignMap.get(i.related_campaign_id) : null;
      const campaignStub = c ? ({ priority: c.priority, program_name: c.program_name, application_status: 'applied' } as unknown as RevenueCampaign) : null;
      return actions.buildContentRecommendation(i, campaignStub);
    })
    .sort((a, b) => b.score - a.score);

  const topRec = recommendations[0] ?? null;

  // KPIs
  const drafts = items.filter(i => i.status === 'draft' || i.status === 'idea').length;
  const needApproval = items.filter(i => i.status === 'needs_review' || i.status === 'approval_requested').length;
  const approved = items.filter(i => i.status === 'approved').length;
  const scheduled = items.filter(i => i.status === 'scheduled').length;
  const published = items.filter(i => i.status === 'published').length;
  const linkedCampaigns = new Set(items.filter(i => i.related_campaign_id).map(i => i.related_campaign_id)).size;

  // ── Action Plan buckets — tells Ray exactly what to do, not just shows cards ──
  const active = items.filter(i => !i.archived && i.status !== 'published');
  const plan = {
    readyToReview: active.filter(i => i.status === 'needs_review'),
    needsDisclosure: active.filter(i => i.disclosure_required && !i.disclosure_added),
    needsLink: active.filter(i => !i.related_campaign_id),
    readyForApproval: active.filter(i => i.status === 'needs_review' && i.disclosure_added && i.related_campaign_id),
    awaitingPublish: active.filter(i => i.status === 'approved' || i.status === 'approval_requested'),
  };
  // Strongest 3 by recommendation score, among items that still need review
  const top3 = recommendations
    .filter(r => { const it = items.find(x => x.id === r.item_id); return it && it.status === 'needs_review'; })
    .slice(0, 3);

  async function handleSave(data: ContentItemFormData) {
    if (modal?.mode === 'create') {
      const created = await actions.createItem(data);
      setItems(prev => [created, ...prev]);
    } else if (modal?.item) {
      const updated = await actions.updateItem(modal.item.id, data);
      setItems(prev => prev.map(i => i.id === updated.id ? updated : i));
    }
  }

  async function handleSaveSource(source: { title: string; type: string; content_url?: string; summary?: string; tags?: string[] }) {
    const created = await actions.createSource(source);
    setSources(prev => [created, ...prev]);
  }

  async function handleArchive(id: string) {
    if (!confirm('Archive this content item? It can be restored via "Show archived".')) return;
    await actions.archiveItem(id);
    setItems(prev => prev.filter(i => i.id !== id));
  }

  async function handleRequestApproval(item: ContentItem, rec: ContentRecommendation) {
    if (!rec.approval_action) return;
    // Compliance gate: affiliate CTA requires disclosure
    if (item.disclosure_required && !item.disclosure_added) {
      setApprovalFeedback(prev => ({ ...prev, [item.id]: 'Blocked: disclosure required but not added. Edit → Compliance tab.' }));
      return;
    }
    setApprovalLoading(item.id);
    try {
      const approvalId = await actions.requestApproval(
        item,
        rec.approval_action,
        `${rec.item_title}: ${rec.next_action}`,
        item.priority === 'high' ? 'urgent' : 'normal',
      );
      setApprovalFeedback(prev => ({
        ...prev,
        [item.id]: approvalId
          ? `Approval request created (${approvalId.slice(0, 8)}) — check Approval Center`
          : 'Approval request failed — check logs',
      }));
      setItems(prev => prev.map(i =>
        i.id === item.id ? { ...i, approval_status: 'pending_review', status: 'approval_requested' } : i,
      ));
    } catch (err) {
      setApprovalFeedback(prev => ({ ...prev, [item.id]: `Error: ${String(err)}` }));
    } finally {
      setApprovalLoading(null);
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
            Content <span className="text-[#5B7CFA]">Studio</span>
          </h2>
          <p className="text-slate-400 text-xs mt-0.5">
            Live from Supabase · nexus_os_content_items · {items.length} items
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
          <button onClick={() => setSourceModal(true)}
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-slate-100 text-slate-600 text-xs font-bold hover:bg-slate-200 transition-all">
            <BookOpen className="w-3.5 h-3.5" /> Add Source
          </button>
          <button onClick={() => setModal({ mode: 'create' })}
            className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-[#5B7CFA] text-white text-xs font-black hover:bg-[#4A6BEB] transition-all shadow">
            <Plus className="w-3.5 h-3.5" /> New Content
          </button>
        </div>
      </div>

      {/* Safety guardrail */}
      <div className="flex items-start gap-2 p-3 rounded-xl bg-amber-50 border border-amber-200">
        <AlertTriangle className="w-4 h-4 text-amber-500 shrink-0 mt-0.5" />
        <p className="text-xs text-amber-700 font-medium">
          Auto-publishing is disabled. Publishing, scheduling, newsletters, and social posts require explicit approval.
          Affiliate disclosure required. No earnings claims. No guarantees. Funding/credit content stays educational.
        </p>
      </div>

      {/* KPI row */}
      <div className="grid grid-cols-2 md:grid-cols-6 gap-3">
        <MiniKPI label="Total" value={items.filter(i => !i.archived).length} color="blue" />
        <MiniKPI label="Drafts" value={drafts} color="default" />
        <MiniKPI label="Need Approval" value={needApproval} color="amber" />
        <MiniKPI label="Approved" value={approved} color="green" />
        <MiniKPI label="Scheduled" value={scheduled} color="info" />
        <MiniKPI label="Published" value={published} color="green" />
      </div>

      {/* Action Plan — tells Ray what to do, not just shows cards */}
      {active.length > 0 && (
        <div className="rounded-xl border border-indigo-200 bg-indigo-50/60 p-4">
          <div className="flex items-center gap-2 mb-3">
            <Zap className="w-4 h-4 text-indigo-500" />
            <h3 className="text-sm font-bold text-[#1A2244]">Content Studio Action Plan</h3>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-2 mb-3 text-center">
            {([
              ['Ready to review', plan.readyToReview.length, 'text-amber-600'],
              ['Needs disclosure', plan.needsDisclosure.length, 'text-red-600'],
              ['Needs campaign link', plan.needsLink.length, 'text-red-600'],
              ['Ready for approval', plan.readyForApproval.length, 'text-green-600'],
              ['Awaiting publish', plan.awaitingPublish.length, 'text-blue-600'],
            ] as Array<[string, number, string]>).map(([label, n, cls]) => (
              <div key={label} className="rounded-lg bg-white border border-slate-100 py-2">
                <p className={`text-lg font-black ${n ? cls : 'text-slate-300'}`}>{n}</p>
                <p className="text-[10px] text-slate-500 leading-tight">{label}</p>
              </div>
            ))}
          </div>
          {top3.length > 0 && (
            <div className="space-y-1.5">
              <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wide">Review these 3 first</p>
              {top3.map((r, i) => (
                <div key={r.item_id} className="flex items-start gap-2 text-xs">
                  <span className="font-black text-indigo-400">{i + 1}</span>
                  <div>
                    <span className="font-semibold text-[#1A2244]">{r.item_title.slice(0, 60)}</span>
                    <span className="text-slate-500"> — {r.next_action}</span>
                  </div>
                </div>
              ))}
              <p className="text-[10px] text-slate-400 mt-2 italic">
                Nothing here is published or scheduled. Add disclosure, then use “Request Approval” on a card.
              </p>
            </div>
          )}
        </div>
      )}

      {/* Main grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Content queue — 2/3 */}
        <div className="lg:col-span-2 space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-black text-[#1A2244] uppercase tracking-widest">Content Queue</h3>
            {needApproval > 0 && <Badge label={`${needApproval} awaiting approval`} variant="warn" />}
          </div>

          {loading ? (
            <div className="flex items-center justify-center py-16">
              <Loader2 className="w-6 h-6 animate-spin text-slate-300" />
            </div>
          ) : items.length === 0 ? (
            <EmptyState icon={Video} message="No content items yet — click New Content to start" />
          ) : (
            items.map(item => (
              <ContentCard
                key={item.id}
                item={item}
                campaign={item.related_campaign_id ? campaignMap.get(item.related_campaign_id) : undefined}
                recommendation={recommendations.find(r => r.item_id === item.id)}
                expanded={expanded.has(item.id)}
                onToggle={() => toggleExpand(item.id)}
                onEdit={() => setModal({ mode: 'edit', item })}
                onArchive={() => handleArchive(item.id)}
                onRequestApproval={rec => handleRequestApproval(item, rec)}
                approvalLoading={approvalLoading === item.id}
                approvalFeedback={approvalFeedback[item.id]}
              />
            ))
          )}
        </div>

        {/* Sidebar — 1/3 */}
        <div className="space-y-4">
          {/* Next Content Action */}
          <OSSection title="Next Content Action" icon={Zap}>
            {!topRec ? (
              <EmptyState icon={Zap} message="Add content to get recommendations" />
            ) : (
              <NextContentAction
                rec={topRec}
                item={items.find(i => i.id === topRec.item_id)}
                onRequestApproval={rec => {
                  const it = items.find(x => x.id === rec.item_id);
                  if (it) handleRequestApproval(it, rec);
                }}
                approvalLoading={approvalLoading !== null}
              />
            )}
          </OSSection>

          {/* Source intake */}
          <OSSection title="Source Intake" icon={FileText} action={
            <button onClick={() => setSourceModal(true)} className="text-[10px] font-bold text-[#5B7CFA] hover:underline flex items-center gap-1">
              <Plus className="w-3 h-3" /> Add
            </button>
          }>
            {sources.length === 0 ? (
              <EmptyState icon={FileText} message="No sources yet" />
            ) : (
              <div className="space-y-2">
                {sources.slice(0, 6).map(s => (
                  <div key={s.id} className="p-2.5 rounded-xl bg-slate-50 border border-slate-100">
                    <div className="flex items-center justify-between gap-2">
                      <p className="text-xs font-bold text-[#1A2244] line-clamp-1">{s.title}</p>
                      <Badge label={s.status} variant="info" />
                    </div>
                    <p className="text-[10px] text-slate-400 mt-0.5">{s.type} · {timeAgo(s.created_at)}</p>
                  </div>
                ))}
              </div>
            )}
          </OSSection>

          {/* Platform targets reference */}
          <OSSection title="Platform Targets" icon={Globe}>
            <div className="grid grid-cols-2 gap-2">
              {[
                { p: 'YouTube Shorts', icon: Video },
                { p: 'TikTok', icon: Video },
                { p: 'Instagram', icon: Instagram },
                { p: 'LinkedIn', icon: Linkedin },
                { p: 'Newsletter', icon: Mail },
                { p: 'Blog', icon: Globe },
              ].map(({ p, icon: Icon }) => (
                <div key={p} className="flex items-center gap-1.5 p-2 rounded-lg bg-slate-50 border border-slate-100">
                  <Icon className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                  <span className="text-[10px] font-bold text-[#1A2244]">{p}</span>
                </div>
              ))}
            </div>
          </OSSection>
        </div>
      </div>

      {/* Modals */}
      {modal && (
        <ContentModal
          mode={modal.mode}
          initial={modal.item ?? null}
          campaigns={campaigns}
          onSave={handleSave}
          onClose={() => setModal(null)}
        />
      )}
      {sourceModal && (
        <SourceModal onSave={handleSaveSource} onClose={() => setSourceModal(false)} />
      )}
    </div>
  );
}

// ── Content card ──────────────────────────────────────────────────────────────

function ContentCard({
  item, campaign, recommendation: rec, expanded, onToggle,
  onEdit, onArchive, onRequestApproval, approvalLoading, approvalFeedback,
}: {
  item: ContentItem;
  campaign?: { id: string; program_name: string; priority: string };
  recommendation?: ContentRecommendation;
  expanded: boolean;
  onToggle: () => void;
  onEdit: () => void;
  onArchive: () => void;
  onRequestApproval: (rec: ContentRecommendation) => void;
  approvalLoading: boolean;
  approvalFeedback?: string;
}) {
  const Icon = CONTENT_TYPE_ICON[item.content_type] ?? FileText;
  const score = rec?.score ?? 0;
  const variations = Array.isArray(item.platform_variations) ? item.platform_variations : [];
  const targets = Array.isArray(item.platform_targets) ? item.platform_targets : [];

  return (
    <div className={`bg-white border rounded-2xl shadow-sm overflow-hidden ${
      item.archived ? 'border-slate-100 opacity-60' : 'border-slate-200'
    }`}>
      <button onClick={onToggle} className="w-full flex items-center gap-3 px-5 py-4 text-left hover:bg-slate-50/50 transition-colors">
        <div className="w-9 h-9 rounded-xl bg-slate-100 flex items-center justify-center shrink-0 text-slate-500">
          <Icon className="w-4.5 h-4.5 w-[18px] h-[18px]" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <p className="text-sm font-black text-[#1A2244] line-clamp-1">{item.title}</p>
            <PriorityPill priority={item.priority} />
            <Badge label={item.status.replace(/_/g, ' ')} variant={STATUS_VARIANT[item.status] ?? 'default'} />
            {item.approval_status === 'pending_review' && <Badge label="Approval pending" variant="warn" />}
            {campaign && <span className="text-[10px] text-[#5B7CFA] font-semibold flex items-center gap-0.5"><Link2 className="w-2.5 h-2.5" />{campaign.program_name}</span>}
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            {item.content_type.replace(/_/g, ' ')} · {variations.length} variation{variations.length !== 1 ? 's' : ''} · {targets.length} target{targets.length !== 1 ? 's' : ''}
          </p>
          {rec && (
            <p className="text-[10px] text-[#5B7CFA] mt-1 font-semibold line-clamp-1">→ {rec.next_action}</p>
          )}
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {rec && <span className="text-[10px] font-black text-slate-400">{score}</span>}
          {expanded ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
        </div>
      </button>

      {expanded && (
        <div className="px-5 pb-5 border-t border-slate-100 pt-4 space-y-4">
          {/* Global draft */}
          {item.global_draft && (
            <div>
              <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">Global Draft</p>
              <p className="text-xs text-slate-600 whitespace-pre-wrap line-clamp-4">{item.global_draft}</p>
            </div>
          )}

          {/* Platform variations */}
          {variations.length > 0 && (
            <div>
              <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-2">Platform Variations</p>
              <div className="space-y-2">
                {variations.map((v, i) => (
                  <div key={i} className="p-2.5 rounded-lg bg-slate-50 border border-slate-100">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-[#1A2244]">{v.platform}</span>
                      <Badge label={v.status} variant={v.status === 'ready' || v.status === 'approved' ? 'success' : 'default'} />
                    </div>
                    {v.draft_text && <p className="text-[11px] text-slate-600 mt-1 line-clamp-2">{v.draft_text}</p>}
                    {v.hashtags.length > 0 && (
                      <p className="text-[10px] text-[#5B7CFA] mt-1">{v.hashtags.join(' ')}</p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Compliance checklist */}
          <ComplianceChecklist item={item} />

          {/* Metrics — real values only */}
          {(item.views != null || item.clicks != null || item.conversions != null || item.revenue_attributed != null) ? (
            <div className="grid grid-cols-4 gap-2">
              <MetricCell label="Views" value={item.views?.toLocaleString() ?? '—'} />
              <MetricCell label="Clicks" value={item.clicks?.toLocaleString() ?? '—'} />
              <MetricCell label="Conv." value={item.conversions?.toLocaleString() ?? '—'} />
              <MetricCell label="Revenue" value={item.revenue_attributed != null ? `$${item.revenue_attributed.toFixed(0)}` : '—'} />
            </div>
          ) : (
            <p className="text-[10px] text-slate-400 italic">Metrics not tracked yet</p>
          )}

          {/* Blockers */}
          {rec && rec.blockers.length > 0 && (
            <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 space-y-1.5">
              <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Blockers</p>
              {rec.blockers.map((b, i) => (
                <div key={i} className="flex items-center gap-2 text-xs text-slate-600">
                  <div className="w-1.5 h-1.5 rounded-full bg-amber-400 shrink-0" />{b}
                </div>
              ))}
            </div>
          )}

          {/* Actions */}
          <div className="flex items-center gap-2 flex-wrap">
            <button onClick={onEdit}
              className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-white border border-slate-200 text-slate-600 text-xs font-bold hover:bg-slate-50 transition-all">
              <Edit2 className="w-3 h-3" /> Edit
            </button>
            {rec?.approval_needed && rec.approval_action && item.approval_status !== 'pending_review' && (
              <button onClick={() => onRequestApproval(rec)} disabled={approvalLoading}
                className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-[#5B7CFA] text-white text-xs font-bold hover:bg-[#4A6BEB] disabled:opacity-50 transition-all">
                {approvalLoading ? <Loader2 className="w-3 h-3 animate-spin" /> : <ShieldCheck className="w-3 h-3" />}
                Request Approval
              </button>
            )}
            {!item.archived && (
              <button onClick={onArchive}
                className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-white border border-slate-200 text-slate-400 text-xs font-bold hover:bg-red-50 hover:text-red-500 hover:border-red-200 transition-all">
                <Archive className="w-3 h-3" /> Archive
              </button>
            )}
          </div>

          {approvalFeedback && <p className="text-[10px] text-slate-500 italic">{approvalFeedback}</p>}

          <p className="text-[10px] text-slate-400">
            Source: Supabase nexus_os_content_items · Updated {timeAgo(item.updated_at)}
          </p>
        </div>
      )}
    </div>
  );
}

// ── Next Content Action panel ─────────────────────────────────────────────────

function NextContentAction({
  rec, item, onRequestApproval, approvalLoading,
}: {
  rec: ContentRecommendation;
  item?: ContentItem;
  onRequestApproval: (rec: ContentRecommendation) => void;
  approvalLoading: boolean;
}) {
  const confColor = rec.confidence === 'high' ? 'text-green-600' : rec.confidence === 'medium' ? 'text-amber-500' : 'text-slate-400';
  const blocked = item?.disclosure_required && !item?.disclosure_added && rec.approval_needed;

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-xs font-black text-[#1A2244] line-clamp-1">{rec.item_title}</p>
        <span className={`text-[10px] font-bold uppercase ${confColor}`}>{rec.confidence}</span>
      </div>

      <div>
        <div className="flex items-center justify-between text-[10px] text-slate-400 mb-1">
          <span>Readiness</span><span>{rec.score}/100</span>
        </div>
        <div className="w-full h-2 rounded-full bg-slate-100 overflow-hidden">
          <div className={`h-full rounded-full ${rec.score >= 70 ? 'bg-green-500' : rec.score >= 40 ? 'bg-amber-400' : 'bg-slate-300'}`} style={{ width: `${rec.score}%` }} />
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

      <div className="flex items-center justify-between text-[10px] text-slate-400">
        <span>Approval needed: <strong className={rec.approval_needed ? 'text-amber-600' : 'text-green-600'}>{rec.approval_needed ? 'YES' : 'No'}</strong></span>
        <span>Source: rules engine</span>
      </div>

      {blocked && (
        <p className="text-[10px] text-red-500 font-semibold">⚠ Disclosure required before approval. Edit → Compliance.</p>
      )}

      {rec.approval_needed && rec.approval_action && item?.approval_status !== 'pending_review' && !blocked && (
        <button onClick={() => onRequestApproval(rec)} disabled={approvalLoading}
          className="w-full flex items-center justify-center gap-1.5 px-3 py-2 rounded-xl bg-[#5B7CFA] text-white text-xs font-bold hover:bg-[#4A6BEB] disabled:opacity-50 transition-all">
          {approvalLoading ? <Loader2 className="w-3 h-3 animate-spin" /> : <ShieldCheck className="w-3 h-3" />}
          Request Approval
        </button>
      )}
      {item?.approval_status === 'pending_review' && (
        <p className="text-[10px] text-amber-600 text-center font-semibold">Approval pending — check Approval Center</p>
      )}
    </div>
  );
}

// ── Compliance checklist ──────────────────────────────────────────────────────

function ComplianceChecklist({ item }: { item: ContentItem }) {
  const checks = [
    { label: 'Compliance reviewed', ok: item.compliance_status === 'approved' },
    { label: 'Disclosure added', ok: !item.disclosure_required || item.disclosure_added },
    { label: 'No earnings claims', ok: item.no_earnings_claims },
    { label: 'No guarantees', ok: item.no_guarantees },
  ];
  const passed = checks.filter(c => c.ok).length;

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Compliance Checklist</p>
        <span className="text-[10px] font-bold text-slate-500">{passed}/{checks.length}</span>
      </div>
      <div className="grid grid-cols-2 gap-1.5">
        {checks.map((c, i) => (
          <div key={i} className="flex items-center gap-1.5">
            {c.ok ? <CheckCircle2 className="w-3.5 h-3.5 text-green-500 shrink-0" /> : <Clock className="w-3.5 h-3.5 text-slate-400 shrink-0" />}
            <span className={`text-[11px] ${c.ok ? 'text-slate-600' : 'text-slate-400'}`}>{c.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Small helpers ─────────────────────────────────────────────────────────────

function MiniKPI({ label, value, color = 'blue' }: { label: string; value: number; color?: string }) {
  const colorMap: Record<string, string> = {
    green: 'text-green-600', blue: 'text-[#5B7CFA]', amber: 'text-amber-600',
    info: 'text-blue-500', default: 'text-slate-500',
  };
  return (
    <OSCard className="p-3 text-center">
      <p className={`text-xl font-black ${colorMap[color] ?? colorMap.blue}`}>{value}</p>
      <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest mt-0.5">{label}</p>
    </OSCard>
  );
}

function PriorityPill({ priority }: { priority: string }) {
  const s = priority === 'high' ? 'bg-red-50 text-red-600' : priority === 'medium' ? 'bg-amber-50 text-amber-600' : 'bg-slate-100 text-slate-500';
  return <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${s}`}>{priority}</span>;
}

function MetricCell({ label, value }: { label: string; value: string }) {
  return (
    <div className="text-center p-2 rounded-xl bg-slate-50 border border-slate-100">
      <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest">{label}</p>
      <p className="text-sm font-black text-[#1A2244] mt-0.5">{value}</p>
    </div>
  );
}
