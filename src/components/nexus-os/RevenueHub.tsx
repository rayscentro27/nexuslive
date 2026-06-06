import React, { useEffect, useState } from 'react';
import {
  DollarSign, TrendingUp, Users, Target, AlertTriangle,
  CheckCircle2, Clock, ExternalLink, Loader2, Info,
} from 'lucide-react';
import { supabase } from '../../lib/supabase';
import { OSSection, OSCard, Badge, MockLabel, timeAgo, EmptyState } from './shared';
import type { Lead, RevenueEvent } from './types';

interface AffiliateCampaign {
  id: string;
  program_name: string;
  niche: string;
  application_status: 'applied' | 'approved' | 'pending' | 'not_applied';
  link_status: 'active' | 'pending' | 'none';
  landing_page: 'ready' | 'draft' | 'none';
  compliance_ok: boolean;
  disclosure_ok: boolean;
  next_action: string;
  traffic_source: string;
  estimated_epc?: number;
  notes?: string;
}

// Static affiliate campaign data — no fake earnings, no claims, compliance notes required
const CAMPAIGNS: AffiliateCampaign[] = [
  {
    id: 'nav',
    program_name: 'Nav Business Credit',
    niche: 'Business Credit & Funding',
    application_status: 'pending',
    link_status: 'pending',
    landing_page: 'none',
    compliance_ok: false,
    disclosure_ok: false,
    next_action: 'Complete application and get affiliate link',
    traffic_source: 'Content / SEO',
    notes: 'High relevance to Nexus audience. Requires disclosure on all pages.',
  },
  {
    id: 'beehiiv',
    program_name: 'Beehiiv Newsletter',
    niche: 'Creator / Newsletter Tools',
    application_status: 'not_applied',
    link_status: 'none',
    landing_page: 'none',
    compliance_ok: false,
    disclosure_ok: false,
    next_action: 'Apply to Beehiiv affiliate program',
    traffic_source: 'YouTube / Social',
    notes: 'Good fit for content-first strategy.',
  },
  {
    id: 'legalzoom',
    program_name: 'LegalZoom',
    niche: 'Business Formation',
    application_status: 'not_applied',
    link_status: 'none',
    landing_page: 'none',
    compliance_ok: false,
    disclosure_ok: false,
    next_action: 'Research program terms, apply',
    traffic_source: 'Content / SEO',
    notes: 'Natural pairing with LLC/business credit content.',
  },
  {
    id: 'business-credit-tools',
    program_name: 'Business Credit Tools (TBD)',
    niche: 'Business Credit / Paydex',
    application_status: 'pending',
    link_status: 'none',
    landing_page: 'draft',
    compliance_ok: false,
    disclosure_ok: false,
    next_action: 'Identify top program, verify compliance, apply',
    traffic_source: 'YouTube / Email',
    notes: 'High-intent audience. Do not make earnings claims. Disclosure required.',
  },
];

