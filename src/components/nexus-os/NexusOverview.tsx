import React, { useEffect, useState, useCallback } from 'react';
import {
  Sparkles, Activity, Zap, Bot, CheckCircle2, DollarSign, Video,
  Network, ShieldCheck, ArrowRight, Loader2, MessageSquare, Bell, Lock,
} from 'lucide-react';
import { supabase } from '../../lib/supabase';
import { useNexusRecommendations, type NexusRecommendation } from './useNexusRecommendations';
import type { OsSection } from './types';

interface OverviewProps { onNavigate: (s: OsSection) => void; }

interface Counts {
  campaigns: number;
  content: number;
  contentByStatus: Record<string, number>;
  sources: number;
  entities: number;
  relationships: number;
  pendingApprovals: number;
  revenueTracked: number;
}

export function NexusOverview({ onNavigate }: OverviewProps) {
  const [counts, setCounts] = useState<Counts | null>(null);
  const [hermes, setHermes] = useState<'checking' | 'live' | 'degraded' | 'offline'>('checking');
  const [topRec, setTopRec] = useState<NexusRecommendation | null>(null);
  const [loading, setLoading] = useState(true);
  const engine = useNexusRecommendations();

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [camps, content, sources, ents, rels, appr, rev] = await Promise.all([
        supabase.from('nexus_os_revenue_campaigns').select('id', { count: 'exact', head: true }).eq('archived', false),
        supabase.from('nexus_os_content_items').select('status').eq('archived', false),
        supabase.from('nexus_os_sources').select('id', { count: 'exact', head: true }).neq('status', 'archived'),
        supabase.from('nexus_os_entities').select('id', { count: 'exact', head: true }).eq('archived', false),
        supabase.from('nexus_os_relationships').select('id', { count: 'exact', head: true }),
        supabase.from('owner_approval_queue').select('id', { count: 'exact', head: true }).eq('status', 'pending'),
        supabase.from('revenue_events').select('amount').limit(500),
      ]);
      const byStatus: Record<string, number> = {};
      (content.data ?? []).forEach((r: { status: string }) => { byStatus[r.status] = (byStatus[r.status] ?? 0) + 1; });
      const revenueTracked = (rev.data ?? []).reduce((s: number, e: { amount: number }) => s + (e.amount ?? 0), 0);
      setCounts({
        campaigns: camps.count ?? 0,
        content: (content.data ?? []).length,
        contentByStatus: byStatus,
        sources: sources.count ?? 0,
        entities: ents.count ?? 0,
        relationships: rels.count ?? 0,
        pendingApprovals: appr.count ?? 0,
        revenueTracked,
      });
    } catch (e) {
      console.warn('[Overview] load error', e);
    } finally {
      setLoading(false);
    }
    // Hermes health (fast GET) + top recommendation (best-effort)
    fetch('/.netlify/functions/hermes-chat', { method: 'GET', signal: AbortSignal.timeout(9000) })
      .then(r => r.json()).then(d => setHermes(d.status ?? 'offline')).catch(() => setHermes('offline'));
    engine.recommend('next_step').then(setTopRec).catch(() => setTopRec(null));
  }, [engine]);

  useEffect(() => { load(); }, [load]);

  const c = counts;

  return (
    <div className="space-y-6 nexus-ink">
      {/* Header */}
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div>
          <h1 className="text-2xl font-black flex items-center gap-2 nexus-ink">
            Overview <Sparkles className="w-5 h-5" style={{ color: 'var(--nexus-purple)' }} />
          </h1>
          <p className="text-sm nexus-muted mt-1">Real-time intelligence across your Nexus OS.</p>
        </div>
        <button onClick={() => onNavigate('command-center')}
          className="flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold text-white transition-all nexus-accent-grad">
          Open Command Center <ArrowRight className="w-3.5 h-3.5" />
        </button>
      </div>

      {loading && !c ? (
        <div className="flex items-center justify-center py-20"><Loader2 className="w-6 h-6 animate-spin nexus-muted" /></div>
      ) : (
        <div className="grid gap-4" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(min(320px, 100%), 1fr))' }}>
          {/* Command Center hero — spans wide */}
          <div className="nexus-glass p-5" style={{ gridColumn: '1 / -1' }}>
            <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
              <div>
                <p className="text-sm font-black nexus-ink flex items-center gap-2"><Activity className="w-4 h-4" style={{ color: 'var(--nexus-blue)' }} /> Command Center</p>
                <p className="text-[11px] nexus-muted mt-0.5">Mission-critical system overview.</p>
              </div>
              <button onClick={() => onNavigate('command-center')} className="text-[11px] font-bold flex items-center gap-1" style={{ color: 'var(--nexus-blue)' }}>
                Open <ArrowRight className="w-3 h-3" />
              </button>
            </div>
            <div className="grid gap-3" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(min(200px,100%), 1fr))' }}>
              <HeroMetric icon={ShieldCheck} label="System Health" value={hermes === 'live' ? 'Healthy' : hermes === 'checking' ? '…' : 'Degraded'} sub="Core services" tone="success" />
              <HeroMetric icon={Bot} label="Hermes" value={hermes === 'live' ? 'Live' : hermes === 'checking' ? 'Checking' : hermes === 'degraded' ? 'Degraded' : 'Offline'} sub="AI intelligence layer" tone={hermes === 'live' ? 'success' : hermes === 'offline' ? 'danger' : 'warn'} />
              <HeroMetric icon={Network} label="Graph Links" value={String(c?.relationships ?? 0)} sub={`${c?.entities ?? 0} entities`} tone="blue" />
              <HeroMetric icon={CheckCircle2} label="Pending Approvals" value={String(c?.pendingApprovals ?? 0)} sub="Awaiting review" tone={c?.pendingApprovals ? 'warn' : 'success'} />
            </div>
          </div>

          {/* Hermes preview */}
          <WidgetCard title="Hermes Chat" subtitle="Your AI intelligence layer" icon={MessageSquare}
            pill={hermes === 'live' ? { text: 'Live', tone: 'success' } : hermes === 'offline' ? { text: 'Offline', tone: 'danger' } : { text: hermes === 'checking' ? 'Checking' : 'Degraded', tone: 'warn' }}
            cta="Open Hermes Chat" onCta={() => onNavigate('hermes-chat')}>
            <div className="space-y-2">
              <ChatBubble who="hermes" text="How can I help you today?" />
              <ChatBubble who="user" text="What's the next revenue action?" />
              <ChatBubble who="hermes" text={topRec ? topRec.recommendation.slice(0, 120) : 'Nav is the strongest next move — it has starter content; the blocker is application/compliance review.'} />
            </div>
          </WidgetCard>

          {/* Revenue Hub */}
          <WidgetCard title="Revenue Hub" subtitle="Campaign pipeline" icon={DollarSign}
            pill={{ text: 'Active', tone: 'blue' }} cta="Go to Revenue Hub" onCta={() => onNavigate('revenue')}>
            <div className="space-y-2.5">
              <BigStat value={String(c?.campaigns ?? 0)} label="Campaigns" />
              <Row label="Revenue tracked" value={`$${(c?.revenueTracked ?? 0).toFixed(0)}`} />
              <Row label="Next" value="Nav application / content review" />
            </div>
          </WidgetCard>

          {/* Content Studio */}
          <WidgetCard title="Content Studio" subtitle="Content pipeline" icon={Video}
            pill={{ text: 'Active', tone: 'success' }} cta="Open Content Studio" onCta={() => onNavigate('content')}>
            <div className="space-y-2.5">
              <BigStat value={String(c?.content ?? 0)} label="Drafts" />
              {['draft', 'needs_review', 'approval_requested', 'approved', 'published'].map(s => (
                <Row key={s} label={s.replace(/_/g, ' ')} value={String(c?.contentByStatus[s] ?? 0)} />
              ))}
            </div>
          </WidgetCard>

          {/* Knowledge Graph */}
          <WidgetCard title="Knowledge Graph" subtitle="Relationship intelligence" icon={Network}
            pill={{ text: 'Insights', tone: 'blue' }} cta="Explore Knowledge Graph" onCta={() => onNavigate('graph')}>
            <div className="flex items-center gap-4">
              <GraphGlyph />
              <div className="space-y-2.5 flex-1">
                <BigStat value={String(c?.entities ?? 0)} label="Entities" />
                <Row label="Relationships" value={String(c?.relationships ?? 0)} />
                <Row label="Sources" value={String(c?.sources ?? 0)} />
              </div>
            </div>
          </WidgetCard>

          {/* Trading Ops (safe) */}
          <WidgetCard title="Trading Ops" subtitle="Paper / research only" icon={Activity}
            pill={{ text: 'Safe', tone: 'success' }} cta="Open Trading Ops" onCta={() => onNavigate('trading')}>
            <div className="space-y-2.5">
              <Row label="Live trading" value="Locked" lock />
              <Row label="Auto execution" value="Disabled" lock />
              <Row label="Mode" value="Paper / demo" />
            </div>
          </WidgetCard>

          {/* Approvals / Notifications */}
          <WidgetCard title="Approvals" subtitle="What needs Ray" icon={Bell}
            pill={c?.pendingApprovals ? { text: `${c.pendingApprovals} pending`, tone: 'warn' } : { text: 'Clear', tone: 'success' }}
            cta="Open Approvals" onCta={() => onNavigate('approvals')}>
            <div className="space-y-2.5">
              <BigStat value={String(c?.pendingApprovals ?? 0)} label="Pending approvals" />
              <Row label="Risky actions" value="Approval-gated" />
              <Row label="Executor" value="Disabled" lock />
            </div>
          </WidgetCard>
        </div>
      )}

      {/* Safety strip */}
      <div className="nexus-glass p-3 flex items-center gap-2 flex-wrap">
        <Lock className="w-3.5 h-3.5" style={{ color: 'var(--nexus-success)' }} />
        {['Live trading locked', 'Publishing off', 'Email/social off', 'Ad spend off', 'Executor off'].map(s => (
          <span key={s} className="text-[10px] font-bold px-2 py-0.5 rounded-full" style={{ background: 'var(--nexus-surface-strong)', color: 'var(--nexus-text-muted)', border: '1px solid var(--nexus-border)' }}>{s}</span>
        ))}
      </div>
    </div>
  );
}

