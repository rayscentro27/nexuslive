import React, { useEffect, useState, useMemo } from 'react';
import { ShieldCheck, AlertCircle, CheckCircle2, Clock, Search, FileText, TrendingUp, Zap, Loader2 } from 'lucide-react';
import { cn } from '../../lib/utils';
import { getAllCreditReports, getAllCreditDisputes, CreditReport, CreditDispute } from '../../lib/db';

function disputeStatusColor(status: string) {
  switch (status) {
    case 'resolved':  return 'bg-green-50 text-green-600';
    case 'submitted': return 'bg-blue-50 text-[#5B7CFA]';
    case 'rejected':  return 'bg-red-50 text-red-600';
    default:          return 'bg-amber-50 text-amber-600';
  }
}

export function AdminCreditOps() {
  const [reports, setReports] = useState<CreditReport[]>([]);
  const [disputes, setDisputes] = useState<CreditDispute[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [activeTab, setActiveTab] = useState<'reports' | 'disputes'>('disputes');

  useEffect(() => {
    Promise.all([getAllCreditReports(), getAllCreditDisputes()]).then(([{ data: r }, { data: d }]) => {
      setReports(r);
      setDisputes(d);
      setLoading(false);
    });
  }, []);

  const filteredDisputes = useMemo(() => {
    if (!search) return disputes;
    const q = search.toLowerCase();
    return disputes.filter(d => d.creditor.toLowerCase().includes(q) || d.reason.toLowerCase().includes(q));
  }, [disputes, search]);

  const filteredReports = useMemo(() => {
    if (!search) return reports;
    const q = search.toLowerCase();
    return reports.filter(r => (r.score_band ?? '').toLowerCase().includes(q));
  }, [reports, search]);

  const pending = disputes.filter(d => d.status === 'pending').length;
  const resolved = disputes.filter(d => d.status === 'resolved').length;
  const avgScoreIncrease = reports.length > 0
    ? Math.round(reports.reduce((s, r) => s + (r.score ?? 0), 0) / reports.length)
    : 0;

  const colorMap: Record<string, string> = {
    blue: 'bg-blue-50 text-[#5B7CFA]',
    green: 'bg-green-50 text-green-600',
    purple: 'bg-purple-50 text-purple-600',
    amber: 'bg-amber-50 text-amber-600',
  };

  return (
    <div className="p-8 space-y-8 bg-slate-50/50 min-h-full text-slate-600">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-black text-[#1A2244] tracking-tight">Credit Ops</h1>
          <p className="text-slate-500 font-medium mt-1 text-sm">Manage credit repair cases, dispute letters, and bureau integrations.</p>
        </div>
        <button className="px-6 py-2 rounded-xl bg-[#5B7CFA] text-white text-xs font-black uppercase tracking-widest shadow-lg shadow-blue-500/20 hover:bg-[#4A6BEB] transition-all flex items-center gap-2">
          <Zap className="w-4 h-4" /> New Case
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {[
          { label: 'Active Cases', value: String(reports.length), icon: ShieldCheck, color: 'blue' },
          { label: 'Avg Score', value: avgScoreIncrease > 0 ? String(avgScoreIncrease) : '—', icon: TrendingUp, color: 'green' },
          { label: 'Pending Disputes', value: String(pending), icon: Clock, color: 'amber' },
          { label: 'Resolved', value: String(resolved), icon: CheckCircle2, color: 'purple' },
        ].map((stat, i) => (
          <div key={i} className="bg-white border border-slate-200 p-6 rounded-3xl shadow-sm">
            <div className="flex items-center gap-4">
              <div className={cn("w-12 h-12 rounded-2xl flex items-center justify-center", colorMap[stat.color])}>
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

      {/* Tabs */}
      <div className="flex gap-1.5 p-1 bg-slate-100 rounded-xl w-fit">
        {(['disputes', 'reports'] as const).map(tab => (
          <button key={tab} onClick={() => setActiveTab(tab)}
            className={cn("px-4 py-1.5 rounded-lg text-[10px] font-black uppercase tracking-widest transition-all",
              activeTab === tab ? "bg-white text-[#5B7CFA] shadow-sm" : "text-slate-500 hover:text-slate-700"
            )}>
            {tab === 'disputes' ? `Disputes (${disputes.length})` : `Credit Reports (${reports.length})`}
          </button>
        ))}
      </div>

      <div className="bg-white border border-slate-200 rounded-3xl overflow-hidden shadow-sm">
        <div className="p-6 border-b border-slate-100 flex items-center justify-between bg-slate-50/30">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-blue-50 flex items-center justify-center text-[#5B7CFA]">
              <FileText className="w-4 h-4" />
            </div>
            <h3 className="text-sm font-black text-[#1A2244] uppercase tracking-widest">
              {activeTab === 'disputes' ? 'Dispute Cases' : 'Credit Reports'}
            </h3>
          </div>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400" />
            <input type="text" placeholder={`Search ${activeTab}...`} value={search} onChange={e => setSearch(e.target.value)}
              className="bg-slate-50 border border-slate-200 rounded-xl py-1.5 pl-9 pr-4 text-[10px] font-bold text-slate-600 focus:outline-none focus:border-[#5B7CFA]/50 w-48" />
          </div>
        </div>
        {loading ? (
          <div className="flex items-center justify-center py-16"><Loader2 className="w-6 h-6 text-slate-300 animate-spin" /></div>
        ) : activeTab === 'disputes' ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-50">
                  {['Creditor', 'Reason', 'Amount', 'Status', 'Submitted'].map(h => (
                    <th key={h} className="px-6 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50">
                {filteredDisputes.length > 0 ? filteredDisputes.map(d => (
                  <tr key={d.id} className="hover:bg-slate-50/50 transition-colors">
                    <td className="px-6 py-4"><span className="text-xs font-bold text-[#1A2244]">{d.creditor}</span></td>
                    <td className="px-6 py-4"><span className="text-xs text-slate-500 max-w-[200px] truncate block">{d.reason}</span></td>
                    <td className="px-6 py-4"><span className="text-xs font-black text-[#5B7CFA]">{d.amount ? '$' + d.amount.toLocaleString() : '—'}</span></td>
                    <td className="px-6 py-4">
                      <span className={cn("px-2 py-1 rounded-lg text-[9px] font-black uppercase tracking-widest", disputeStatusColor(d.status))}>
                        {d.status}
                      </span>
                    </td>
                    <td className="px-6 py-4"><span className="text-xs text-slate-400">{d.submitted_at ? new Date(d.submitted_at).toLocaleDateString() : '—'}</span></td>
                  </tr>
                )) : (
                  <tr><td colSpan={5} className="px-6 py-12 text-center">
                    <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">{search ? 'No matches' : 'No disputes on file'}</p>
                  </td></tr>
                )}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-50">
                  {['Score', 'Band', 'Funding Range', 'Utilization', 'Total Debt', 'Date'].map(h => (
                    <th key={h} className="px-6 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50">
                {filteredReports.length > 0 ? filteredReports.map(r => (
                  <tr key={r.id} className="hover:bg-slate-50/50 transition-colors">
                    <td className="px-6 py-4"><span className="text-xl font-black text-[#5B7CFA]">{r.score ?? '—'}</span></td>
                    <td className="px-6 py-4"><span className="text-xs font-bold text-slate-600">{r.score_band ?? '—'}</span></td>
                    <td className="px-6 py-4">
                      <span className="text-xs font-bold text-green-600">
                        {r.funding_range_min && r.funding_range_max
                          ? `$${r.funding_range_min.toLocaleString()} – $${r.funding_range_max.toLocaleString()}`
                          : '—'}
                      </span>
                    </td>
                    <td className="px-6 py-4"><span className="text-xs font-bold text-slate-600">{r.utilization_percent != null ? `${r.utilization_percent}%` : '—'}</span></td>
                    <td className="px-6 py-4"><span className="text-xs font-bold text-slate-600">{r.total_debt ? '$' + r.total_debt.toLocaleString() : '—'}</span></td>
                    <td className="px-6 py-4"><span className="text-xs text-slate-400">{r.report_date ? new Date(r.report_date).toLocaleDateString() : '—'}</span></td>
                  </tr>
                )) : (
                  <tr><td colSpan={6} className="px-6 py-12 text-center">
                    <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">No credit reports on file</p>
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