export function RevenueHub() {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [revenueEvents, setRevenueEvents] = useState<RevenueEvent[]>([]);
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    const [leadsRes, revenueRes] = await Promise.all([
      supabase
        .from('leads')
        .select('id,name,business_name,status,lead_score,estimated_value,created_at')
        .order('created_at', { ascending: false })
        .limit(10),
      supabase
        .from('revenue_events')
        .select('id,event_type,amount,currency,created_at')
        .order('created_at', { ascending: false })
        .limit(20),
    ]);
    if (leadsRes.data) setLeads(leadsRes.data as Lead[]);
    if (revenueRes.data) setRevenueEvents(revenueRes.data as RevenueEvent[]);
    setLoading(false);
  }

  useEffect(() => { load(); }, []);

  const totalRevenue = revenueEvents.reduce((s, e) => s + (e.amount ?? 0), 0);
  const hotLeads = leads.filter(l => l.lead_score >= 70);
  const pendingLeads = leads.filter(l => l.status === 'new' || l.status === 'contacted');

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-black text-[#1A2244]">
            Revenue <span className="text-[#5B7CFA]">Command Center</span>
          </h2>
          <p className="text-slate-400 text-xs mt-0.5">
            Live leads + revenue events from Supabase · Campaigns: static registry
          </p>
        </div>
        <MockLabel />
      </div>

      {/* KPI row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <KPICard icon={DollarSign} label="Revenue Events" value={`${revenueEvents.length}`} sub="From Supabase" color="green" />
        <KPICard icon={Users} label="Leads" value={String(leads.length)} sub={`${hotLeads.length} hot (score ≥70)`} color="blue" />
        <KPICard icon={Target} label="Campaigns" value={String(CAMPAIGNS.length)} sub="Affiliate programs" color="purple" />
        <KPICard
          icon={TrendingUp}
          label="Pipeline Status"
          value={pendingLeads.length > 0 ? `${pendingLeads.length} to contact` : 'All contacted'}
          color="amber"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Affiliate campaigns */}
        <OSSection title="Affiliate Campaigns" icon={Target} action={
          <div className="flex items-center gap-1.5">
            <MockLabel />
          </div>
        }>
          <div className="space-y-3">
            {CAMPAIGNS.map(c => (
              <CampaignCard key={c.id} campaign={c} />
            ))}
          </div>

          {/* Compliance guardrail */}
          <div className="mt-4 p-3 rounded-xl bg-amber-50 border border-amber-200 flex items-start gap-2">
            <AlertTriangle className="w-3.5 h-3.5 text-amber-500 shrink-0 mt-0.5" />
            <p className="text-[10px] text-amber-700 font-medium">
              No publishing, email outreach, or ad spend without approval. Affiliate disclosure required on all content. No earnings claims.
            </p>
          </div>
        </OSSection>

        {/* Leads */}
        <OSSection title="Lead Pipeline" icon={Users} action={
          <Badge label={`${leads.length} leads`} variant="info" />
        }>
          {loading ? (
            <LoadingRow />
          ) : leads.length === 0 ? (
            <EmptyState icon={Users} message="No leads yet" />
          ) : (
            <div className="space-y-2">
              {leads.slice(0, 6).map(l => (
                <div key={l.id} className="flex items-center gap-3 p-2.5 rounded-xl bg-slate-50 border border-slate-100">
                  <div className={`w-2 h-2 rounded-full shrink-0 ${
                    l.lead_score >= 70 ? 'bg-green-500' : l.lead_score >= 40 ? 'bg-amber-400' : 'bg-slate-300'
                  }`} />
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-bold text-[#1A2244] truncate">
                      {l.name ?? l.business_name ?? 'Unnamed Lead'}
                    </p>
                    <p className="text-[10px] text-slate-400">Score: {l.lead_score} · {l.status}</p>
                  </div>
                  {l.estimated_value && (
                    <span className="text-xs font-bold text-green-600">${l.estimated_value.toLocaleString()}</span>
                  )}
                </div>
              ))}
            </div>
          )}
        </OSSection>

        {/* Revenue events */}
        <OSSection title="Revenue Events" icon={DollarSign} action={
          <Badge label={`${revenueEvents.length} events`} variant="success" />
        }>
          {loading ? (
            <LoadingRow />
          ) : revenueEvents.length === 0 ? (
            <EmptyState icon={DollarSign} message="No revenue events yet" />
          ) : (
            <div className="space-y-2">
              {revenueEvents.slice(0, 6).map(e => (
                <div key={e.id} className="flex items-center gap-3 p-2.5 rounded-xl bg-slate-50 border border-slate-100">
                  <DollarSign className="w-4 h-4 text-green-500 shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-bold text-[#1A2244]">{e.event_type}</p>
                    <p className="text-[10px] text-slate-400">{timeAgo(e.created_at)}</p>
                  </div>
                  <span className="text-sm font-black text-green-600">
                    ${e.amount?.toFixed(2) ?? '0.00'} {e.currency ?? 'USD'}
                  </span>
                </div>
              ))}
            </div>
          )}
        </OSSection>

        {/* Next best revenue action */}
        <OSSection title="Next Best Revenue Action" icon={TrendingUp}>
          <div className="space-y-2">
            <ActionItem emoji="📋" text="Complete affiliate program applications (Nav, Beehiiv)" priority="high" />
            <ActionItem emoji="📄" text="Create affiliate disclosure page before any publishing" priority="high" />
            <ActionItem emoji="🎥" text="Queue business credit content for YouTube" priority="medium" />
            <ActionItem emoji="📧" text="Build email list via Beehiiv — approval required for outreach" priority="medium" />
            <ActionItem emoji="🔗" text="Draft landing pages for top 2 affiliate offers" priority="medium" />
            <ActionItem emoji="📊" text="Set revenue KPI targets in Supabase launch_metrics" priority="low" />
          </div>

          <div className="mt-4 p-3 rounded-xl bg-blue-50 border border-blue-100 flex items-start gap-2">
            <Info className="w-3.5 h-3.5 text-blue-500 shrink-0 mt-0.5" />
            <p className="text-[10px] text-blue-700">
              All publishing, outreach, and ad spend requires explicit approval in the Approval Center before execution.
            </p>
          </div>
        </OSSection>
      </div>
    </div>
  );
}

