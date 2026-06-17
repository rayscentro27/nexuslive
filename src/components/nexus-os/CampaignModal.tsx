import React, { useState, useEffect } from 'react';
import { X, Loader2, AlertTriangle } from 'lucide-react';
import type { RevenueCampaign, CampaignFormData } from './types';

const BLANK: CampaignFormData = {
  program_name: '',
  niche: '',
  campaign_type: 'affiliate',
  application_status: 'not_applied',
  link_status: 'none',
  affiliate_link: null,
  landing_page_status: 'none',
  landing_page_url: null,
  compliance_ok: false,
  disclosure_ok: false,
  traffic_source: '',
  content_queue_count: 0,
  clicks: null,
  conversions: null,
  revenue_usd: null,
  next_action: '',
  notes: '',
  offer_url: '',
  priority: 'medium',
  estimated_value: null,
  approval_status: 'not_required',
  archived: false,
};

interface CampaignModalProps {
  mode: 'create' | 'edit';
  initial?: RevenueCampaign | null;
  onSave: (data: CampaignFormData) => Promise<void>;
  onClose: () => void;
}

export function CampaignModal({ mode, initial, onSave, onClose }: CampaignModalProps) {
  const [form, setForm] = useState<CampaignFormData>(
    initial ? { ...BLANK, ...initial } : { ...BLANK },
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  function set<K extends keyof CampaignFormData>(key: K, value: CampaignFormData[K]) {
    setForm(prev => ({ ...prev, [key]: value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.program_name.trim()) { setError('Program name is required.'); return; }
    if (!form.niche.trim()) { setError('Niche/category is required.'); return; }
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
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl border border-slate-200 overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 bg-slate-50/50">
          <div>
            <h2 className="text-base font-black text-[#1A2244]">
              {mode === 'create' ? 'Add Campaign' : 'Edit Campaign'}
            </h2>
            <p className="text-[10px] text-slate-400 mt-0.5">
              No publishing, link activation, or outreach until approval.
            </p>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-lg text-slate-400 hover:bg-slate-100 transition-colors">
            <X className="w-4 h-4" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-5 max-h-[80vh] overflow-y-auto">
          {/* Row: name + niche */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Field label="Program Name *">
              <input required value={form.program_name} onChange={e => set('program_name', e.target.value)}
                placeholder="Nav Business Credit"
                className="input-base" />
            </Field>
            <Field label="Niche / Category *">
              <input required value={form.niche} onChange={e => set('niche', e.target.value)}
                placeholder="Business Credit & Funding"
                className="input-base" />
            </Field>
          </div>

          {/* Row: type + priority */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Field label="Campaign Type">
              <select value={form.campaign_type} onChange={e => set('campaign_type', e.target.value as CampaignFormData['campaign_type'])} className="input-base">
                <option value="affiliate">Affiliate</option>
                <option value="direct">Direct / Own Product</option>
                <option value="partnership">Partnership</option>
                <option value="content">Content Monetization</option>
                <option value="referral_program">Referral Program</option>
              </select>
            </Field>
            <Field label="Priority">
              <select value={form.priority} onChange={e => set('priority', e.target.value as CampaignFormData['priority'])} className="input-base">
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
              </select>
            </Field>
          </div>

          {/* Row: application + link status */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Field label="Application Status">
              <select value={form.application_status} onChange={e => set('application_status', e.target.value as CampaignFormData['application_status'])} className="input-base">
                <option value="not_applied">Not Applied</option>
                <option value="applied">Applied</option>
                <option value="pending">Pending Review</option>
                <option value="approved">Approved</option>
                <option value="rejected">Rejected</option>
                <option value="paused">Paused</option>
              </select>
            </Field>
            <Field label="Affiliate Link Status">
              <select value={form.link_status} onChange={e => set('link_status', e.target.value as CampaignFormData['link_status'])} className="input-base">
                <option value="none">None</option>
                <option value="pending">Pending</option>
                <option value="active">Active (requires approval to use)</option>
                <option value="expired">Expired</option>
              </select>
            </Field>
          </div>

          {/* Row: landing page + traffic source */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Field label="Landing Page Status">
              <select value={form.landing_page_status} onChange={e => set('landing_page_status', e.target.value as CampaignFormData['landing_page_status'])} className="input-base">
                <option value="none">None</option>
                <option value="draft">Draft</option>
                <option value="review">In Review</option>
                <option value="ready">Ready (requires approval to publish)</option>
              </select>
            </Field>
            <Field label="Traffic Source">
              <input value={form.traffic_source ?? ''} onChange={e => set('traffic_source', e.target.value)}
                placeholder="Content / SEO / YouTube"
                className="input-base" />
            </Field>
          </div>

          {/* Row: offer URL + estimated value */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Field label="Offer URL (public)">
              <input type="url" value={form.offer_url ?? ''} onChange={e => set('offer_url', e.target.value)}
                placeholder="https://nav.com"
                className="input-base" />
            </Field>
            <Field label="Estimated Value / Potential (USD) — planning only">
              <input type="number" min="0" step="0.01" value={form.estimated_value ?? ''}
                onChange={e => set('estimated_value', e.target.value ? parseFloat(e.target.value) : null)}
                placeholder="0.00"
                className="input-base" />
            </Field>
          </div>

          {/* Compliance toggles */}
          <div className="flex items-center gap-6 p-3 rounded-xl bg-amber-50 border border-amber-200">
            <label className="flex items-center gap-2 cursor-pointer">
              <input type="checkbox" checked={form.compliance_ok}
                onChange={e => set('compliance_ok', e.target.checked)}
                className="w-4 h-4 rounded accent-[#5B7CFA]" />
              <span className="text-xs font-bold text-[#1A2244]">Compliance reviewed</span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input type="checkbox" checked={form.disclosure_ok}
                onChange={e => set('disclosure_ok', e.target.checked)}
                className="w-4 h-4 rounded accent-[#5B7CFA]" />
              <span className="text-xs font-bold text-[#1A2244]">Affiliate disclosure added</span>
            </label>
          </div>

          {/* Next action */}
          <Field label="Next Action">
            <input value={form.next_action ?? ''} onChange={e => set('next_action', e.target.value)}
              placeholder="Apply to program, draft landing page, ..."
              className="input-base" />
          </Field>

          {/* Notes */}
          <Field label="Notes / Compliance Notes">
            <textarea value={form.notes ?? ''} onChange={e => set('notes', e.target.value)}
              rows={3} placeholder="Compliance requirements, restrictions, observations..."
              className="input-base resize-none" />
          </Field>

          {/* Compliance warning */}
          <div className="flex items-start gap-2 p-3 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-500">
            <AlertTriangle className="w-3.5 h-3.5 text-amber-500 shrink-0 mt-0.5" />
            <span>No earnings claims. No misleading guarantees. Affiliate disclosure required on all published content. Publishing and link activation require explicit approval.</span>
          </div>

          {error && (
            <p className="text-xs text-red-600 font-semibold bg-red-50 border border-red-200 rounded-xl p-3">{error}</p>
          )}

          {/* Actions */}
          <div className="flex items-center justify-end gap-3 pt-2">
            <button type="button" onClick={onClose}
              className="px-4 py-2 rounded-xl border border-slate-200 text-slate-600 text-xs font-bold hover:bg-slate-50 transition-all">
              Cancel
            </button>
            <button type="submit" disabled={saving}
              className="flex items-center gap-1.5 px-5 py-2 rounded-xl bg-[#5B7CFA] text-white text-xs font-black hover:bg-[#4A6BEB] disabled:opacity-50 transition-all shadow">
              {saving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : null}
              {mode === 'create' ? 'Create Campaign' : 'Save Changes'}
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
