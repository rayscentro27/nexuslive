import React, { useEffect, useState, useMemo } from 'react';
import { Users, Search, Filter, Mail, Loader2, ArrowUpDown } from 'lucide-react';
import { cn } from '../../lib/utils';
import { getAllClients, UserProfile } from '../../lib/db';

export function AdminClients() {
  const [clients, setClients] = useState<UserProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [sortBy, setSortBy] = useState<'readiness' | 'joined' | 'plan'>('joined');

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
                        <button className="px-4 py-2 bg-blue-50 text-[#5B7CFA] text-[10px] font-black uppercase tracking-widest rounded-lg hover:bg-[#5B7CFA] hover:text-white transition-all">
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
    </div>
  );
}
