import React, { useState } from 'react';
import { X, Loader2 } from 'lucide-react';

const SOURCE_TYPES = [
  { value: 'session_notes', label: 'Manual Idea / Notes' },
  { value: 'transcript', label: 'Transcript' },
  { value: 'video', label: 'Video / YouTube' },
  { value: 'audio', label: 'Audio / Voice Note' },
  { value: 'article', label: 'Article / Report' },
  { value: 'document', label: 'Document' },
  { value: 'url', label: 'URL / Link' },
];

interface SourceModalProps {
  onSave: (source: { title: string; type: string; content_url?: string; summary?: string; tags?: string[] }) => Promise<void>;
  onClose: () => void;
}

export function SourceModal({ onSave, onClose }: SourceModalProps) {
  const [title, setTitle] = useState('');
  const [type, setType] = useState('session_notes');
  const [contentUrl, setContentUrl] = useState('');
  const [summary, setSummary] = useState('');
  const [tags, setTags] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!title.trim()) { setError('Title is required.'); return; }
    setError('');
    setSaving(true);
    try {
      await onSave({
        title: title.trim(),
        type,
        content_url: contentUrl.trim() || undefined,
        summary: summary.trim() || undefined,
        tags: tags.split(',').map(t => t.trim()).filter(Boolean),
      });
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
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg border border-slate-200 overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 bg-slate-50/50">
          <div>
            <h2 className="text-base font-black text-[#1A2244]">Add Source</h2>
            <p className="text-[10px] text-slate-400 mt-0.5">Stores source metadata only — no automatic scraping or download.</p>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-lg text-slate-400 hover:bg-slate-100 transition-colors">
            <X className="w-4 h-4" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <Field label="Title *">
            <input required value={title} onChange={e => setTitle(e.target.value)}
              placeholder="Paydex Building Strategy Notes" className="input-base" />
          </Field>

          <Field label="Source Type">
            <select value={type} onChange={e => setType(e.target.value)} className="input-base">
              {SOURCE_TYPES.map(s => <option key={s.value} value={s.value}>{s.label}</option>)}
            </select>
          </Field>

          <Field label="URL (optional)">
            <input type="url" value={contentUrl} onChange={e => setContentUrl(e.target.value)}
              placeholder="https://youtube.com/watch?v=..." className="input-base" />
          </Field>

          <Field label="Summary / Key Points (optional)">
            <textarea value={summary} onChange={e => setSummary(e.target.value)}
              rows={3} placeholder="Main takeaways from this source..." className="input-base resize-none" />
          </Field>

          <Field label="Tags (comma-separated)">
            <input value={tags} onChange={e => setTags(e.target.value)}
              placeholder="business-credit, paydex, funding" className="input-base" />
          </Field>

          {error && (
            <p className="text-xs text-red-600 font-semibold bg-red-50 border border-red-200 rounded-xl p-3">{error}</p>
          )}

          <div className="flex items-center justify-end gap-3 pt-2">
            <button type="button" onClick={onClose}
              className="px-4 py-2 rounded-xl border border-slate-200 text-slate-600 text-xs font-bold hover:bg-slate-50 transition-all">
              Cancel
            </button>
            <button type="submit" disabled={saving}
              className="flex items-center gap-1.5 px-5 py-2 rounded-xl bg-[#5B7CFA] text-white text-xs font-black hover:bg-[#4A6BEB] disabled:opacity-50 transition-all shadow">
              {saving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : null}
              Add Source
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
