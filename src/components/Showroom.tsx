import React, { useState } from 'react';
import { Store, FileCheck2, Sparkles, Package, Eye, Check, RefreshCw, ShieldCheck, Send } from 'lucide-react';
import { showroomSocialApprovalManifest } from '../data/showroomSocialApprovalManifest';

/**
 * Showroom — proof assets, demos, generated packages, and review-ready outputs.
 *
 * Read-only first version. There is no showroom API helper yet, so this page
 * documents the known asset registry and proof/package examples without making
 * any backend call. Approve / Revise actions are UI-only placeholders — approval
 * is routed through the Nexus approval queue, NOT direct frontend script execution.
 */

const STATUS_CARDS = [
  { key: 'needs_review', label: 'Needs Review', emoji: '🟡', tone: 'border-amber-200 bg-amber-50 text-amber-700' },
  { key: 'approved',     label: 'Approved',     emoji: '🟢', tone: 'border-emerald-200 bg-emerald-50 text-emerald-700' },
  { key: 'revise',       label: 'Revise',       emoji: '🟠', tone: 'border-orange-200 bg-orange-50 text-orange-700' },
  { key: 'draft',        label: 'Draft',        emoji: '⚪', tone: 'border-slate-200 bg-slate-50 text-slate-600' },
];

const KNOWN_PACKAGES = [
  { name: 'proof_credit', desc: 'Credit proof package (assessment + checklist + report).', icon: FileCheck2 },
  { name: 'Credit/Funding Readiness package', desc: 'Primary offer: readiness review, intake checklist, lender-readiness report, 30-day plan.', icon: Package },
  { name: 'YouTube shorts', desc: 'Generated short-form video scripts/packages.', icon: Sparkles },
  { name: 'newsletters', desc: 'Drafted newsletter sequences (needs review).', icon: Sparkles },
  { name: 'landing pages', desc: 'Landing page drafts for offers.', icon: Sparkles },
  { name: 'approval packets', desc: 'Review-ready packets queued for Ray approval.', icon: ShieldCheck },
];