function CampaignCard({ campaign: c }: { campaign: AffiliateCampaign }) {
  const statusColor = {
    approved: 'text-green-600',
    pending: 'text-amber-500',
    applied: 'text-blue-500',
    not_applied: 'text-slate-400',
  }[c.application_status];

  return (
    <div className="p-3 rounded-xl border border-slate-200 bg-slate-50/50 space-y-1.5">
      <div className="flex items-center justify-between">
        <p className="text-xs font-bold text-[#1A2244]">{c.program_name}</p>
        <span className={`text-[10px] font-black uppercase ${statusColor}`}>{c.application_status}</span>
      </div>
      <p className="text-[10px] text-slate-400">{c.niche} · {c.traffic_source}</p>
      <div className="flex items-center gap-2 flex-wrap">
        <StatusChip label="Link" ok={c.link_status === 'active'} pending={c.link_status === 'pending'} />
        <StatusChip label="Landing Page" ok={c.landing_page === 'ready'} pending={c.landing_page === 'draft'} />
        <StatusChip label="Compliance" ok={c.compliance_ok} />
        <StatusChip label="Disclosure" ok={c.disclosure_ok} />
      </div>
      <p className="text-[10px] text-[#5B7CFA] font-semibold">→ {c.next_action}</p>
    </div>
  );
}

function StatusChip({ label, ok, pending = false }: { label: string; ok: boolean; pending?: boolean }) {
  return (
    <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold uppercase ${
      ok ? 'bg-green-50 text-green-700' : pending ? 'bg-amber-50 text-amber-600' : 'bg-slate-100 text-slate-400'
    }`}>
      {ok ? '✓' : pending ? '~' : '✗'} {label}
    </span>
  );
}

function ActionItem({ emoji, text, priority }: { emoji: string; text: string; priority: 'high' | 'medium' | 'low' }) {
  const dot = priority === 'high' ? 'bg-red-400' : priority === 'medium' ? 'bg-amber-400' : 'bg-slate-300';
  return (
    <div className="flex items-start gap-2.5 py-1.5">
      <span className="text-sm shrink-0">{emoji}</span>
      <p className="text-xs text-slate-700 flex-1">{text}</p>
      <div className={`w-1.5 h-1.5 rounded-full mt-1.5 shrink-0 ${dot}`} />
    </div>
  );
}

function KPICard({
  icon: Icon,
  label,
  value,
  sub,
  color = 'blue',
}: {
  icon: React.ElementType;
  label: string;
  value: string;
  sub?: string;
  color?: string;
}) {
  const colorMap: Record<string, string> = {
    green: 'bg-green-50 text-green-600',
    blue: 'bg-blue-50 text-[#5B7CFA]',
    purple: 'bg-purple-50 text-purple-600',
    amber: 'bg-amber-50 text-amber-600',
  };
  return (
    <OSCard className="p-4 flex items-center gap-3">
      <div className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ${colorMap[color] ?? colorMap.blue}`}>
        <Icon className="w-5 h-5" />
      </div>
      <div className="min-w-0">
        <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest">{label}</p>
        <p className="text-lg font-black text-[#1A2244]">{value}</p>
        {sub && <p className="text-[9px] text-slate-400 truncate mt-0.5">{sub}</p>}
      </div>
    </OSCard>
  );
}

function LoadingRow() {
  return (
    <div className="flex items-center justify-center py-6">
      <Loader2 className="w-5 h-5 animate-spin text-slate-300" />
    </div>
  );
}
