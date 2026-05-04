import React, { useEffect, useState, useMemo } from 'react';
import { Users, Search, Loader2, X, CheckCircle2, Circle } from 'lucide-react';
import { cn } from '../../lib/utils';
import { getAllClients, UserProfile } from '../../lib/db';
import { supabase } from '../../lib/supabase';

interface ClientDetail {
  entity: { business_name: string | null; entity_type: string | null; ein: string | null; formation_state: string | null } | null;
  credit: { score: number | null; score_band: string | null; utilization_percent: number | null } | null;
  tasks: { id: string; title: string; status: string; priority: number }[];
}

const PLANS = ['free', 'pilot', 'pro', 'elite'];

function ManagePanel({ client, onClose, onPlanChange }: {
  client: UserProfile;
  onClose: () => void;
  onPlanChange: (id: string, plan: string) => void;
}) {
  const [detail, setDetail] = useState<ClientDetail>({ entity: null, credit: null, tasks: [] });
  const [loading, setLoading] = useState(true);
  const [plan, setPlan] = useState(client.subscription_plan);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    Promise.all([
      supabase.from('business_entities').select('business_name,entity_type,ein,formation_state').eq('user_id', client.id).maybeSingle(),
      supabase.from('credit_reports').select('score,score_band,utilization_percent').eq('user_id', client.id).order('created_at', { ascending: false }).limit(1).maybeSingle(),
      supabase.from('tasks').select('id,title,status,priority').eq('user_id', client.id).order('priority').limit(8),
    ]).then(([{ data: entity }, { data: credit }, { data: tasks }]) => {
      setDetail({ entity: entity as any, credit: credit as any, tasks: (tasks ?? []) as any });
      setLoading(false);
    });
  }, [client.id]);

  const savePlan = async () => {
    setSaving(true);
    await supabase.from('user_profiles').update({ subscription_plan: plan }).eq('id', client.id);
    onPlanChange(client.id, plan);
    setSaving(false);
  };

  return (
    <div style={{ position: 'fixed', inset: 0, zIndex: 1000, display: 'flex' }}>
      <div style={{ flex: 1, background: 'rgba(0,0,0,0.35)' }} onClick={onClose} />
      <div style={{ width: 440, background: '#fff', height: '100%', overflowY: 'auto', boxShadow: '-8px 0 40px rgba(0,0,0,0.15)', display: 'flex', flexDirection: 'column' }}>
        {/* Header */}
        <div style={{ padding: '24px 24px 16px', borderBottom: '1px solid #e8e9f2', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexShrink: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
            <div style={{ width: 44, height: 44, borderRadius: 12, background: '#C5C9F7', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 18, fontWeight: 800, color: '#5B7CFA' }}>
              {(client.full_name ?? 'U').charAt(0).toUpperCase()}
            </div>
            <div>
              <p style={{ fontSize: 16, fontWeight: 800, color: '#1a1c3a', margin: 0 }}>{client.full_name ?? 'Unknown'}</p>
              <p style={{ fontSize: 11, color: '#8b8fa8', margin: 0 }}>Readiness: {client.readiness_score}% · Joined {new Date(client.created_at).toLocaleDateString()}</p>
            </div>
          </div>
          <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#8b8fa8' }}><X size={20} /></button>
        </div>

        {loading ? (
          <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Loader2 size={24} color="#8b8fa8" style={{ animation: 'spin 1s linear infinite' }} />
          </div>
        ) : (
          <div style={{ padding: 24, display: 'flex', flexDirection: 'column', gap: 20 }}>
            {/* Plan */}
            <div style={{ padding: 16, border: '1px solid #e8e9f2', borderRadius: 14 }}>
              <p style={{ fontSize: 11, fontWeight: 700, color: '#8b8fa8', margin: '0 0 10px', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Subscription Plan</p>
              <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                <select
                  value={plan}
                  onChange={e => setPlan(e.target.value)}
                  style={{ flex: 1, padding: '8px 12px', borderRadius: 10, border: '1.5px solid #e8e9f2', fontSize: 14, fontWeight: 700, color: '#1a1c3a', outline: 'none' }}
                >
                  {PLANS.map(p => <option key={p} value={p}>{p.charAt(0).toUpperCase() + p.slice(1)}</option>)}
                </select>
                <button
                  onClick={savePlan}
                  disabled={saving || plan === client.subscription_plan}
                  style={{ padding: '8px 16px', borderRadius: 10, border: 'none', background: '#3d5af1', color: '#fff', fontSize: 13, fontWeight: 700, cursor: 'pointer', opacity: saving || plan === client.subscription_plan ? 0.5 : 1 }}
                >
                  {saving ? 'Saving…' : 'Save'}
                </button>
              </div>
            </div>

            {/* Business Entity */}
            <div style={{ padding: 16, border: '1px solid #e8e9f2', borderRadius: 14 }}>
              <p style={{ fontSize: 11, fontWeight: 700, color: '#8b8fa8', margin: '0 0 10px', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Business Entity</p>
              {detail.entity ? (
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  {[
                    { label: 'Name', value: detail.entity.business_name },
                    { label: 'Type', value: detail.entity.entity_type },
                    { label: 'EIN', value: detail.entity.ein },
                    { label: 'State', value: detail.entity.formation_state },
                  ].map(f => (
                    <div key={f.label} style={{ padding: '8px 10px', background: '#f7f8ff', borderRadius: 8 }}>
                      <p style={{ fontSize: 10, color: '#8b8fa8', margin: '0 0 2px', fontWeight: 700, textTransform: 'uppercase' }}>{f.label}</p>
                      <p style={{ fontSize: 13, fontWeight: 700, color: f.value ? '#1a1c3a' : '#c7d2fe', margin: 0 }}>{f.value ?? '—'}</p>
                    </div>
                  ))}
                </div>
              ) : (
                <p style={{ fontSize: 13, color: '#8b8fa8' }}>No business entity on file.</p>
              )}
            </div>

            {/* Credit */}
            <div style={{ padding: 16, border: '1px solid #e8e9f2', borderRadius: 14 }}>
              <p style={{ fontSize: 11, fontWeight: 700, color: '#8b8fa8', margin: '0 0 10px', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Credit Report</p>
              {detail.credit ? (
                <div style={{ display: 'flex', gap: 12 }}>
                  <div style={{ textAlign: 'center', flex: 1, padding: '10px', background: '#f7f8ff', borderRadius: 10 }}>
                    <p style={{ fontSize: 28, fontWeight: 800, color: '#3d5af1', margin: 0 }}>{detail.credit.score ?? '—'}</p>
                    <p style={{ fontSize: 10, color: '#8b8fa8', margin: 0 }}>FICO Score</p>
                  </div>
                  <div style={{ textAlign: 'center', flex: 1, padding: '10px', background: '#f7f8ff', borderRadius: 10 }}>
                    <p style={{ fontSize: 28, fontWeight: 800, color: (detail.credit.utilization_percent ?? 0) > 30 ? '#ef4444' : '#22c55e', margin: 0 }}>{detail.credit.utilization_percent ?? '—'}%</p>
                    <p style={{ fontSize: 10, color: '#8b8fa8', margin: 0 }}>Utilization</p>
                  </div>
                  <div style={{ textAlign: 'center', flex: 1, padding: '10px', background: '#f7f8ff', borderRadius: 10 }}>
                    <p style={{ fontSize: 14, fontWeight: 800, color: '#1a1c3a', margin: 0 }}>{detail.credit.score_band ?? '—'}</p>
                    <p style={{ fontSize: 10, color: '#8b8fa8', margin: 0 }}>Band</p>
                  </div>
                </div>
              ) : (
                <p style={{ fontSize: 13, color: '#8b8fa8' }}>No credit report on file.</p>
              )}
            </div>

            {/* Tasks */}
            <div style={{ padding: 16, border: '1px solid #e8e9f2', borderRadius: 14 }}>
              <p style={{ fontSize: 11, fontWeight: 700, color: '#8b8fa8', margin: '0 0 10px', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Tasks ({detail.tasks.length})</p>
              {detail.tasks.length === 0 ? (
                <p style={{ fontSize: 13, color: '#8b8fa8' }}>No tasks on file.</p>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  {detail.tasks.map(t => (
                    <div key={t.id} style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                      {t.status === 'complete'
                        ? <CheckCircle2 size={14} color="#22c55e" style={{ flexShrink: 0 }} />
                        : <Circle size={14} color="#e8e9f2" style={{ flexShrink: 0 }} />
                      }
                      <span style={{ fontSize: 12, color: t.status === 'complete' ? '#8b8fa8' : '#1a1c3a', textDecoration: t.status === 'complete' ? 'line-through' : 'none' }}>{t.title}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export function AdminClients() {
  const [clients, setClients] = useState<UserProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [sortBy, setSortBy] = useState<'readiness' | 'joined' | 'plan'>('joined');
  const [selectedClient, setSelectedClient] = useState<UserProfile | null>(null);

  useEffect(() => {
    getAllClients().then(({ data }) => {
      setClients(data);
      setLoading(false);
    });
  }, []);

  const filtered = useMemo(() => {
    const q = search.toLowerCase();
    const list = q
      ? clients.filter(c => (c.full_name ?? '').toLowerCase().includes(q) || c.subscription_plan.includes(q))
      : [...clients];

    list.sort((a, b) => {
      if (sortBy === 'readiness') return b.readiness_score - a.readiness_score;
      if (sortBy === 'plan') return a.subscription_plan.localeCompare(b.subscription_plan);
      return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
    });
    return list;
  }, [clients, search, sortBy]);

  const readinessStatus = (score: number) => {
    if (score >= 80) return { label: 'active', color: 'bg-green-50 text-green-600' };
    if (score >= 50) return { label: 'building', color: 'bg-blue-50 text-blue-600' };
    if (score >= 20) return { label: 'early', color: 'bg-amber-50 text-amber-600' };
    return { label: 'new', color: 'bg-slate-100 text-slate-500' };
  };

  const stageFromScore = (score: number) => {
    if (score >= 80) return 'Funding Prep';
    if (score >= 60) return 'Credit Repair';
    if (score >= 40) return 'Bank Setup';
    if (score >= 20) return 'Entity Setup';
    return 'Initial Audit';
  };

  return (
    <div className="p-8 space-y-8 bg-slate-50/50 min-h-full text-slate-600">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-black text-[#1A2244] tracking-tight">Clients</h1>
          <p className="text-slate-500 font-medium mt-1 text-sm">Manage all clients, monitor funding stages, and track progress.</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="px-4 py-2 rounded-xl bg-white border border-slate-200 flex items-center gap-2 shadow-sm">
            <Users className="w-4 h-4 text-slate-400" />
            <span className="text-xs font-bold text-slate-500">{clients.length} clients</span>
          </div>
        </div>
      </div>

      {/* Search & Sort */}
      <div className="flex items-center justify-between gap-4 bg-white p-4 rounded-2xl border border-slate-200 shadow-sm">
        <div className="flex items-center gap-4 flex-1">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input
              type="text"
              placeholder="Search by name or plan..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="w-full bg-slate-50 border border-slate-200 rounded-xl py-2 pl-10 pr-4 text-xs font-medium text-slate-600 focus:outline-none focus:border-[#5B7CFA]/50 transition-all"
            />
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Sort by:</span>
          <select
            value={sortBy}
            onChange={e => setSortBy(e.target.value as any)}
            className="bg-white border border-slate-200 rounded-xl px-3 py-2 text-[10px] font-black text-slate-600 uppercase tracking-widest focus:outline-none focus:border-[#5B7CFA]/50"
          >
            <option value="joined">Joined Date</option>
            <option value="readiness">Readiness Score</option>
            <option value="plan">Plan</option>
          </select>
        </div>
      </div>

      {/* Client Table */}
      <div className="bg-white border border-slate-200 rounded-3xl overflow-hidden shadow-sm">
        {loading ? (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="w-6 h-6 text-slate-300 animate-spin" />
          </div>
        ) : (
          <>
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-100 bg-slate-50/30">
                  <th className="px-6 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest">Client</th>
                  <th className="px-6 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest">Stage</th>
                  <th className="px-6 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest">Readiness</th>
                  <th className="px-6 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest">Plan</th>
                  <th className="px-6 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest">Status</th>
                  <th className="px-6 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50">
                {filtered.length > 0 ? filtered.map((client) => {
                  const { label, color } = readinessStatus(client.readiness_score);
                  const stage = stageFromScore(client.readiness_score);
                  return (
                    <tr key={client.id} className="hover:bg-slate-50/50 transition-colors group">
                      <td className="px-6 py-5">
                        <div className="flex items-center gap-4">
                          <div className="w-10 h-10 rounded-xl bg-[#C5C9F7] flex items-center justify-center font-black text-[#5B7CFA] text-sm shrink-0">
                            {(client.full_name ?? 'U').charAt(0).toUpperCase()}
                          </div>
                          <div className="min-w-0">
                            <p className="text-sm font-black text-[#1A2244] truncate">{client.full_name ?? 'Unknown'}</p>
                            <p className="text-[9px] font-bold text-slate-400 mt-0.5">
                              Joined {new Date(client.created_at).toLocaleDateString()}
                            </p>
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-5">
                        <div className="flex items-center gap-2">
                          <div className={cn("w-1.5 h-1.5 rounded-full", client.readiness_score >= 80 ? "bg-green-500" : "bg-[#5B7CFA]")} />
                          <span className="text-[10px] font-black text-slate-600 uppercase tracking-widest">{stage}</span>
                        </div>
                      </td>
                      <td className="px-6 py-5">
                        <div className="flex items-center gap-3">
                          <div className="flex-1 h-1.5 bg-slate-100 rounded-full overflow-hidden w-24">
                            <div
                              className={cn("h-full rounded-full", client.readiness_score >= 80 ? "bg-green-500" : client.readiness_score >= 50 ? "bg-[#5B7CFA]" : "bg-amber-500")}
                              style={{ width: `${client.readiness_score}%` }}
                            />
                          </div>
                          <span className="text-[10px] font-black text-[#1A2244]">{client.readiness_score}%</span>
                        </div>
                      </td>
                      <td className="px-6 py-5">
                        <span className="text-[10px] font-black text-slate-500 uppercase tracking-widest">{client.subscription_plan}</span>
                      </td>
                      <td className="px-6 py-5">
                        <span className={cn("px-2 py-1 rounded-lg text-[9px] font-black uppercase tracking-widest", color)}>
                          {label}
                        </span>
                      </td>
                      <td className="px-6 py-5 text-right">
                        <button
                          onClick={() => setSelectedClient(client)}
                          className="px-4 py-2 bg-blue-50 text-[#5B7CFA] text-[10px] font-black uppercase tracking-widest rounded-lg hover:bg-[#5B7CFA] hover:text-white transition-all"
                        >
                          Manage
                        </button>
                      </td>
                    </tr>
                  );
                }) : (
                  <tr>
                    <td colSpan={6} className="px-6 py-12 text-center">
                      <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">
                        {search ? 'No clients match your search' : 'No clients yet'}
                      </p>
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
            <div className="p-6 border-t border-slate-100 flex items-center justify-between bg-slate-50/30">
              <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">
                Showing {filtered.length} of {clients.length} clients
              </p>
            </div>
          </>
        )}
      </div>

      {selectedClient && (
        <ManagePanel
          client={selectedClient}
          onClose={() => setSelectedClient(null)}
          onPlanChange={(id, plan) => {
            setClients(prev => prev.map(c => c.id === id ? { ...c, subscription_plan: plan } : c));
            setSelectedClient(prev => prev && prev.id === id ? { ...prev, subscription_plan: plan } : prev);
          }}
        />
      )}
    </div>
  );
}