export function Showroom() {
  // UI-only selection state — no backend calls.
  const [filter, setFilter] = useState<string>('all');

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="glass-card p-5">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-2xl bg-[#eef0fd] flex items-center justify-center border-2 border-white shadow">
            <Store size={24} className="text-[#3d5af1]" />
          </div>
          <div>
            <h1 className="text-xl font-black text-slate-800">Showroom</h1>
            <p className="text-sm text-slate-500">
              Proof assets, demos, generated packages, and review-ready outputs.
            </p>
          </div>
        </div>
      </div>

      {/* Status filter cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {STATUS_CARDS.map(s => (
          <button
            key={s.key}
            onClick={() => setFilter(filter === s.key ? 'all' : s.key)}
            className={`glass-card p-4 text-left transition-all ${filter === s.key ? 'ring-2 ring-[#3d5af1]' : ''}`}
            aria-pressed={filter === s.key}
          >
            <div className={`inline-flex items-center gap-1.5 text-xs font-bold px-2 py-1 rounded-full border ${s.tone}`}>
              <span>{s.emoji}</span>{s.label}
            </div>
            <div className="mt-2 text-2xl font-black text-slate-800">—</div>
            <div className="text-[11px] text-slate-400">count loads with registry API</div>
          </button>
        ))}
      </div>

      {/* Social approval manifest */}
      <div className="glass-card p-5">
        <div className="flex items-center justify-between gap-3 mb-3">
          <div>
            <h2 className="text-base font-black text-slate-800">Social Approval Queue</h2>
            <p className="text-sm text-slate-500">
              Facebook approval items staged for Clear Credentials. Real publishing remains Ray-approved only.
            </p>
          </div>
          <div className="inline-flex items-center gap-1.5 text-xs font-bold px-2.5 py-1.5 rounded-full border border-emerald-200 bg-emerald-50 text-emerald-700 shrink-0">
            <ShieldCheck size={13} /> Safe Manifest
          </div>
        </div>

        <div className="space-y-3">
          {showroomSocialApprovalManifest.map(item => (
            <div key={item.id} className="rounded-xl border border-slate-100 bg-white/70 p-3">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="text-sm font-black text-slate-800">{item.title}</div>
                  <div className="text-[11px] text-slate-400 mt-0.5">
                    {item.queueItemId} · {item.platform} · {item.channel}
                  </div>
                </div>
                <div className={`text-[11px] font-bold px-2 py-1 rounded-full border shrink-0 ${
                  item.approvalStatus === 'published'
                    ? 'border-emerald-200 bg-emerald-50 text-emerald-700'
                    : 'border-amber-200 bg-amber-50 text-amber-700'
                }`}>
                  {item.approvalStatus.replaceAll('_', ' ')}
                </div>
              </div>
              <p className="mt-2 text-sm text-slate-600">{item.captionPreview}</p>
              <div className="mt-2 text-xs font-semibold text-[#3d5af1]">{item.cta}</div>
              {typeof item.qualityScore === 'number' && (
                <div className="mt-1 text-[11px] font-bold text-slate-500">
                  Quality score: {item.qualityScore}/100
                </div>
              )}
              {item.proofPermalink && (
                <a
                  href={item.proofPermalink}
                  target="_blank"
                  rel="noreferrer"
                  className="mt-2 inline-flex items-center gap-1.5 text-xs font-semibold text-slate-700 hover:text-[#3d5af1]"
                >
                  <Send size={13} /> Published proof: {item.proofPostId}
                </a>
              )}
              {item.approveCommand && (
                <div className="mt-3 grid gap-1.5 text-[11px] text-slate-500">
                  <code className="rounded bg-slate-50 border border-slate-100 px-2 py-1 overflow-x-auto">
                    {item.approveCommand}
                  </code>
                  <code className="rounded bg-slate-50 border border-slate-100 px-2 py-1 overflow-x-auto">
                    {item.dryRunCommand}
                  </code>
                  <code className="rounded bg-slate-50 border border-slate-100 px-2 py-1 overflow-x-auto">
                    DO NOT RUN UNTIL APPROVED: {item.publishCommand}
                  </code>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Asset Registry */}
      <div className="glass-card p-5">
        <h2 className="text-base font-black text-slate-800 mb-1">Asset Registry</h2>
        <p className="text-sm text-slate-500 mb-3">
          Registry path:{' '}
          <code className="px-1.5 py-0.5 rounded bg-slate-100 text-slate-700 text-xs">logs/showroom_assets.json</code>
        </p>

        <div className="space-y-2">
          {KNOWN_PACKAGES.map(p => {
            const Icon = p.icon;
            return (
              <div key={p.name} className="flex items-center gap-3 rounded-xl border border-slate-100 bg-white/70 p-3">
                <div className="w-9 h-9 rounded-lg bg-[#eef0fd] flex items-center justify-center shrink-0">
                  <Icon size={18} className="text-[#3d5af1]" />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="text-sm font-bold text-slate-800 truncate">{p.name}</div>
                  <div className="text-xs text-slate-500 truncate">{p.desc}</div>
                </div>
                <div className="flex items-center gap-1.5 shrink-0">
                  <button
                    type="button"
                    className="inline-flex items-center gap-1 text-xs font-semibold px-2.5 py-1.5 rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50"
                  >
                    <Eye size={13} /> Review
                  </button>
                  <button
                    type="button"
                    className="inline-flex items-center gap-1 text-xs font-semibold px-2.5 py-1.5 rounded-lg border border-emerald-200 text-emerald-700 hover:bg-emerald-50"
                  >
                    <Check size={13} /> Approve
                  </button>
                  <button
                    type="button"
                    className="inline-flex items-center gap-1 text-xs font-semibold px-2.5 py-1.5 rounded-lg border border-orange-200 text-orange-700 hover:bg-orange-50"
                  >
                    <RefreshCw size={13} /> Request Revision
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Safety note */}
      <div className="glass-card p-4 border-l-4 border-[#3d5af1]">
        <p className="text-xs text-slate-600">
          <ShieldCheck size={14} className="inline mr-1 text-[#3d5af1]" />
          Approval actions are routed through the Nexus approval queue. Direct frontend
          script execution is disabled. Live asset counts and Approve/Revise wiring will
          arrive with a read-only <code className="px-1 rounded bg-slate-100">/api/showroom</code> endpoint.
        </p>
      </div>
    </div>
  );
}
