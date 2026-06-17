import React, { useState } from 'react';
import { X, Loader2, AlertTriangle, Plus, Trash2 } from 'lucide-react';
import type { ContentItem, ContentItemFormData, PlatformVariation } from './types';

const PLATFORM_OPTIONS = [
  'YouTube Shorts', 'TikTok', 'Instagram', 'Facebook',
  'LinkedIn', 'Newsletter', 'Blog', 'X/Threads',
];

const CONTENT_TYPES = [
  { value: 'short_video', label: 'Short Video' },
  { value: 'youtube_short', label: 'YouTube Short' },
  { value: 'tiktok', label: 'TikTok' },
  { value: 'linkedin_post', label: 'LinkedIn Post' },
  { value: 'newsletter', label: 'Newsletter' },
  { value: 'blog', label: 'Blog' },
  { value: 'x_thread', label: 'X Thread' },
  { value: 'instagram', label: 'Instagram' },
  { value: 'facebook', label: 'Facebook' },
  { value: 'script', label: 'Script' },
  { value: 'landing_page_copy', label: 'Landing Page Copy' },
  { value: 'other', label: 'Other' },
];

const SOURCE_TYPES = ['manual', 'transcript', 'video', 'audio', 'report', 'research', 'voice_note', 'other'];

function blankForm(): ContentItemFormData {
  return {
    title: '',
    type: 'short_video',
    content_type: 'short_video',
    status: 'idea',
    source_id: null,
    source_artifact_id: null,
    source_description: null,
    source_type: 'manual',
    source_url: null,
    related_campaign_id: null,
    content_body: null,
    global_draft: '',
    platform_variations: [],
    platform_targets: [],
    compliance_note: null,
    compliance_status: 'not_reviewed',
    disclosure_required: true,
    disclosure_added: false,
    no_earnings_claims: false,
    no_guarantees: false,
    approval_status: 'not_required',
    approval_id: null,
    priority: 'medium',
    next_action: '',
    notes: '',
    archived: false,
    scheduled_at: null,
    published_at: null,
    analytics_url: null,
    lesson_stored: false,
    created_by_agent: 'ray',
    views: null,
    clicks: null,
    conversions: null,
    revenue_attributed: null,
    performance_summary: null,
  };
}

function blankVariation(platform: string): PlatformVariation {
  return {
    platform,
    draft_text: '',
    caption: '',
    hashtags: [],
    cta: '',
    disclosure_note: '',
    status: 'empty',
    approval_required: true,
  };
}

interface ContentModalProps {
  mode: 'create' | 'edit';
  initial?: ContentItem | null;
  campaigns: Array<{ id: string; program_name: string; priority: string }>;
  onSave: (data: ContentItemFormData) => Promise<void>;
  onClose: () => void;
}

