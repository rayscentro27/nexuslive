import React, { useState } from 'react';
import { Store, FileCheck2, Sparkles, Package, Eye, Check, RefreshCw, ShieldCheck, Send, X, Copy, XCircle, Terminal } from 'lucide-react';
import { showroomSocialApprovalManifest, type ShowroomSocialApprovalItem } from '../data/showroomSocialApprovalManifest';

/**
 * Showroom — proof assets, demos, generated packages, and review-ready outputs.
 *
 * Each social approval item is now clickable: "Review" opens a modal with the full
 * caption, score, status, queue ID, and the exact CLI commands to approve / dry-run /
 * reject / request revision. There is no safe production API to mutate the local
 * social queue, so the action buttons COPY the exact command (clearly labelled
 * "CLI approval required") — they never fake an approval or one-click real-publish.
 */

const STATUS_CARDS = [
  { key: 'needs_review', label: 'Needs Review', emoji: '🟡', tone: 'border-amber-200 bg-amber-50 text-amber-700' },
  { key: 'approved',     label: 'Approved',     emoji: '🟢', tone: 'border-emerald-200 bg-emerald-50 text-emerald-700' },
  { key: 'revise',       label: 'Revise',       emoji: '🟠', tone: 'border-orange-200 bg-orange-50 text-orange-700' },
  { key: 'published',    label: 'Published',    emoji: '🔵', tone: 'border-blue-200 bg-blue-50 text-blue-700' },
];

const KNOWN_PACKAGES = [
  { name: 'proof_credit', desc: 'Credit proof package (assessment + checklist + report).', icon: FileCheck2 },
  { name: 'Credit/Funding Readiness package', desc: 'Primary offer: readiness review, intake checklist, lender-readiness report, 30-day plan.', icon: Package },
  { name: 'YouTube shorts', desc: 'Generated short-form video scripts/packages.', icon: Sparkles },
  { name: 'newsletters', desc: 'Drafted newsletter sequences (needs review).', icon: Sparkles },
  { name: 'landing pages', desc: 'Landing page drafts for offers.', icon: Sparkles },
  { name: 'approval packets', desc: 'Review-ready packets queued for Ray approval.', icon: ShieldCheck },
];

// Build the reject / request-revision commands from the queue id (the manifest only
// ships approve/dry-run/publish). These mirror scripts/social_queue_reject.py.
function rejectCommand(id: string) {
  return `python3 scripts/social_queue_reject.py --item-id ${id} --reason "rejected via Showroom"`;
}
function reviseCommand(id: string) {
  return `python3 scripts/social_queue_reject.py --item-id ${id} --reason "needs_revision via Showroom: <what to change>"`;
}

function statusTone(status: string) {
  if (status === 'published') return 'border-blue-200 bg-blue-50 text-blue-700';
  if (status === 'approved') return 'border-emerald-200 bg-emerald-50 text-emerald-700';
  return 'border-amber-200 bg-amber-50 text-amber-700';
}

