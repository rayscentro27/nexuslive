import React, { useEffect, useState, useMemo } from 'react';
import { Lightbulb, DollarSign, Search, Target, Zap, Loader2, Plus } from 'lucide-react';
import { cn } from '../../lib/utils';
import { getBusinessOpportunities, BusinessOpportunity } from '../../lib/db';

function typeColor(type: string) {
  switch (type.toLowerCase()) {
    case 'funding':     return 'bg-blue-50 text-[#5B7CFA]';
    case 'grant':       return 'bg-green-50 text-green-600';
    case 'partnership': return 'bg-purple-50 text-purple-600';
    case 'growth':      return 'bg-amber-50 text-amber-600';
    case 'ai_detected': return 'bg-pink-50 text-pink-600';
    default:            return 'bg-slate-100 text-slate-500';
  }
}

function statusColor(status: string) {
  switch (status) {
    case 'active':   return 'bg-green-50 text-green-600';
    case 'applied':  return 'bg-blue-50 text-[#5B7CFA]';
    case 'archived': return 'bg-slate-100 text-slate-400';
    default:         return 'bg-slate-100 text-slate-500';
  }
}

function fmtRange(min: number | null, max: number | null) {
  if (!min && !max) return '—';
  const fmt = (n: number) => n >= 1000 ? '$' + (n / 1000).toFixed(0) + 'k' : '$' + n;
  if (min && max) return `${fmt(min)} – ${fmt(max)}`;
  return fmt(min ?? max!);
}

export function AdminBusinessOpportunities() {
  const [opps, setOpps] = useState<BusinessOpportunity[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');

  useEffect(() => {
    getBusinessOpportunities().then(({ data }) => {
      setOpps(data);
      setLoading(false);
    });
  }, []);

  const filtered = useMemo(() => {
    if (!search) return opps;
    const q = search.toLowerCase();
    return opps.filter(o => o.title.toLowerCase().includes(q) || o.type.toLowerCase().includes(q));
  }, [opps, search]);

  const active = opps.filter(o => o.status === 'active').length;
  const totalPotential = opps.reduce((s, o) => s + (o.value_max ?? o.value_min ?? 0), 0);

  return (
    <div className="p-8 space-y-8 bg-slate-50/50 min-h-full text-slate-600">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-black text-[#1A2244] tracking-tight">Business Opportunities</h1>
          <p className="text-slate-500 font-medium mt-1 text-sm">Identify and manage high-potential business ventures for clients.</p>
        </div>
        <button className="px-6 py-2 rounded-xl bg-[#5B7CFA] text-white text-xs font-black uppercase tracking-widest shadow-lg shadow-blue-500/20 hover:bg-[#4A6BEB] transition-all flex items-center gap-2">
          <Plus className="w-4 h-4" /> Add Opportunity
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {[
          { label: 'Active Opps', value: String(active), icon: Lightbulb, color: 'blue' },
          { label: 'Total Potential', value: totalPotential >= 1000 ? '$' + (totalPotential / 1000).toFixed(0) + 'k' : '$' + totalPotential, icon: DollarSign, color: 'green' },
          { label: 'Total Listed', value: String(opps.length), icon: Target, color: 'purple' },
          { label: 'Applied', value: String(opps.filter(o => o.status === 'applied').length), icon: Zap, color: 'amber' },
        ].map((stat, i) => (
          <div key={i} className="bg-white border border-slate-200 p-6 rounded-3xl shadow-sm">
            <div className="flex items-center gap-4">
              <div className={cn("w-12 h-12 rounded-2xl flex items-center justify-center",
                stat.color === 'blue' ? "bg-blue-50 text-[#5B7CFA]" :
                stat.color === 'green' ? "bg-green-50 text-green-600" :
                stat.color === 'purple' ? "bg-purple-50 text-purple-600" :
                "bg-amber-50 text-amber-600")}>
                <stat.icon className="w-6 h-6" />
              </div>
              <div>
                <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">{stat.label}</p>
                <h3 className="text-xl font-black text-[#1A2244] mt-0.5">{loading ? '—' : stat.value}</h3>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="bg-white border border-slate-200 rounded-3xl overflow-hidden shadow-sm">
        <div className="p-6 border-b border-slate-100 flex items-center justify-between bg-slate-50/30">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-blue-50 flex items-center justify-center text-[#5B7CFA]">
              <Target className="w-4 h-4" />
            </div>
            <h3 className="text-sm font-black text-[#1A2244] uppercase tracking-widest">Opportunities</h3>
          </div>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400" />
            <input type="text" placeholder="Search..." value={search} onChange={e => setSearch(e.target.value)}
              className="bg-slate-50 border border-slate-200 rounded-xl py-1.5 pl-9 pr-4 text-[10px] font-bold text-slate-600 focus:outline-none focus:border-[#5B7CFA]/50 w-48" />
          </div>
        </div>
        {loading ? (
          <div className="flex items-center justify-center py-16"><Loader2 className="w-6 h-6 text-slate-300 animate-spin" /></div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-50">
                  {['Title', 'Type', 'Value Range', 'Deadline', 'Client Facing', 'Status'].map(h => (
                    <th key={h} className="px-6 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50">
                {filtered.length > 0 ? filtered.map(opp => (
                  <tr key={opp.id} className="hover:bg-slate-50/50 transition-colors">
                    <td className="px-6 py-4">
                      <div>
                        <p className="text-xs font-bold text-[#1A2244]">{opp.title}</p>
                        {opp.description && <p className="text-[9px] text-slate-400 mt-0.5 truncate max-w-[200px]">{opp.description}</p>}
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <span className={cn("px-2 py-1 rounded-lg text-[9px] font-black uppercase tracking-widest", typeColor(opp.type))}>
                        {opp.type.replace('_', ' ')}
                      </span>
                    </td>
                    <td className="px-6 py-4"><span className="text-xs font-black text-green-600">{fmtRange(opp.value_min, opp.value_max)}</span></td>
                    <td className="px-6 py-4"><span className="text-xs text-slate-400">{opp.deadline ? new Date(opp.deadline).toLocaleDateString() : '—'}</span></td>
                    <td className="px-6 py-4">
                      <span className={cn("px-2 py-1 rounded-lg text-[9px] font-black uppercase tracking-widest",
                        opp.is_client_facing ? "bg-green-50 text-green-600" : "bg-slate-100 text-slate-400")}>
                        {opp.is_client_facing ? 'Yes' : 'Admin Only'}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <span className={cn("px-2 py-1 rounded-lg text-[9px] font-black uppercase tracking-widest", statusColor(opp.status))}>
                        {opp.status}
                      </span>
                    </td>
                  </tr>
                )) : (
                  <tr><td colSpan={6} className="px-6 py-12 text-center">
                    <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">{search ? 'No matches' : 'No opportunities yet'}</p>
                    {!search && <p className="text-xs text-slate-400 mt-1">Click "Add Opportunity" to create your first one</p>}
                  </td></tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
