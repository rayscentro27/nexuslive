import React, { useState } from 'react';
import {
  Video, FileText, Instagram, Linkedin, Globe, Mail,
  Play, Pause, CheckCircle2, Clock, AlertTriangle, Sparkles, Plus,
} from 'lucide-react';
import { OSSection, OSCard, Badge, MockLabel } from './shared';

interface ContentItem {
  id: string;
  title: string;
  type: 'youtube_short' | 'tiktok' | 'instagram' | 'linkedin' | 'newsletter' | 'blog' | 'x';
  status: 'draft' | 'approval_needed' | 'approved' | 'scheduled' | 'published';
  source?: string;
  platform_variations: string[];
  compliance_note?: string;
  created_at: string;
}

interface SourceAsset {
  id: string;
  title: string;
  type: 'transcript' | 'article' | 'video' | 'document' | 'session_notes';
  status: 'ingested' | 'summarized' | 'ideas_generated' | 'drafts_ready';
  created_at: string;
}

// Placeholder data — content pipeline not yet wired to backend
const MOCK_SOURCES: SourceAsset[] = [
  { id: 's1', title: 'Business Credit Deep Dive Session Notes', type: 'session_notes', status: 'ingested', created_at: new Date().toISOString() },
  { id: 's2', title: 'Paydex Building Strategy Transcript', type: 'transcript', status: 'summarized', created_at: new Date().toISOString() },
  { id: 's3', title: 'Nav Affiliate Overview Notes', type: 'document', status: 'ideas_generated', created_at: new Date().toISOString() },
];

const MOCK_CONTENT: ContentItem[] = [
  {
    id: 'c1',
    title: 'How to Build Business Credit Fast (Paydex Method)',
    type: 'youtube_short',
    status: 'draft',
    source: 'Paydex Building Strategy Transcript',
    platform_variations: ['YouTube Short', 'TikTok', 'Instagram Reel'],
    compliance_note: 'Include affiliate disclosure if mentioning Nav. No earnings claims.',
    created_at: new Date().toISOString(),
  },
  {
    id: 'c2',
    title: '5 Business Credit Mistakes That Kill Your Paydex Score',
    type: 'linkedin',
    status: 'approval_needed',
    source: 'Business Credit Deep Dive Session Notes',
    platform_variations: ['LinkedIn Article', 'Newsletter Issue'],
    compliance_note: 'Educational content only. No guarantees. Disclosure required.',
    created_at: new Date().toISOString(),
  },
];

const PLATFORM_ICONS: Record<string, React.ElementType> = {
  youtube_short: Video,
  tiktok: Video,
  instagram: Instagram,
  linkedin: Linkedin,
  newsletter: Mail,
  blog: Globe,
  x: FileText,
};

const STATUS_CONFIG: Record<string, { label: string; color: string }> = {
  draft: { label: 'Draft', color: 'default' },
  approval_needed: { label: 'Awaiting Approval', color: 'warn' },
  approved: { label: 'Approved', color: 'success' },
  scheduled: { label: 'Scheduled', color: 'info' },
  published: { label: 'Published', color: 'success' },
};