// ── Widgets ───────────────────────────────────────────────────────────────────

function WidgetCard({ title, subtitle, icon: Icon, pill, cta, onCta, children }: {
  title: string; subtitle: string; icon: React.ElementType;
  pill?: { text: string; tone: string }; cta: string; onCta: () => void; children: React.ReactNode;
}) {
  return (
    <div className="nexus-glass p-5 flex flex-col">
      <div className="flex items-start justify-between mb-3 gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <div className="w-8 h-8 rounded-xl flex items-center justify-center shrink-0" style={{ background: 'var(--nexus-surface-strong)', border: '1px solid var(--nexus-border)' }}>
            <Icon className="w-4 h-4" style={{ color: 'var(--nexus-blue)' }} />
          </div>
          <div className="min-w-0">
            <p className="text-sm font-black nexus-ink truncate">{title}</p>
            <p className="text-[10px] nexus-muted truncate">{subtitle}</p>
          </div>
        </div>
        {pill && <Pill text={pill.text} tone={pill.tone} />}
      </div>
      <div className="flex-1">{children}</div>
      <button onClick={onCta} className="mt-4 flex items-center gap-1 text-[11px] font-bold self-start" style={{ color: 'var(--nexus-blue)' }}>
        {cta} <ArrowRight className="w-3 h-3" />
      </button>
    </div>
  );
}