export function Showroom() {
  const [filter, setFilter] = useState<string>('all');
  const [active, setActive] = useState<ShowroomSocialApprovalItem | null>(null);

  const counts = showroomSocialApprovalManifest.reduce<Record<string, number>>((acc, i) => {
    const k = i.approvalStatus === 'published' ? 'published' : 'needs_review';
    acc[k] = (acc[k] ?? 0) + 1;
    return acc;
  }, {});

  const visible = showroomSocialApprovalManifest.filter(i => {
    if (filter === 'all') return true;
    if (filter === 'published') return i.approvalStatus === 'published';
    if (filter === 'needs_review') return i.approvalStatus !== 'published';
    return true;
  });

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
            <div className="mt-2 text-2xl font-black text-slate-800">
              {s.key === 'published' ? (counts.published ?? 0)
                : s.key === 'needs_review' ? (counts.needs_review ?? 0)
                : 0}
            </div>
            <div className="text-[11px] text-slate-400">social approval manifest</div>
          </button>
        ))}
      </div>

      {/* Social approval manifest */}
      <div className="glass-card p-5">
        <div className="flex items-center justify-between gap-3 mb-3">
          <div>
            <h2 className="text-base font-black text-slate-800">Social Approval Queue</h2>
            <p className="text-sm text-slate-500">
              Facebook approval items staged for Clear Credentials. Tap <b>Review</b> to see the full
              post and approval commands. Real publishing remains Ray-approved (CLI) only.
            </p>
          </div>
          <div className="inline-flex items-center gap-1.5 text-xs font-bold px-2.5 py-1.5 rounded-full border border-emerald-200 bg-emerald-50 text-emerald-700 shrink-0">
            <ShieldCheck size={13} /> Safe Manifest
          </div>
        </div>

        <div className="space-y-3">
          {visible.map(item => (
            <div key={item.id} className="rounded-xl border border-slate-100 bg-white/70 p-3">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="text-sm font-black text-slate-800">{item.title}</div>
                  <div className="text-[11px] text-slate-400 mt-0.5">
                    {item.queueItemId} · {item.platform} · {item.channel}
                  </div>
                </div>
                <div className={`text-[11px] font-bold px-2 py-1 rounded-full border shrink-0 ${statusTone(item.approvalStatus)}`}>
                  {item.approvalStatus.replaceAll('_', ' ')}
                </div>
              </div>
              <p className="mt-2 text-sm text-slate-600 line-clamp-2 whitespace-pre-wrap">{item.captionPreview}</p>
              <div className="mt-2 flex items-center justify-between gap-2 flex-wrap">
                <div className="text-xs font-semibold text-[#3d5af1]">{item.cta}</div>
                <div className="flex items-center gap-2">
                  {typeof item.qualityScore === 'number' && (
                    <span className="text-[11px] font-bold text-slate-500">Score: {item.qualityScore}/100</span>
                  )}
                  <button
                    type="button"
                    onClick={() => setActive(item)}
                    className="inline-flex items-center gap-1 text-xs font-bold px-3 py-1.5 rounded-lg bg-[#3d5af1] text-white hover:bg-[#3450d8] transition-all"
                  >
                    <Eye size={13} /> Review
                  </button>
                </div>
              </div>
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
          {' '}· approvals run via{' '}
          <code className="px-1.5 py-0.5 rounded bg-slate-100 text-slate-700 text-xs">scripts/review_showroom_asset.py</code>
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
                <span className="inline-flex items-center gap-1 text-[11px] font-semibold px-2.5 py-1.5 rounded-lg border border-slate-200 text-slate-500 shrink-0">
                  <Terminal size={12} /> CLI approval
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Safety note */}
      <div className="glass-card p-4 border-l-4 border-[#3d5af1]">
        <p className="text-xs text-slate-600">
          <ShieldCheck size={14} className="inline mr-1 text-[#3d5af1]" />
          Approval actions are routed through the Nexus approval queue. The Showroom never
          executes scripts or publishes directly — Review actions copy the exact command for
          you to run in your terminal. One-click real publishing is intentionally disabled.
        </p>
      </div>

      {active && <ReviewModal item={active} onClose={() => setActive(null)} />}
    </div>
  );
}

