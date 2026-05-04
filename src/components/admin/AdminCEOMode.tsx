import React, { useEffect, useState } from 'react';
import {
  Brain, TrendingUp, Users, DollarSign, Rocket, MessageSquare,
  CheckCircle2, AlertTriangle, Clock, Zap, RefreshCw, Loader2,
} from 'lucide-react';
import { cn } from '../../lib/utils';
import { supabase } from '../../lib/supabase';

// ─── Types ────────────────────────────────────────────────────────────────────

type Alert = { id: string; event_type: string; classification: string; aggregated_summary: string; created_at: string };
type AutoFix = { id: string; issue_type: string; action_taken: string; status: string; created_at: string };
type Lead = { id: string; name: string; status: string; estimated_value: number | null; created_at: string };
type RevenueEvent = { id: string; event_type: string; amount: number; created_at: string };
type LaunchMetric = { id: string; metric_name: string; metric_value: number; target_value: number | null; unit: string };
type Approval = { id: string; action_type: string; description: string; priority: string; requested_by: string; created_at: string };
type CommsLog = { id: string; channel: string; status: string; created_at: string };

// ─── Helpers ─────────────────────────────────────────────────────────────────

function StatCard({ icon: Icon, label, value, color = 'blue', sub = '' }: {
  icon: React.ElementType; label: string; value: string; color?: string; sub?: string;
}) {
  const colors: Record<string, string> = {
    blue:   'bg-blue-50 text-[#5B7CFA]',
    green:  'bg-green-50 text-green-600',
    amber:  'bg-amber-50 text-amber-600',
    purple: 'bg-purple-50 text-purple-600',
    red:    'bg-red-50 text-red-600',
  };
  return (
    <div className="bg-white border border-slate-200 p-5 rounded-2xl shadow-sm flex items-center gap-4">
      <div className={cn('w-11 h-11 rounded-xl flex items-center justify-center shrink-0', colors[color])}>
        <Icon className="w-5 h-5" />
      </div>
      <div>
        <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest">{label}</p>
        <p className="text-xl font-black text-[#1A2244]">{value}</p>
        {sub && <p className="text-[10px] text-slate-400 mt-0.5">{sub}</p>}
      </div>
    </div>
  );
}