export function ContentModal({ mode, initial, campaigns, onSave, onClose }: ContentModalProps) {
  const [form, setForm] = useState<ContentItemFormData>(
    initial ? { ...blankForm(), ...initial } : blankForm(),
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [tab, setTab] = useState<'details' | 'variations' | 'compliance'>('details');

  function set<K extends keyof ContentItemFormData>(key: K, value: ContentItemFormData[K]) {
    setForm(prev => ({ ...prev, [key]: value }));
  }

  function toggleTarget(platform: string) {
    const targets = form.platform_targets.includes(platform)
      ? form.platform_targets.filter(p => p !== platform)
      : [...form.platform_targets, platform];
    set('platform_targets', targets);
  }

  function addVariation(platform: string) {
    if (form.platform_variations.some(v => v.platform === platform)) return;
    set('platform_variations', [...form.platform_variations, blankVariation(platform)]);
  }

  function updateVariation(index: number, changes: Partial<PlatformVariation>) {
    const next = form.platform_variations.map((v, i) => i === index ? { ...v, ...changes } : v);
    set('platform_variations', next);
  }

  function removeVariation(index: number) {
    set('platform_variations', form.platform_variations.filter((_, i) => i !== index));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.title.trim()) { setError('Title is required.'); setTab('details'); return; }
    setError('');
    setSaving(true);
    try {
      await onSave(form);
      onClose();
    } catch (err) {
      setError(String(err));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-[300] flex items-start justify-center overflow-y-auto bg-black/40 backdrop-blur-sm py-6 px-4"
      onClick={e => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-3xl border border-slate-200 overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 bg-slate-50/50">
          <div>
            <h2 className="text-base font-black text-[#1A2244]">
              {mode === 'create' ? 'New Content Item' : 'Edit Content Item'}
            </h2>
            <p className="text-[10px] text-slate-400 mt-0.5">
              No publishing or scheduling until approved. Disclosure required for affiliate CTAs.
            </p>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-lg text-slate-400 hover:bg-slate-100 transition-colors">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-slate-100 px-6">
          {(['details', 'variations', 'compliance'] as const).map(t => (
            <button key={t} onClick={() => setTab(t)}
              className={`px-4 py-2.5 text-xs font-bold capitalize transition-colors border-b-2 -mb-px ${
                tab === t ? 'border-[#5B7CFA] text-[#5B7CFA]' : 'border-transparent text-slate-400 hover:text-slate-600'
              }`}>
              {t}
              {t === 'variations' && form.platform_variations.length > 0 && (
                <span className="ml-1 px-1.5 py-0.5 rounded-full bg-slate-100 text-[9px]">{form.platform_variations.length}</span>
              )}
            </button>
          ))}
        </div>

        <form onSubmit={handleSubmit} className="p-6 max-h-[70vh] overflow-y-auto">
          {/* ── DETAILS TAB ── */}
          {tab === 'details' && (
            <div className="space-y-5">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <Field label="Title *">
                  <input required value={form.title} onChange={e => set('title', e.target.value)}
                    placeholder="How to Build Business Credit Fast" className="input-base" />
                </Field>
                <Field label="Content Type">
                  <select value={form.content_type} onChange={e => set('content_type', e.target.value)} className="input-base">
                    {CONTENT_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
                  </select>
                </Field>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <Field label="Status">
                  <select value={form.status} onChange={e => set('status', e.target.value as ContentItemFormData['status'])} className="input-base">
                    <option value="idea">Idea</option>
                    <option value="draft">Draft</option>
                    <option value="needs_review">Needs Review</option>
                    <option value="approval_requested">Approval Requested</option>
                    <option value="approved">Approved</option>
                    <option value="scheduled">Scheduled</option>
                    <option value="published">Published</option>
                  </select>
                </Field>
                <Field label="Priority">
                  <select value={form.priority} onChange={e => set('priority', e.target.value as ContentItemFormData['priority'])} className="input-base">
                    <option value="high">High</option>
                    <option value="medium">Medium</option>
                    <option value="low">Low</option>
                  </select>
                </Field>
              </div>

              {/* Campaign link */}
              <Field label="Related Revenue Campaign (optional)">
                <select value={form.related_campaign_id ?? ''} onChange={e => set('related_campaign_id', e.target.value || null)} className="input-base">
                  <option value="">— None —</option>
                  {campaigns.map(c => (
                    <option key={c.id} value={c.id}>{c.program_name} ({c.priority} priority)</option>
                  ))}
                </select>
              </Field>

              {/* Source */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <Field label="Source Type">
                  <select value={form.source_type ?? 'manual'} onChange={e => set('source_type', e.target.value)} className="input-base">
                    {SOURCE_TYPES.map(s => <option key={s} value={s}>{s.replace('_', ' ')}</option>)}
                  </select>
                </Field>
                <Field label="Source URL (optional)">
                  <input type="url" value={form.source_url ?? ''} onChange={e => set('source_url', e.target.value || null)}
                    placeholder="https://youtube.com/..." className="input-base" />
                </Field>
              </div>

              <Field label="Source Summary (optional)">
                <textarea value={form.source_description ?? ''} onChange={e => set('source_description', e.target.value || null)}
                  rows={2} placeholder="Key points from the source material..." className="input-base resize-none" />
              </Field>

              {/* Platform targets */}
              <Field label="Platform Targets">
                <div className="flex flex-wrap gap-2">
                  {PLATFORM_OPTIONS.map(p => (
                    <button key={p} type="button" onClick={() => toggleTarget(p)}
                      className={`px-3 py-1.5 rounded-lg text-[11px] font-bold transition-all ${
                        form.platform_targets.includes(p)
                          ? 'bg-[#5B7CFA] text-white'
                          : 'bg-slate-100 text-slate-500 hover:bg-slate-200'
                      }`}>
                      {p}
                    </button>
                  ))}
                </div>
              </Field>

              {/* Global draft */}
              <Field label="Global Draft (main message before platform adaptation)">
                <textarea value={form.global_draft ?? ''} onChange={e => set('global_draft', e.target.value)}
                  rows={4} placeholder="Write the core content idea / draft here..." className="input-base resize-none" />
              </Field>

              <Field label="Next Action">
                <input value={form.next_action ?? ''} onChange={e => set('next_action', e.target.value)}
                  placeholder="Draft LinkedIn variation, complete compliance review..." className="input-base" />
              </Field>
            </div>
          )}

          {/* ── VARIATIONS TAB ── */}
          {tab === 'variations' && (
            <div className="space-y-4">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Add variation:</span>
                {PLATFORM_OPTIONS.map(p => (
                  <button key={p} type="button" onClick={() => addVariation(p)}
                    disabled={form.platform_variations.some(v => v.platform === p)}
                    className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-slate-100 text-slate-600 text-[10px] font-bold hover:bg-slate-200 disabled:opacity-40 disabled:cursor-not-allowed transition-all">
                    <Plus className="w-2.5 h-2.5" /> {p}
                  </button>
                ))}
              </div>

              {form.platform_variations.length === 0 ? (
                <p className="text-xs text-slate-400 italic py-6 text-center">No platform variations yet. Add one above.</p>
              ) : (
                form.platform_variations.map((v, i) => (
                  <div key={i} className="p-4 rounded-xl border border-slate-200 bg-slate-50/50 space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-black text-[#1A2244]">{v.platform}</span>
                      <button type="button" onClick={() => removeVariation(i)}
                        className="p-1 rounded text-slate-400 hover:text-red-500 hover:bg-red-50 transition-colors">
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                    <textarea value={v.draft_text} onChange={e => updateVariation(i, { draft_text: e.target.value, status: e.target.value ? 'draft' : 'empty' })}
                      rows={3} placeholder={`${v.platform} draft text...`} className="input-base resize-none text-xs" />
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                      <input value={v.caption} onChange={e => updateVariation(i, { caption: e.target.value })}
                        placeholder="Caption" className="input-base text-xs py-2" />
                      <input value={v.cta} onChange={e => updateVariation(i, { cta: e.target.value })}
                        placeholder="Call to action" className="input-base text-xs py-2" />
                    </div>
                    <input value={v.hashtags.join(' ')} onChange={e => updateVariation(i, { hashtags: e.target.value.split(/\s+/).filter(Boolean) })}
                      placeholder="#hashtags #separated #by #space" className="input-base text-xs py-2" />
                    <input value={v.disclosure_note} onChange={e => updateVariation(i, { disclosure_note: e.target.value })}
                      placeholder="Disclosure note (required for affiliate CTAs)" className="input-base text-xs py-2" />
                  </div>
                ))
              )}
            </div>
          )}

          {/* ── COMPLIANCE TAB ── */}
          {tab === 'compliance' && (
            <div className="space-y-4">
              <Field label="Compliance Status">
                <select value={form.compliance_status} onChange={e => set('compliance_status', e.target.value as ContentItemFormData['compliance_status'])} className="input-base">
                  <option value="not_reviewed">Not Reviewed</option>
                  <option value="in_review">In Review</option>
                  <option value="approved">Approved</option>
                  <option value="blocked">Blocked</option>
                </select>
              </Field>

              <div className="space-y-2 p-4 rounded-xl bg-amber-50 border border-amber-200">
                <CheckRow label="Disclosure required for this content"
                  checked={form.disclosure_required} onChange={v => set('disclosure_required', v)} />
                <CheckRow label="Affiliate / sponsored disclosure added"
                  checked={form.disclosure_added} onChange={v => set('disclosure_added', v)} />
                <CheckRow label="No earnings / income claims in copy"
                  checked={form.no_earnings_claims} onChange={v => set('no_earnings_claims', v)} />
                <CheckRow label="No guarantees (approval / results / credit)"
                  checked={form.no_guarantees} onChange={v => set('no_guarantees', v)} />
                <CheckRow label="Lesson stored after publishing"
                  checked={form.lesson_stored} onChange={v => set('lesson_stored', v)} />
              </div>

              <Field label="Compliance Notes">
                <textarea value={form.compliance_note ?? ''} onChange={e => set('compliance_note', e.target.value || null)}
                  rows={3} placeholder="Compliance requirements, restrictions, FTC notes..." className="input-base resize-none" />
              </Field>

              <Field label="Internal Notes">
                <textarea value={form.notes ?? ''} onChange={e => set('notes', e.target.value || null)}
                  rows={2} placeholder="Internal observations..." className="input-base resize-none" />
              </Field>
            </div>
          )}

          {/* Footer warning + actions */}
          <div className="mt-5 flex items-start gap-2 p-3 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-500">
            <AlertTriangle className="w-3.5 h-3.5 text-amber-500 shrink-0 mt-0.5" />
            <span>Saving stores the draft only. Publishing, scheduling, and social posting require explicit approval. No earnings claims, no guarantees, disclosure required for affiliate CTAs.</span>
          </div>

          {error && (
            <p className="mt-3 text-xs text-red-600 font-semibold bg-red-50 border border-red-200 rounded-xl p-3">{error}</p>
          )}

          <div className="flex items-center justify-end gap-3 pt-4">
            <button type="button" onClick={onClose}
              className="px-4 py-2 rounded-xl border border-slate-200 text-slate-600 text-xs font-bold hover:bg-slate-50 transition-all">
              Cancel
            </button>
            <button type="submit" disabled={saving}
              className="flex items-center gap-1.5 px-5 py-2 rounded-xl bg-[#5B7CFA] text-white text-xs font-black hover:bg-[#4A6BEB] disabled:opacity-50 transition-all shadow">
              {saving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : null}
              {mode === 'create' ? 'Create' : 'Save Changes'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">{label}</label>
      {children}
    </div>
  );
}

function CheckRow({ label, checked, onChange }: { label: string; checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <label className="flex items-center gap-2 cursor-pointer">
      <input type="checkbox" checked={checked} onChange={e => onChange(e.target.checked)}
        className="w-4 h-4 rounded accent-[#5B7CFA]" />
      <span className="text-xs font-semibold text-[#1A2244]">{label}</span>
    </label>
  );
}