function HeroMetric({ icon: Icon, label, value, sub, tone }: { icon: React.ElementType; label: string; value: string; sub: string; tone: string }) {
  const color = tone === 'success' ? 'var(--nexus-success)' : tone === 'danger' ? 'var(--nexus-danger)' : tone === 'warn' ? 'var(--nexus-warning)' : tone === 'blue' ? 'var(--nexus-blue)' : 'var(--nexus-purple)';
  return (
    <div className="rounded-2xl p-4" style={{ background: 'var(--nexus-surface-strong)', border: '1px solid var(--nexus-border)' }}>
      <div className="flex items-center justify-between mb-2">
        <Icon className="w-4 h-4" style={{ color }} />
        <Sparkline color={color} />
      </div>
      <p className="text-lg font-black nexus-ink leading-tight">{value}</p>
      <p className="text-[9px] font-black uppercase tracking-widest nexus-muted mt-1">{label}</p>
      <p className="text-[9px] nexus-muted mt-0.5">{sub}</p>
    </div>
  );
}

function Sparkline({ color }: { color: string }) {
  return (
    <svg width="48" height="16" viewBox="0 0 48 16" fill="none">
      <polyline points="0,12 8,9 16,11 24,5 32,8 40,3 48,6" stroke={color} strokeWidth="1.5" fill="none" strokeLinecap="round" strokeLinejoin="round" opacity="0.8" />
    </svg>
  );
}