export function ContentStudio() {
  const [activeWorkflow, setActiveWorkflow] = useState<string | null>(null);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-black text-[#1A2244]">
            Content <span className="text-[#5B7CFA]">Studio</span>
          </h2>
          <p className="text-slate-400 text-xs mt-0.5">
            Source → Summary → Ideas → Drafts → Approval → Publish
          </p>
        </div>
        <MockLabel />
      </div>

      {/* Safety guardrail */}
      <div className="p-3 rounded-xl bg-amber-50 border border-amber-200 flex items-start gap-2">
        <AlertTriangle className="w-4 h-4 text-amber-500 shrink-0 mt-0.5" />
        <p className="text-xs text-amber-700 font-medium">
          Auto-publishing is disabled. All content requires approval before any platform distribution.
          Affiliate disclosure required. No earnings claims. No misleading fear tactics.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Workflow */}
        <OSSection title="Content Workflow" icon={Sparkles}>
          <div className="space-y-2">
            {[
              { step: 1, label: 'Source Intake', desc: 'Upload transcripts, notes, articles', icon: FileText },
              { step: 2, label: 'AI Summary', desc: 'Hermes extracts key points', icon: Sparkles },
              { step: 3, label: 'Content Ideas', desc: 'Generate platform-specific angles', icon: Sparkles },
              { step: 4, label: 'Draft Creation', desc: 'Write platform variations', icon: FileText },
              { step: 5, label: 'Approval', desc: 'Ray reviews and approves', icon: CheckCircle2 },
              { step: 6, label: 'Schedule / Publish', desc: 'Queue for distribution', icon: Clock },
              { step: 7, label: 'Analytics', desc: 'Track performance', icon: Globe },
              { step: 8, label: 'Lesson Stored', desc: 'Save insight to knowledge base', icon: CheckCircle2 },
            ].map(s => (
              <div key={s.step} className="flex items-center gap-3">
                <div className="w-6 h-6 rounded-full bg-[#5B7CFA]/10 text-[#5B7CFA] flex items-center justify-center text-[10px] font-black shrink-0">
                  {s.step}
                </div>
                <div className="flex-1">
                  <p className="text-xs font-bold text-[#1A2244]">{s.label}</p>
                  <p className="text-[10px] text-slate-400">{s.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </OSSection>

        {/* Source assets */}
        <OSSection title="Source Intake" icon={FileText} action={
          <button className="text-[10px] font-bold text-[#5B7CFA] hover:underline flex items-center gap-1">
            <Plus className="w-3 h-3" /> Add Source
          </button>
        }>
          <div className="space-y-2">
            {MOCK_SOURCES.map(s => (
              <div key={s.id} className="p-3 rounded-xl bg-slate-50 border border-slate-100">
                <div className="flex items-center justify-between">
                  <p className="text-xs font-bold text-[#1A2244] line-clamp-1">{s.title}</p>
                  <Badge label={s.status} variant="info" />
                </div>
                <p className="text-[10px] text-slate-400 mt-1">{s.type}</p>
              </div>
            ))}
          </div>
          <p className="text-[10px] text-slate-400 mt-3 italic">
            Not wired to backend yet. Set up Supabase nexus_os_sources table to persist.
          </p>
        </OSSection>
      </div>

      {/* Content draft queue */}
      <OSSection title="Content Draft Queue" icon={Video} action={
        <Badge label={`${MOCK_CONTENT.filter(c => c.status === 'approval_needed').length} awaiting approval`} variant="warn" />
      }>
        <div className="space-y-3">
          {MOCK_CONTENT.map(item => (
            <ContentCard key={item.id} item={item} />
          ))}
        </div>
        <div className="mt-3 p-3 rounded-xl bg-slate-50 border border-slate-100">
          <p className="text-[10px] text-slate-400 italic">
            Content items stored here are placeholders. Wire to nexus_os_content_items Supabase table for persistence.
          </p>
        </div>
      </OSSection>

      {/* Platform targets */}
      <OSSection title="Platform Targets" icon={Globe}>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[
            { platform: 'YouTube Shorts', icon: Video, priority: 'Primary', status: 'active' },
            { platform: 'TikTok', icon: Video, priority: 'Primary', status: 'active' },
            { platform: 'Instagram', icon: Instagram, priority: 'Secondary', status: 'active' },
            { platform: 'LinkedIn', icon: Linkedin, priority: 'Secondary', status: 'active' },
            { platform: 'Newsletter', icon: Mail, priority: 'Primary', status: 'planned' },
            { platform: 'Blog / SEO', icon: Globe, priority: 'Secondary', status: 'planned' },
            { platform: 'Facebook', icon: Globe, priority: 'Low', status: 'planned' },
            { platform: 'X / Threads', icon: FileText, priority: 'Optional', status: 'planned' },
          ].map(p => {
            const Icon = p.icon;
            return (
              <div key={p.platform} className="flex items-center gap-2 p-2.5 rounded-xl bg-slate-50 border border-slate-100">
                <Icon className="w-4 h-4 text-slate-400 shrink-0" />
                <div>
                  <p className="text-[11px] font-bold text-[#1A2244]">{p.platform}</p>
                  <p className="text-[9px] text-slate-400">{p.priority}</p>
                </div>
              </div>
            );
          })}
        </div>
      </OSSection>
    </div>
  );
}

function ContentCard({ item }: { item: ContentItem }) {
  const Icon = PLATFORM_ICONS[item.type] ?? FileText;
  const status = STATUS_CONFIG[item.status] ?? { label: item.status, color: 'default' };

  return (
    <div className="p-4 rounded-xl border border-slate-200 bg-white space-y-2">
      <div className="flex items-start gap-3">
        <div className="w-8 h-8 rounded-xl bg-slate-100 flex items-center justify-center shrink-0">
          <Icon className="w-4 h-4 text-slate-500" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <p className="text-sm font-bold text-[#1A2244] line-clamp-1">{item.title}</p>
            <Badge label={status.label} variant={status.color as 'default' | 'warn' | 'success' | 'info'} />
          </div>
          {item.source && (
            <p className="text-[10px] text-slate-400 mt-0.5">Source: {item.source}</p>
          )}
        </div>
      </div>

      <div className="flex flex-wrap gap-1">
        {item.platform_variations.map(v => (
          <span key={v} className="px-2 py-0.5 rounded-full bg-slate-100 text-[10px] font-semibold text-slate-600">{v}</span>
        ))}
      </div>

      {item.compliance_note && (
        <div className="flex items-start gap-1.5 p-2 rounded-lg bg-amber-50 border border-amber-100">
          <AlertTriangle className="w-3 h-3 text-amber-500 shrink-0 mt-0.5" />
          <p className="text-[10px] text-amber-700">{item.compliance_note}</p>
        </div>
      )}

      {item.status === 'approval_needed' && (
        <div className="flex gap-2 pt-1">
          <button className="px-3 py-1.5 rounded-lg bg-slate-100 text-slate-500 text-[10px] font-bold hover:bg-slate-200 transition-colors cursor-not-allowed" disabled title="Approval execution not yet wired">
            Approve (sets status only)
          </button>
          <p className="text-[9px] text-slate-400 italic self-center">Backend executor not yet wired</p>
        </div>
      )}
    </div>
  );
}