function SectionCard({ title, icon: Icon, children, action }: {
  title: string; icon: React.ElementType; children: React.ReactNode; action?: React.ReactNode;
}) {
  return (
    <div className="bg-white border border-slate-200 rounded-2xl overflow-hidden shadow-sm">
      <div className="px-5 py-4 border-b border-slate-100 bg-slate-50/30 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Icon className="w-4 h-4 text-[#5B7CFA]" />
          <span className="text-[10px] font-black text-[#1A2244] uppercase tracking-widest">{title}</span>
        </div>
        {action}
      </div>
      <div className="p-4">{children}</div>
    </div>
  );
}

function badge(text: string, color: string) {
  const cls: Record<string, string> = {
    green:  'bg-green-50 text-green-600',
    amber:  'bg-amber-50 text-amber-600',
    red:    'bg-red-50 text-red-600',
    blue:   'bg-blue-50 text-[#5B7CFA]',
    purple: 'bg-purple-50 text-purple-600',
    slate:  'bg-slate-100 text-slate-500',
  };
  return (
    <span className={cn('px-2 py-0.5 rounded-md text-[9px] font-black uppercase tracking-widest', cls[color] || cls.slate)}>
      {text}
    </span>
  );
}

// ─── Widget: CEO Status ───────────────────────────────────────────────────────

function CEOStatusWidget() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    supabase
      .from('hermes_aggregates')
      .select('id,event_type,classification,aggregated_summary,created_at')
      .in('classification', ['critical_alert', 'actionable'])
      .order('created_at', { ascending: false })
      .limit(5)
      .then(({ data }) => { setAlerts(data ?? []); setLoading(false); });
  }, []);

  return (
    <SectionCard title="CEO Status — Active Alerts" icon={Brain}>
      {loading ? (
        <div className="flex justify-center py-6"><Loader2 className="w-5 h-5 animate-spin text-slate-300" /></div>
      ) : alerts.length === 0 ? (
        <div className="flex items-center gap-2 text-green-600 py-4">
          <CheckCircle2 className="w-4 h-4" />
          <span className="text-xs font-bold">All systems green — no critical alerts</span>
        </div>
      ) : (
        <div className="space-y-2">
          {alerts.map(a => (
            <div key={a.id} className="flex items-start gap-3 p-3 rounded-xl bg-red-50/50 border border-red-100">
              <AlertTriangle className="w-4 h-4 text-red-500 shrink-0 mt-0.5" />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-0.5">
                  {badge(a.classification.replace('_', ' '), a.classification === 'critical_alert' ? 'red' : 'amber')}
                  <span className="text-[9px] text-slate-400">{new Date(a.created_at).toLocaleString()}</span>
                </div>
                <p className="text-xs text-slate-600 truncate">{a.aggregated_summary}</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </SectionCard>
  );
}

// ─── Widget: Auto-Fix ─────────────────────────────────────────────────────────

function AutoFixWidget() {
  const [fixes, setFixes] = useState<AutoFix[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    supabase
      .from('hermes_autofix_actions')
      .select('id,issue_type,action_taken,status,created_at')
      .order('created_at', { ascending: false })
      .limit(6)
      .then(({ data }) => { setFixes(data ?? []); setLoading(false); });
  }, []);

  const statusColor = (s: string) =>
    s === 'completed' ? 'green' : s === 'failed' ? 'red' : s === 'awaiting_approval' ? 'amber' : 'slate';

  return (
    <SectionCard title="Auto-Fix Actions" icon={Zap}>
      {loading ? (
        <div className="flex justify-center py-6"><Loader2 className="w-5 h-5 animate-spin text-slate-300" /></div>
      ) : fixes.length === 0 ? (
        <p className="text-[10px] font-bold text-slate-400 text-center py-4 uppercase tracking-widest">No auto-fix actions yet</p>
      ) : (
        <div className="space-y-2">
          {fixes.map(f => (
            <div key={f.id} className="flex items-center justify-between py-2 border-b border-slate-50 last:border-0">
              <div className="flex-1 min-w-0">
                <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">{f.issue_type.replace(/_/g, ' ')}</p>
                <p className="text-xs text-slate-600 truncate">{f.action_taken}</p>
              </div>
              {badge(f.status, statusColor(f.status))}
            </div>
          ))}
        </div>
      )}
    </SectionCard>
  );
}

// ─── Widget: Leads ────────────────────────────────────────────────────────────

function LeadsWidget() {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    supabase
      .from('leads')
      .select('id,name,status,estimated_value,created_at')
      .order('created_at', { ascending: false })
      .limit(8)
      .then(({ data }) => { setLeads(data ?? []); setLoading(false); });
  }, []);

  const stageColor: Record<string, string> = {
    new: 'blue', contacted: 'purple', qualified: 'amber',
    proposal: 'amber', negotiation: 'amber', won: 'green', lost: 'red', cold: 'slate',
  };
  const total = leads.length;
  const won = leads.filter(l => l.status === 'won').length;
  const pipeline = leads.reduce((s, l) => s + (l.estimated_value ?? 0), 0);

  return (
    <SectionCard
      title="Lead Pipeline"
      icon={Users}
      action={<span className="text-[9px] font-black text-slate-400">${pipeline.toLocaleString()} pipeline</span>}
    >
      {loading ? (
        <div className="flex justify-center py-6"><Loader2 className="w-5 h-5 animate-spin text-slate-300" /></div>
      ) : leads.length === 0 ? (
        <p className="text-[10px] font-bold text-slate-400 text-center py-4 uppercase tracking-widest">No leads yet</p>
      ) : (
        <>
          <div className="flex gap-4 mb-3">
            <div className="text-center"><p className="text-lg font-black text-[#1A2244]">{total}</p><p className="text-[9px] text-slate-400 uppercase tracking-wider">Total</p></div>
            <div className="text-center"><p className="text-lg font-black text-green-600">{won}</p><p className="text-[9px] text-slate-400 uppercase tracking-wider">Won</p></div>
            <div className="text-center"><p className="text-lg font-black text-[#5B7CFA]">{total - won}</p><p className="text-[9px] text-slate-400 uppercase tracking-wider">Active</p></div>
          </div>
          <div className="space-y-1.5">
            {leads.slice(0, 5).map(l => (
              <div key={l.id} className="flex items-center justify-between py-1.5 border-b border-slate-50 last:border-0">
                <span className="text-xs font-bold text-[#1A2244] truncate max-w-[140px]">{l.name || 'Unknown'}</span>
                <div className="flex items-center gap-2">
                  {l.estimated_value ? <span className="text-[10px] font-black text-green-600">${l.estimated_value.toLocaleString()}</span> : null}
                  {badge(l.status, stageColor[l.status] || 'slate')}
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </SectionCard>
  );
}

// ─── Widget: Revenue ──────────────────────────────────────────────────────────

function RevenueWidget() {
  const [events, setEvents] = useState<RevenueEvent[]>([]);
  const [loading, setLoading] = useState(true);

  const month = new Date().toISOString().slice(0, 7);
  useEffect(() => {
    supabase
      .from('revenue_events')
      .select('id,event_type,amount,created_at')
      .eq('period_month', month)
      .order('created_at', { ascending: false })
      .limit(20)
      .then(({ data }) => { setEvents(data ?? []); setLoading(false); });
  }, [month]);

  const total = events.reduce((s, e) => s + e.amount, 0);
  const mrr = events
    .filter(e => ['subscription_start', 'upgrade'].includes(e.event_type))
    .reduce((s, e) => s + e.amount, 0)
    - events
      .filter(e => ['downgrade', 'churn'].includes(e.event_type))
      .reduce((s, e) => s + e.amount, 0);

  return (
    <SectionCard
      title="Revenue This Month"
      icon={DollarSign}
      action={<span className="text-[9px] font-black text-green-600">${total.toLocaleString()} total</span>}
    >
      {loading ? (
        <div className="flex justify-center py-6"><Loader2 className="w-5 h-5 animate-spin text-slate-300" /></div>
      ) : events.length === 0 ? (
        <p className="text-[10px] font-bold text-slate-400 text-center py-4 uppercase tracking-widest">No revenue events this month</p>
      ) : (
        <>
          <div className="flex gap-4 mb-3">
            <div><p className="text-lg font-black text-[#1A2244]">${total.toLocaleString()}</p><p className="text-[9px] text-slate-400 uppercase tracking-wider">Total</p></div>
            <div><p className="text-lg font-black text-[#5B7CFA]">${mrr.toLocaleString()}</p><p className="text-[9px] text-slate-400 uppercase tracking-wider">MRR</p></div>
          </div>
          <div className="space-y-1.5">
            {events.slice(0, 5).map(e => (
              <div key={e.id} className="flex items-center justify-between py-1.5 border-b border-slate-50 last:border-0">
                <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">{e.event_type.replace(/_/g, ' ')}</span>
                <span className="text-xs font-black text-green-600">${e.amount.toLocaleString()}</span>
              </div>
            ))}
          </div>
        </>
      )}
    </SectionCard>
  );
}

// ─── Widget: Launch KPIs ──────────────────────────────────────────────────────

function LaunchWidget() {
  const [metrics, setMetrics] = useState<LaunchMetric[]>([]);
  const [loading, setLoading] = useState(true);
  const today = new Date().toISOString().slice(0, 10);

  useEffect(() => {
    supabase
      .from('launch_metrics')
      .select('id,metric_name,metric_value,target_value,unit')
      .eq('period', 'daily')
      .eq('period_label', today)
      .order('metric_name')
      .limit(10)
      .then(({ data }) => { setMetrics(data ?? []); setLoading(false); });
  }, [today]);

  const getColor = (m: LaunchMetric) => {
    if (!m.target_value) return 'slate';
    const pct = m.metric_value / m.target_value;
    if (pct >= 1) return 'green';
    if (pct >= 0.7) return 'amber';
    return 'red';
  };

  return (
    <SectionCard title="Launch KPIs Today" icon={Rocket}>
      {loading ? (
        <div className="flex justify-center py-6"><Loader2 className="w-5 h-5 animate-spin text-slate-300" /></div>
      ) : metrics.length === 0 ? (
        <p className="text-[10px] font-bold text-slate-400 text-center py-4 uppercase tracking-widest">No metrics recorded today</p>
      ) : (
        <div className="space-y-2">
          {metrics.map(m => {
            const pct = m.target_value ? Math.min((m.metric_value / m.target_value) * 100, 100) : null;
            return (
              <div key={m.id}>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-[10px] font-bold text-slate-600">{m.metric_name.replace(/_/g, ' ')}</span>
                  <div className="flex items-center gap-1.5">
                    <span className="text-xs font-black text-[#1A2244]">{m.metric_value.toFixed(1)}</span>
                    {m.target_value ? <span className="text-[9px] text-slate-400">/ {m.target_value.toFixed(1)}</span> : null}
                    {badge(pct !== null ? `${Math.round(pct)}%` : 'no target', getColor(m))}
                  </div>
                </div>
                {pct !== null && (
                  <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
                    <div
                      className={cn('h-full rounded-full transition-all', pct >= 100 ? 'bg-green-400' : pct >= 70 ? 'bg-amber-400' : 'bg-red-400')}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </SectionCard>
  );
}

// ─── Widget: Communications ───────────────────────────────────────────────────

function CommsWidget() {
  const [logs, setLogs] = useState<CommsLog[]>([]);
  const [loading, setLoading] = useState(true);

  const cutoff = new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString();
  useEffect(() => {
    supabase
      .from('hermes_comms_log')
      .select('id,channel,status,created_at')
      .gt('created_at', cutoff)
      .order('created_at', { ascending: false })
      .limit(30)
      .then(({ data }) => { setLogs(data ?? []); setLoading(false); });
  }, []);

  const sent = logs.filter(l => l.status === 'sent').length;
  const failed = logs.filter(l => l.status === 'failed').length;
  const pending = logs.filter(l => ['pending', 'retrying'].includes(l.status)).length;

  return (
    <SectionCard title="Comms Health (24h)" icon={MessageSquare}>
      {loading ? (
        <div className="flex justify-center py-6"><Loader2 className="w-5 h-5 animate-spin text-slate-300" /></div>
      ) : logs.length === 0 ? (
        <p className="text-[10px] font-bold text-slate-400 text-center py-4 uppercase tracking-widest">No comms in 24h</p>
      ) : (
        <div className="space-y-3">
          <div className="flex gap-4">
            <div className="text-center"><p className="text-lg font-black text-green-600">{sent}</p><p className="text-[9px] text-slate-400 uppercase">Sent</p></div>
            <div className="text-center"><p className="text-lg font-black text-red-500">{failed}</p><p className="text-[9px] text-slate-400 uppercase">Failed</p></div>
            <div className="text-center"><p className="text-lg font-black text-amber-500">{pending}</p><p className="text-[9px] text-slate-400 uppercase">Pending</p></div>
          </div>
          <div className="h-2 bg-slate-100 rounded-full overflow-hidden flex">
            <div className="bg-green-400 h-full" style={{ width: `${(sent / logs.length) * 100}%` }} />
            <div className="bg-amber-400 h-full" style={{ width: `${(pending / logs.length) * 100}%` }} />
            <div className="bg-red-400 h-full" style={{ width: `${(failed / logs.length) * 100}%` }} />
          </div>
          <p className="text-[9px] text-slate-400 text-center">{logs.length} total messages</p>
        </div>
      )}
    </SectionCard>
  );
}

// ─── Widget: Approvals ────────────────────────────────────────────────────────

function ApprovalsWidget() {
  const [items, setItems] = useState<Approval[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    supabase
      .from('owner_approval_queue')
      .select('id,action_type,description,priority,requested_by,created_at')
      .eq('status', 'pending')
      .order('priority')
      .order('created_at')
      .limit(8)
      .then(({ data }) => { setItems(data ?? []); setLoading(false); });
  }, []);

  const priorityColor: Record<string, string> = { urgent: 'red', normal: 'amber', low: 'slate' };

  return (
    <SectionCard
      title="Pending Approvals"
      icon={Clock}
      action={items.length > 0 ? <span className="text-[9px] font-black text-amber-500">{items.length} awaiting</span> : undefined}
    >
      {loading ? (
        <div className="flex justify-center py-6"><Loader2 className="w-5 h-5 animate-spin text-slate-300" /></div>
      ) : items.length === 0 ? (
        <div className="flex items-center gap-2 text-green-600 py-4">
          <CheckCircle2 className="w-4 h-4" />
          <span className="text-xs font-bold">No pending approvals</span>
        </div>
      ) : (
        <div className="space-y-2">
          {items.map(item => (
            <div key={item.id} className="p-3 rounded-xl border border-slate-100 bg-slate-50/50">
              <div className="flex items-center justify-between mb-1">
                <span className="text-[9px] font-black text-slate-500 uppercase tracking-wider">{item.action_type.replace(/_/g, ' ')}</span>
                {badge(item.priority, priorityColor[item.priority] || 'slate')}
              </div>
              <p className="text-xs text-slate-600 truncate">{item.description}</p>
              <p className="text-[9px] text-slate-400 mt-1">By {item.requested_by} · {new Date(item.created_at).toLocaleDateString()}</p>
            </div>
          ))}
          <p className="text-[9px] text-slate-400 text-center mt-1">Use Telegram: /approve or /reject &lt;id&gt;</p>
        </div>
      )}
    </SectionCard>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────────

export function AdminCEOMode() {
  const [refreshKey, setRefreshKey] = useState(0);

  return (
    <div className="p-8 space-y-8 bg-slate-50/50 min-h-full text-slate-600">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-black text-[#1A2244] tracking-tight">CEO Mode</h1>
          <p className="text-slate-500 font-medium mt-1 text-sm">
            Aggregated business intelligence, auto-fix, leads, revenue, and owner approvals.
          </p>
        </div>
        <button
          onClick={() => setRefreshKey(k => k + 1)}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-white border border-slate-200 text-xs font-bold text-slate-500 hover:bg-slate-50 transition-all"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          Refresh
        </button>
      </div>

      <div key={refreshKey} className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
        <div className="lg:col-span-2 xl:col-span-2">
          <CEOStatusWidget />
        </div>
        <ApprovalsWidget />
        <LeadsWidget />
        <RevenueWidget />
        <LaunchWidget />
        <AutoFixWidget />
        <div className="lg:col-span-2 xl:col-span-1">
          <CommsWidget />
        </div>
      </div>
    </div>
  );
}