function GraphGlyph() {
  return (
    <svg width="64" height="64" viewBox="0 0 64 64" fill="none" className="shrink-0">
      <circle cx="32" cy="14" r="5" fill="var(--nexus-purple)" opacity="0.9" />
      <circle cx="14" cy="44" r="5" fill="var(--nexus-blue)" opacity="0.9" />
      <circle cx="50" cy="44" r="5" fill="var(--nexus-cyan)" opacity="0.9" />
      <circle cx="32" cy="34" r="4" fill="var(--nexus-text-muted)" opacity="0.7" />
      <line x1="32" y1="14" x2="14" y2="44" stroke="var(--nexus-border)" strokeWidth="1.5" />
      <line x1="32" y1="14" x2="50" y2="44" stroke="var(--nexus-border)" strokeWidth="1.5" />
      <line x1="32" y1="14" x2="32" y2="34" stroke="var(--nexus-border)" strokeWidth="1.5" />
      <line x1="14" y1="44" x2="50" y2="44" stroke="var(--nexus-border)" strokeWidth="1.5" />
    </svg>
  );
}

function ChatBubble({ who, text }: { who: 'hermes' | 'user'; text: string }) {
  const isUser = who === 'user';
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div className="max-w-[85%] px-3 py-1.5 rounded-xl text-[11px]" style={{
        background: isUser ? 'var(--nexus-accent-grad, var(--nexus-blue))' : 'var(--nexus-surface-strong)',
        backgroundImage: isUser ? 'linear-gradient(135deg, var(--nexus-purple), var(--nexus-blue))' : 'none',
        color: isUser ? '#fff' : 'var(--nexus-text)',
        border: isUser ? 'none' : '1px solid var(--nexus-border)',
      }}>{text}</div>
    </div>
  );
}

function BigStat({ value, label }: { value: string; label: string }) {
  return (
    <div>
      <p className="text-2xl font-black nexus-ink leading-none">{value}</p>
      <p className="text-[10px] font-black uppercase tracking-widest nexus-muted mt-1">{label}</p>
    </div>
  );
}

function Row({ label, value, lock }: { label: string; value: string; lock?: boolean }) {
  return (
    <div className="flex items-center justify-between gap-2">
      <span className="text-[11px] nexus-muted capitalize">{label}</span>
      <span className="text-[11px] font-bold flex items-center gap-1" style={{ color: lock ? 'var(--nexus-success)' : 'var(--nexus-text)' }}>
        {lock && <Lock className="w-2.5 h-2.5" />}{value}
      </span>
    </div>
  );
}

function Pill({ text, tone }: { text: string; tone: string }) {
  const color = tone === 'success' ? 'var(--nexus-success)' : tone === 'danger' ? 'var(--nexus-danger)' : tone === 'warn' ? 'var(--nexus-warning)' : 'var(--nexus-blue)';
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold shrink-0"
      style={{ background: 'var(--nexus-surface-strong)', border: '1px solid var(--nexus-border)', color }}>
      <span className="w-1.5 h-1.5 rounded-full" style={{ background: color }} />{text}
    </span>
  );
}