function ReviewModal({ item, onClose }: { item: ShowroomSocialApprovalItem; onClose: () => void }) {
  const [copied, setCopied] = useState<string>('');
  const isPublished = item.approvalStatus === 'published';

  function copy(label: string, command?: string) {
    if (!command) return;
    navigator.clipboard?.writeText(command).then(
      () => { setCopied(label); setTimeout(() => setCopied(''), 1800); },
      () => { setCopied('copy failed'); setTimeout(() => setCopied(''), 1800); },
    );
  }

  const CmdRow = ({ label, command, tone }: { label: string; command?: string; tone: string }) =>
    command ? (
      <div className="space-y-1">
        <div className="flex items-center justify-between gap-2">
          <span className="text-[11px] font-bold text-slate-600">{label}</span>
          <button
            type="button"
            onClick={() => copy(label, command)}
            className={`inline-flex items-center gap-1 text-[11px] font-bold px-2 py-1 rounded-md border ${tone}`}
          >
            <Copy size={11} /> {copied === label ? 'Copied!' : 'Copy'}
          </button>
        </div>
        <code className="block rounded bg-slate-900 text-slate-100 px-2.5 py-1.5 text-[11px] overflow-x-auto whitespace-pre">{command}</code>
      </div>
    ) : null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40" onClick={onClose}>
      <div className="glass-card max-w-2xl w-full max-h-[88vh] overflow-y-auto p-5 bg-white" onClick={e => e.stopPropagation()}>
        <div className="flex items-start justify-between gap-3 mb-3">
          <div className="min-w-0">
            <h3 className="text-base font-black text-slate-800">{item.title}</h3>
            <div className="text-[11px] text-slate-400 mt-0.5">{item.queueItemId} · {item.platform} · {item.channel}</div>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-slate-100 text-slate-400"><X size={18} /></button>
        </div>

        <div className="flex items-center gap-2 mb-3 flex-wrap">
          <span className={`text-[11px] font-bold px-2 py-1 rounded-full border ${statusTone(item.approvalStatus)}`}>
            {item.approvalStatus.replaceAll('_', ' ')}
          </span>
          {typeof item.qualityScore === 'number' && (
            <span className="text-[11px] font-bold px-2 py-1 rounded-full border border-slate-200 bg-slate-50 text-slate-600">
              Quality {item.qualityScore}/100
            </span>
          )}
          <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2 py-1 rounded-full border border-indigo-200 bg-indigo-50 text-indigo-700">
            <Terminal size={11} /> CLI approval required
          </span>
        </div>

        <div className="rounded-xl border border-slate-100 bg-slate-50/60 p-3 mb-3">
          <div className="text-[11px] font-bold text-slate-500 mb-1">Caption</div>
          <p className="text-sm text-slate-700 whitespace-pre-wrap">{item.captionPreview}</p>
          <div className="mt-2 text-xs font-semibold text-[#3d5af1]">{item.cta}</div>
        </div>

        {isPublished ? (
          <div className="rounded-xl border border-blue-200 bg-blue-50 p-3">
            <p className="text-xs font-bold text-blue-700">Already published ✅</p>
            {item.proofPermalink && (
              <a href={item.proofPermalink} target="_blank" rel="noreferrer" className="mt-1 inline-flex items-center gap-1.5 text-xs font-semibold text-blue-700 hover:underline">
                <Send size={13} /> View post {item.proofPostId}
              </a>
            )}
          </div>
        ) : (
          <div className="space-y-3">
            <p className="text-[11px] text-slate-500">
              These actions <b>copy a command</b> for you to run in your terminal. The Showroom
              does not run them and never publishes directly.
            </p>
            <CmdRow label="Approve" command={item.approveCommand} tone="border-emerald-200 text-emerald-700 hover:bg-emerald-50" />
            <CmdRow label="Dry-run (safe preview)" command={item.dryRunCommand} tone="border-blue-200 text-blue-700 hover:bg-blue-50" />
            <CmdRow label="Request revision" command={reviseCommand(item.queueItemId)} tone="border-orange-200 text-orange-700 hover:bg-orange-50" />
            <CmdRow label="Reject" command={rejectCommand(item.queueItemId)} tone="border-red-200 text-red-700 hover:bg-red-50" />

            {item.publishCommand && (
              <div className="space-y-1 pt-2 border-t border-slate-100">
                <div className="flex items-center justify-between gap-2">
                  <span className="inline-flex items-center gap-1 text-[11px] font-bold text-red-600">
                    <XCircle size={12} /> Real publish — DO NOT RUN until approved
                  </span>
                  <button
                    type="button"
                    onClick={() => copy('Publish', item.publishCommand)}
                    className="inline-flex items-center gap-1 text-[11px] font-bold px-2 py-1 rounded-md border border-red-200 text-red-700 hover:bg-red-50"
                  >
                    <Copy size={11} /> {copied === 'Publish' ? 'Copied!' : 'Copy'}
                  </button>
                </div>
                <code className="block rounded bg-slate-900 text-red-200 px-2.5 py-1.5 text-[11px] overflow-x-auto whitespace-pre">{item.publishCommand}</code>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
