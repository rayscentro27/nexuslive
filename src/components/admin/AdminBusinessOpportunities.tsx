import React from 'react';
import { 
  Lightbulb, 
  TrendingUp, 
  Users, 
  DollarSign, 
  Search, 
  Filter, 
  ArrowUpRight,
  Zap,
  Briefcase,
  Target
} from 'lucide-react';
import { cn } from '../../lib/utils';

export function AdminBusinessOpportunities() {
  const opportunities = [
    { id: 1, title: 'E-commerce Expansion', category: 'Growth', potential: '$150k', readiness: 85, status: 'High Priority' },
    { id: 2, title: 'SaaS Integration', category: 'Tech', potential: '$45k', readiness: 60, status: 'Active' },
    { id: 3, title: 'Real Estate Portfolio', category: 'Investment', potential: '$500k', readiness: 40, status: 'Pending' },
    { id: 4, title: 'Logistics Optimization', category: 'Operations', potential: '$85k', readiness: 75, status: 'Active' },
  ];

  return (
    <div className="p-8 space-y-8 bg-slate-50/50 min-h-full text-slate-600">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-black text-[#1A2244] tracking-tight">Business Opportunities</h1>
          <p className="text-slate-500 font-medium mt-1 text-sm">Identify and manage high-potential business ventures for clients.</p>
        </div>
        <div className="flex items-center gap-3">
          <button className="px-6 py-2 rounded-xl bg-white border border-slate-200 text-[#1A2244] text-xs font-black uppercase tracking-widest hover:bg-slate-50 transition-all shadow-sm">
            Market Trends
          </button>
          <button className="px-6 py-2 rounded-xl bg-[#5B7CFA] text-white text-xs font-black uppercase tracking-widest shadow-lg shadow-blue-500/20 hover:bg-[#4A6BEB] transition-all flex items-center gap-2">
            <Zap className="w-4 h-4" />
            Add Opportunity
          </button>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {[
          { label: 'Active Opps', value: '24', icon: Lightbulb, color: 'blue' },
          { label: 'Total Potential', value: '$2.8M', icon: DollarSign, color: 'green' },
          { label: 'Client Matches', value: '156', icon: Users, color: 'purple' },
          { label: 'Conversion Rate', value: '12%', icon: TrendingUp, color: 'amber' },
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

      {/* Opportunities Table */}
      <div className="bg-white border border-slate-200 rounded-3xl overflow-hidden shadow-sm">
        <div className="p-6 border-b border-slate-100 flex items-center justify-between bg-slate-50/30">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-blue-50 flex items-center justify-center text-[#5B7CFA]">
              <Target className="w-4 h-4" />
            </div>
            <h3 className="text-sm font-black text-[#1A2244] uppercase tracking-widest">Market Opportunities</h3>
          </div>
          <div className="flex items-center gap-4">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400" />
              <input 
                type="text" 
                placeholder="Search opportunities..." 
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
                <th className="px-6 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest">Opportunity</th>
                <th className="px-6 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest">Category</th>
                <th className="px-6 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest">Potential</th>
                <th className="px-6 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest">Readiness</th>
                <th className="px-6 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest">Status</th>
                <th className="px-6 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50">
              {opportunities.map((opp) => (
                <tr key={opp.id} className="hover:bg-slate-50/50 transition-colors group">
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-lg bg-slate-100 flex items-center justify-center text-[#1A2244]">
                        <Briefcase className="w-4 h-4" />
                      </div>
                      <span className="text-xs font-bold text-[#1A2244]">{opp.title}</span>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <span className="text-[10px] font-black text-slate-500 uppercase tracking-widest">{opp.category}</span>
                  </td>
                  <td className="px-6 py-4">
                    <span className="text-xs font-black text-green-600">{opp.potential}</span>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      <div className="flex-1 h-1.5 bg-slate-100 rounded-full overflow-hidden w-20">
                        <div className="h-full bg-[#5B7CFA] rounded-full" style={{ width: `${opp.readiness}%` }} />
                      </div>
                      <span className="text-[10px] font-black text-[#1A2244]">{opp.readiness}%</span>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <span className={cn(
                      "px-2 py-1 rounded-lg text-[9px] font-black uppercase tracking-widest",
                      opp.status === 'High Priority' ? "bg-red-50 text-red-600" :
                      opp.status === 'Pending' ? "bg-amber-50 text-amber-600" :
                      "bg-blue-50 text-[#5B7CFA]"
                    )}>
                      {opp.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-right">
                    <button className="text-[10px] font-black text-[#5B7CFA] uppercase tracking-widest hover:text-[#4A6BEB] transition-colors">
                      Match Clients
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
