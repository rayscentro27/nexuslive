import React, { useEffect, useState, useMemo } from 'react';
import { TrendingUp, DollarSign, CheckCircle2, Clock, Search, Briefcase, Loader2 } from 'lucide-react';
import { cn } from '../../lib/utils';
import { getAllFundingApplications, FundingApplication } from '../../lib/db';

function fmtMoney(n: number | null) {
  if (!n) return '—';
  if (n >= 1_000_000) return '$' + (n / 1_000_000).toFixed(1) + 'M';
  if (n >= 1_000) return '$' + (n / 1_000).toFixed(0) + 'k';
  return '$' + n.toLocaleString();
}

function statusColor(status: string) {
  switch (status.toLowerCase()) {
    case 'approved':  return 'bg-green-50 text-green-600';
    case 'pending':   return 'bg-blue-50 text-[#5B7CFA]';
    case 'submitted': return 'bg-amber-50 text-amber-600';
    case 'rejected':  return 'bg-red-50 text-red-600';
    default:          return 'bg-slate-100 text-slate-500';
  }
}

export function AdminFunding() {
  const [applications, setApplications] = useState<FundingApplication[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');

  useEffect(() => {
    getAllFundingApplications().then(({ data }) => {
      setApplications(data);
      setLoading(false);
    });
  }, []);

  const filtered = useMemo(() => {
    if (!search) return applications;
    const q = search.toLowerCase();
    return applications.filter(a =>
      (a.lender_name ?? '').toLowerCase().includes(q) ||
      (a.product_type ?? '').toLowerCase().includes(q) ||
      a.status.toLowerCase().includes(q)
    );
  }, [applications, search]);

  const pipeline = applications.reduce((s, a) => s + (a.requested_amount ?? 0), 0);
  const approved = applications.filter(a => a.status === 'approved');
  const pending = applications.filter(a => a.status === 'pending' || a.status === 'submitted');
  const approvalRate = applications.length > 0 ? Math.round((approved.length / applications.length) * 100) : 0;
  const avgDeal = applications.length > 0
    ? Math.round(pipeline / applications.length) : 0;

  const colorMap: Record<string, string> = {
    blue: 'bg-blue-50 text-[#5B7CFA]',
    green: 'bg-green-50 text-green-600',
    purple: 'bg-purple-50 text-purple-600',
    amber: 'bg-amber-50 text-amber-600',
  };

  return (
    <div className="p-8 space-y-8 bg-slate-50/50 min-h-full text-slate-600">
      <div>
        <h1 className="text-3xl font-black text-[#1A2244] tracking-tight">Funding Engine</h1>
        <p className="text-slate-500 font-medium mt-1 text-sm">Monitor client funding applications and manage application flow.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {[
          { label: 'Total Pipeline', value: fmtMoney(pipeline), icon: DollarSign, color: 'blue' },
          { label: 'Avg Deal Size', value: fmtMoney(avgDeal), icon: TrendingUp, color: 'green' },
          { label: 'Approval Rate', value: `${approvalRate}%`, icon: CheckCircle2, color: 'purple' },
          { label: 'Pending Review', value: String(pending.length), icon: Clock, color: 'amber' },
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

      <div className="bg-white border border-slate-200 rounded-3xl overflow-hidden shadow-sm">
        <div className="p-6 border-b border-slate-100 flex items-center justify-between bg-slate-50/30">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-blue-50 flex items-center justify-center text-[#5B7CFA]">
              <Briefcase className="w-4 h-4" />
            </div>
            <h3 className="text-sm font-black text-[#1A2244] uppercase tracking-widest">All Applications</h3>
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
                  {['Lender', 'Product', 'Requested', 'Approved', 'Odds', 'Status'].map(h => (
                    <th key={h} className="px-6 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50">
                {filtered.length > 0 ? filtered.map(app => (
                  <tr key={app.id} className="hover:bg-slate-50/50 transition-colors">
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-lg bg-blue-50 flex items-center justify-center font-black text-[#5B7CFA] text-sm">
                          {(app.lender_name ?? '?')[0].toUpperCase()}
                        </div>
                        <span className="text-xs font-bold text-[#1A2244]">{app.lender_name ?? '—'}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4"><span className="text-[10px] font-black text-slate-500 uppercase tracking-widest">{app.product_type ?? '—'}</span></td>
                    <td className="px-6 py-4"><span className="text-xs font-black text-[#5B7CFA]">{fmtMoney(app.requested_amount)}</span></td>
                    <td className="px-6 py-4"><span className="text-xs font-black text-green-600">{fmtMoney(app.approved_amount)}</span></td>
                    <td className="px-6 py-4">
                      {app.approval_odds !== null ? (
                        <div className="flex items-center gap-2">
                          <div className="w-16 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                            <div className="h-full bg-[#5B7CFA] rounded-full" style={{ width: `${app.approval_odds}%` }} />
                          </div>
                          <span className="text-[10px] font-black text-[#1A2244]">{app.approval_odds}%</span>
                        </div>
                      ) : <span className="text-[10px] text-slate-300">—</span>}
                    </td>
                    <td className="px-6 py-4">
                      <span className={cn("px-2 py-1 rounded-lg text-[9px] font-black uppercase tracking-widest", statusColor(app.status))}>
                        {app.status}
                      </span>
                    </td>
                  </tr>
                )) : (
                  <tr><td colSpan={6} className="px-6 py-12 text-center">
                    <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">{search ? 'No matches' : 'No applications yet'}</p>
                  </td></tr>
                )}
              </tbody>
            </table>
            <div className="p-5 border-t border-slate-100 bg-slate-50/30">
              <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Showing {filtered.length} of {applications.length}</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
