import React from 'react';
import { 
  ShieldCheck, 
  AlertCircle, 
  CheckCircle2, 
  Clock, 
  Search, 
  Filter, 
  FileText,
  TrendingUp,
  Zap
} from 'lucide-react';
import { cn } from '../../lib/utils';

export function AdminCreditOps() {
  const cases = [
    { id: 1, client: 'Robert Fox', bureau: 'Experian', score: 642, target: 720, items: 4, status: 'In Progress' },
    { id: 2, client: 'Marcus Chen', bureau: 'TransUnion', score: 580, target: 680, items: 7, status: 'Review Needed' },
    { id: 3, client: 'Elena Rodriguez', bureau: 'Equifax', score: 710, target: 750, items: 2, status: 'Completed' },
    { id: 4, client: 'Sarah Jenkins', bureau: 'Experian', score: 615, target: 700, items: 5, status: 'In Progress' },
  ];

  return (
    <div className="p-8 space-y-8 bg-slate-50/50 min-h-full text-slate-600">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-black text-[#1A2244] tracking-tight">Credit Ops</h1>
          <p className="text-slate-500 font-medium mt-1 text-sm">Manage credit repair cases, dispute letters, and bureau integrations.</p>
        </div>
        <div className="flex items-center gap-3">
          <button className="px-6 py-2 rounded-xl bg-white border border-slate-200 text-[#1A2244] text-xs font-black uppercase tracking-widest hover:bg-slate-50 transition-all shadow-sm">
            Dispute Templates
          </button>
          <button className="px-6 py-2 rounded-xl bg-[#5B7CFA] text-white text-xs font-black uppercase tracking-widest shadow-lg shadow-blue-500/20 hover:bg-[#4A6BEB] transition-all flex items-center gap-2">
            <Zap className="w-4 h-4" />
            New Case
          </button>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {[
          { label: 'Active Cases', value: '142', icon: ShieldCheck, color: 'blue' },
          { label: 'Avg Score Increase', value: '+42 pts', icon: TrendingUp, color: 'green' },
          { label: 'Pending Disputes', value: '28', icon: Clock, color: 'amber' },
          { label: 'Success Rate', value: '84%', icon: CheckCircle2, color: 'purple' },
        ].map((stat, i) => (
          <div key={i} className="bg-white border border-slate-200 p-6 rounded-3xl shadow-sm">
            <div className="flex items-center gap-4">
              <div className={cn(
                "w-12 h-12 rounded-2xl flex items-center justify-center",
                stat.color === 'blue' ? "bg-blue-50 text-[#5B7CFA]" :
                stat.color === 'green' ? "bg-green-50 text-green-600" :
                stat.color === 'purple' ? "bg-purple-50 text-purple-600" :
                "bg-amber-50 text-amber-600"
              )}>
                <stat.icon className="w-6 h-6" />
              </div>
              <div>
                <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">{stat.label}</p>
                <h3 className="text-xl font-black text-[#1A2244] mt-0.5">{stat.value}</h3>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Cases Table */}
      <div className="bg-white border border-slate-200 rounded-3xl overflow-hidden shadow-sm">
        <div className="p-6 border-b border-slate-100 flex items-center justify-between bg-slate-50/30">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-blue-50 flex items-center justify-center text-[#5B7CFA]">
              <FileText className="w-4 h-4" />
            </div>
            <h3 className="text-sm font-black text-[#1A2244] uppercase tracking-widest">Active Cases</h3>
          </div>
          <div className="flex items-center gap-4">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400" />
              <input 
                type="text" 
                placeholder="Search cases..." 
                className="bg-slate-50 border border-slate-200 rounded-xl py-1.5 pl-9 pr-4 text-[10px] font-bold text-slate-600 focus:outline-none focus:border-[#5B7CFA]/50 w-48"
              />
            </div>
            <button className="p-2 text-slate-400 hover:text-[#1A2244] transition-colors">
              <Filter className="w-5 h-5" />
            </button>
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-50">
                <th className="px-6 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest">Client</th>
                <th className="px-6 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest">Bureau</th>
                <th className="px-6 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest">Current Score</th>
                <th className="px-6 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest">Target</th>
                <th className="px-6 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest">Items</th>
                <th className="px-6 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest">Status</th>
                <th className="px-6 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50">
              {cases.map((c) => (
                <tr key={c.id} className="hover:bg-slate-50/50 transition-colors group">
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-lg bg-slate-100 overflow-hidden">
                        <img src={`https://api.dicebear.com/7.x/avataaars/svg?seed=${c.client}`} alt="" />
                      </div>
                      <span className="text-xs font-bold text-[#1A2244]">{c.client}</span>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <span className="text-[10px] font-black text-slate-500 uppercase tracking-widest">{c.bureau}</span>
                  </td>
                  <td className="px-6 py-4">
                    <span className="text-xs font-black text-[#1A2244]">{c.score}</span>
                  </td>
                  <td className="px-6 py-4">
                    <span className="text-xs font-black text-slate-400">{c.target}</span>
                  </td>
                  <td className="px-6 py-4">
                    <span className="text-xs font-black text-[#5B7CFA]">{c.items}</span>
                  </td>
                  <td className="px-6 py-4">
                    <span className={cn(
                      "px-2 py-1 rounded-lg text-[9px] font-black uppercase tracking-widest",
                      c.status === 'Completed' ? "bg-green-50 text-green-600" :
                      c.status === 'Review Needed' ? "bg-amber-50 text-amber-600" :
                      "bg-blue-50 text-[#5B7CFA]"
                    )}>
                      {c.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-right">
                    <button className="text-[10px] font-black text-[#5B7CFA] uppercase tracking-widest hover:text-[#4A6BEB] transition-colors">
                      View Details
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
