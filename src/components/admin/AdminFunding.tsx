import React from 'react';
import { 
  BarChart3, 
  TrendingUp, 
  DollarSign, 
  ArrowUpRight, 
  Clock, 
  CheckCircle2, 
  AlertCircle,
  Search,
  Filter,
  MoreHorizontal,
  Briefcase,
  Zap
} from 'lucide-react';
import { cn } from '../../lib/utils';

export function AdminFunding() {
  const deals = [
    { id: 1, client: 'Robert Fox', amount: '$85,000', product: 'SBA 7(a)', stage: 'Underwriting', probability: 85, status: 'urgent' },
    { id: 2, client: 'Marcus Chen', amount: '$45,000', product: 'Business Line of Credit', stage: 'Document Review', probability: 60, status: 'active' },
    { id: 3, client: 'Elena Rodriguez', amount: '$25,000', product: 'Equipment Financing', stage: 'Approved', probability: 100, status: 'active' },
    { id: 4, client: 'Sarah Jenkins', amount: '$15,000', product: 'Microloan', stage: 'Initial Application', probability: 30, status: 'pending' },
  ];

  const stats = [
    { label: 'Total Pipeline', value: '$4.2M', icon: DollarSign, color: 'blue' },
    { label: 'Avg Deal Size', value: '$42.5k', icon: TrendingUp, color: 'green' },
    { label: 'Approval Rate', value: '78%', icon: CheckCircle2, color: 'purple' },
    { label: 'Pending Review', value: '14', icon: Clock, color: 'amber' },
  ];

  return (
    <div className="p-8 space-y-8 bg-slate-50/50 min-h-full text-slate-600">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-black text-[#1A2244] tracking-tight">Funding Engine</h1>
          <p className="text-slate-500 font-medium mt-1 text-sm">Monitor client funding stages, review offers, and manage application flow.</p>
        </div>
        <div className="flex items-center gap-3">
          <button className="px-6 py-2 rounded-xl bg-white border border-slate-200 text-[#1A2244] text-xs font-black uppercase tracking-widest hover:bg-slate-50 transition-all shadow-sm">
            Product Manager
          </button>
          <button className="px-6 py-2 rounded-xl bg-[#5B7CFA] text-white text-xs font-black uppercase tracking-widest shadow-lg shadow-blue-500/20 hover:bg-[#4A6BEB] transition-all flex items-center gap-2">
            <Zap className="w-4 h-4" />
            New Deal
          </button>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {stats.map((stat, i) => (
          <div key={i} className="bg-white border border-slate-200 p-6 rounded-3xl shadow-sm group hover:border-[#5B7CFA]/30 transition-all">
            <div className="flex items-center gap-4">
              <div className={cn(
                "w-12 h-12 rounded-2xl flex items-center justify-center shadow-sm",
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

      {/* Active Deals Table */}
      <div className="bg-white border border-slate-200 rounded-3xl overflow-hidden shadow-sm">
        <div className="p-6 border-b border-slate-100 flex items-center justify-between bg-slate-50/30">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-blue-50 flex items-center justify-center text-[#5B7CFA]">
              <Briefcase className="w-4 h-4" />
            </div>
            <h3 className="text-sm font-black text-[#1A2244] uppercase tracking-widest">Active Deals</h3>
          </div>
          <div className="flex items-center gap-4">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400" />
              <input 
                type="text" 
                placeholder="Search deals..." 
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
                <th className="px-6 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest">Product</th>
                <th className="px-6 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest">Amount</th>
                <th className="px-6 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest">Stage</th>
                <th className="px-6 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest">Probability</th>
                <th className="px-6 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50">
              {deals.map((deal) => (
                <tr key={deal.id} className="hover:bg-slate-50/50 transition-colors group">
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-lg bg-slate-100 overflow-hidden">
                        <img src={`https://api.dicebear.com/7.x/avataaars/svg?seed=${deal.client}`} alt="" />
                      </div>
                      <span className="text-xs font-bold text-[#1A2244]">{deal.client}</span>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <span className="text-[10px] font-black text-slate-500 uppercase tracking-widest">{deal.product}</span>
                  </td>
                  <td className="px-6 py-4">
                    <span className="text-xs font-black text-[#5B7CFA]">{deal.amount}</span>
                  </td>
                  <td className="px-6 py-4">
                    <span className={cn(
                      "px-2 py-1 rounded-lg text-[9px] font-black uppercase tracking-widest",
                      deal.stage === 'Approved' ? "bg-green-50 text-green-600" : "bg-blue-50 text-[#5B7CFA]"
                    )}>
                      {deal.stage}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      <div className="flex-1 h-1.5 bg-slate-100 rounded-full overflow-hidden w-20">
                        <div className="h-full bg-[#5B7CFA] rounded-full" style={{ width: `${deal.probability}%` }} />
                      </div>
                      <span className="text-[10px] font-black text-[#1A2244]">{deal.probability}%</span>
                    </div>
                  </td>
                  <td className="px-6 py-4 text-right">
                    <button className="text-[10px] font-black text-[#5B7CFA] uppercase tracking-widest hover:text-[#4A6BEB] transition-colors">
                      Review
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
