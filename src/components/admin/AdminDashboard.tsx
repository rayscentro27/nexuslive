import React from 'react';
import { 
  Users, 
  DollarSign, 
  Cpu, 
  ShieldAlert, 
  ArrowUpRight, 
  ArrowDownRight,
  Clock,
  CheckCircle2,
  AlertCircle,
  TrendingUp,
  Zap,
  MoreHorizontal,
  Search,
  Lightbulb,
  Building2,
  ChevronRight
} from 'lucide-react';
import { cn } from '../../lib/utils';

export function AdminDashboard() {
  const stats = [
    { label: 'Active Clients', value: '1,284', change: '+12%', trend: 'up', icon: Users, color: 'blue' },
    { label: 'Pipeline Value', value: '$4.2M', change: '+$840k', trend: 'up', icon: DollarSign, color: 'green' },
    { label: 'AI Health', value: '98.2%', change: '+0.4%', trend: 'up', icon: Cpu, color: 'purple' },
    { label: 'System Alerts', value: '3', change: '-2', trend: 'down', icon: ShieldAlert, color: 'amber' },
  ];

  const opportunities = [
    { title: 'SBA 7(a) Expansion', type: 'Funding', impact: 'High', icon: Zap },
    { title: 'Tech Growth Grant', type: 'Grant', impact: 'Medium', icon: Lightbulb },
    { title: 'Strategic Partner Sync', type: 'Partnership', impact: 'High', icon: Users },
  ];

  return (
    <div className="p-8 space-y-8 bg-slate-50/50 min-h-full text-slate-600">
      {/* Header Info */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-black text-[#1A2244] tracking-tight">Overview</h1>
          <p className="text-slate-500 font-medium mt-1 text-sm">Operational workspace and system-wide performance monitoring.</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="px-4 py-2 rounded-xl bg-white border border-slate-200 flex items-center gap-2 shadow-sm">
            <Clock className="w-4 h-4 text-slate-400" />
            <span className="text-xs font-bold text-slate-500">Last Sync: 2m ago</span>
          </div>
          <button className="px-6 py-2 rounded-xl bg-[#5B7CFA] text-white text-xs font-black uppercase tracking-widest shadow-lg shadow-blue-500/20 hover:bg-[#4A6BEB] transition-all">
            System Report
          </button>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {stats.map((stat, i) => (
          <div key={i} className="bg-white border border-slate-200 p-6 rounded-3xl relative overflow-hidden group hover:border-[#5B7CFA]/30 transition-all shadow-sm">
            <div className="absolute top-0 right-0 w-32 h-32 bg-[#5B7CFA]/5 rounded-full -mr-16 -mt-16 blur-3xl group-hover:bg-[#5B7CFA]/10 transition-all" />
            <div className="relative z-10 flex flex-col gap-4">
              <div className="flex items-center justify-between">
                <div className={cn(
                  "w-12 h-12 rounded-2xl flex items-center justify-center shadow-sm",
                  stat.color === 'blue' ? "bg-blue-50 text-[#5B7CFA]" :
                  stat.color === 'green' ? "bg-green-50 text-green-600" :
                  stat.color === 'purple' ? "bg-purple-50 text-purple-600" :
                  "bg-amber-50 text-amber-600"
                )}>
                  <stat.icon className="w-6 h-6" />
                </div>
                <div className={cn(
                  "flex items-center gap-1 px-2 py-1 rounded-lg text-[10px] font-black uppercase tracking-widest",
                  stat.trend === 'up' ? "bg-green-50 text-green-600" : "bg-red-50 text-red-600"
                )}>
                  {stat.trend === 'up' ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />}
                  {stat.change}
                </div>
              </div>
              <div>
                <p className="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em]">{stat.label}</p>
                <h3 className="text-2xl font-black text-[#1A2244] mt-1">{stat.value}</h3>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Funding Pipeline & My Business */}
        <div className="lg:col-span-8 space-y-8">
          {/* My Business Readiness (Admin Personal) */}
          <div className="bg-white border border-slate-200 rounded-3xl p-6 shadow-sm relative overflow-hidden group">
            <div className="absolute top-0 right-0 w-64 h-64 bg-gradient-to-br from-[#5B7CFA]/5 to-transparent rounded-full -mr-32 -mt-32 blur-3xl" />
            <div className="relative z-10 flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="w-14 h-14 rounded-2xl bg-[#5B7CFA]/10 flex items-center justify-center text-[#5B7CFA] shadow-inner">
                  <Building2 className="w-8 h-8" />
                </div>
                <div>
                  <h3 className="text-lg font-black text-[#1A2244] leading-none">My Business Readiness</h3>
                  <p className="text-xs font-medium text-slate-500 mt-1.5">Personal business funding eligibility tracking.</p>
                </div>
              </div>
              <div className="text-right">
                <p className="text-3xl font-black text-[#1A2244]">82%</p>
                <p className="text-[10px] font-black text-green-600 uppercase tracking-widest mt-1">Fundable</p>
              </div>
            </div>
            <div className="mt-6 space-y-2">
              <div className="h-3 bg-slate-100 rounded-full overflow-hidden p-0.5">
                <div className="h-full bg-gradient-to-r from-[#5B7CFA] to-[#4A6BEB] rounded-full shadow-[0_0_8px_rgba(91,124,250,0.4)] w-[82%]" />
              </div>
              <div className="flex justify-between text-[10px] font-black text-slate-400 uppercase tracking-widest">
                <span>Current Readiness</span>
                <span>Target: 90%</span>
              </div>
            </div>
          </div>

          {/* Funding Pipeline */}
          <div className="bg-white border border-slate-200 rounded-3xl overflow-hidden shadow-sm">
            <div className="p-6 border-b border-slate-100 flex items-center justify-between bg-slate-50/30">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-blue-50 flex items-center justify-center text-[#5B7CFA]">
                  <TrendingUp className="w-4 h-4" />
                </div>
                <h3 className="text-sm font-black text-[#1A2244] uppercase tracking-widest">Funding Pipeline</h3>
              </div>
              <button className="text-[10px] font-black text-[#5B7CFA] uppercase tracking-widest hover:text-[#4A6BEB] transition-colors">
                View All
              </button>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-slate-50">
                    <th className="px-6 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest">Client</th>
                    <th className="px-6 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest">Stage</th>
                    <th className="px-6 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest">Amount</th>
                    <th className="px-6 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-50">
                  {[
                    { name: 'Marcus Chen', stage: 'Credit Repair', amount: '$45,000' },
                    { name: 'Sarah Jenkins', stage: 'Entity Setup', amount: '$12,500' },
                    { name: 'Robert Fox', stage: 'Funding Prep', amount: '$85,000' },
                    { name: 'Elena Rodriguez', stage: 'Bank Setup', amount: '$25,000' },
                  ].map((client, i) => (
                    <tr key={i} className="hover:bg-slate-50/50 transition-colors group">
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 rounded-lg bg-slate-100 overflow-hidden">
                            <img src={`https://api.dicebear.com/7.x/avataaars/svg?seed=${client.name}`} alt="" />
                          </div>
                          <span className="text-xs font-bold text-[#1A2244]">{client.name}</span>
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <span className="text-[10px] font-black text-slate-500 uppercase tracking-widest">{client.stage}</span>
                      </td>
                      <td className="px-6 py-4">
                        <span className="text-xs font-black text-[#5B7CFA]">{client.amount}</span>
                      </td>
                      <td className="px-6 py-4 text-right">
                        <button className="p-2 text-slate-400 hover:text-[#5B7CFA] transition-colors">
                          <ChevronRight className="w-4 h-4" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Sidebar: AI Health & Opportunities */}
        <div className="lg:col-span-4 space-y-8">
          {/* AI Workforce Health */}
          <div className="bg-white border border-slate-200 rounded-3xl p-6 shadow-sm space-y-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-purple-50 flex items-center justify-center text-purple-600">
                  <Cpu className="w-4 h-4" />
                </div>
                <h3 className="text-sm font-black text-[#1A2244] uppercase tracking-widest">AI Workforce</h3>
              </div>
              <span className="text-[10px] font-black text-green-600 uppercase tracking-widest">Optimal</span>
            </div>

            <div className="space-y-4">
              {[
                { name: 'Credit AI', status: 'Active', load: 78 },
                { name: 'Funding AI', status: 'Standby', load: 12 },
                { name: 'Setup AI', status: 'Processing', load: 45 },
              ].map((ai, i) => (
                <div key={i} className="space-y-2">
                  <div className="flex justify-between text-[10px] font-black text-slate-500 uppercase tracking-widest">
                    <span>{ai.name}</span>
                    <span>{ai.load}%</span>
                  </div>
                  <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
                    <div className="h-full bg-purple-500 rounded-full" style={{ width: `${ai.load}%` }} />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Business Opportunities */}
          <div className="bg-white border border-slate-200 rounded-3xl p-6 shadow-sm space-y-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-amber-50 flex items-center justify-center text-amber-600">
                  <Lightbulb className="w-4 h-4" />
                </div>
                <h3 className="text-sm font-black text-[#1A2244] uppercase tracking-widest">Opportunities</h3>
              </div>
              <span className="text-[10px] font-black text-amber-600 uppercase tracking-widest">8 New</span>
            </div>

            <div className="space-y-3">
              {opportunities.map((opp, i) => (
                <div key={i} className="flex items-center gap-3 p-3 rounded-2xl bg-slate-50 border border-slate-100 group cursor-pointer hover:border-[#5B7CFA]/30 transition-all">
                  <div className="w-10 h-10 rounded-xl bg-white flex items-center justify-center text-[#5B7CFA] shadow-sm group-hover:scale-110 transition-transform">
                    <opp.icon className="w-5 h-5" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-[11px] font-black text-[#1A2244] truncate">{opp.title}</p>
                    <p className="text-[9px] font-bold text-slate-400 uppercase tracking-widest mt-0.5">{opp.type} • {opp.impact} Impact</p>
                  </div>
                  <ChevronRight className="w-4 h-4 text-slate-300 group-hover:text-[#5B7CFA] transition-colors" />
                </div>
              ))}
            </div>
            <button className="w-full py-3 rounded-xl bg-slate-50 text-[#1A2244] text-[10px] font-black uppercase tracking-widest hover:bg-slate-100 transition-all border border-slate-200">
              View All Opportunities
            </button>
          </div>

          {/* Pending Reviews / Alerts */}
          <div className="bg-white border border-slate-200 rounded-3xl p-6 shadow-sm space-y-6">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-red-50 flex items-center justify-center text-red-600">
                <AlertCircle className="w-4 h-4" />
              </div>
              <h3 className="text-sm font-black text-[#1A2244] uppercase tracking-widest">Pending Reviews</h3>
            </div>
            <div className="space-y-3">
              <div className="p-3 rounded-xl bg-red-50/50 border border-red-100">
                <p className="text-[10px] font-black text-red-600 uppercase tracking-widest">Urgent</p>
                <p className="text-xs font-bold text-[#1A2244] mt-1">Review Articles of Inc. - Marcus Chen</p>
              </div>
              <div className="p-3 rounded-xl bg-amber-50/50 border border-amber-100">
                <p className="text-[10px] font-black text-amber-600 uppercase tracking-widest">Medium</p>
                <p className="text-xs font-bold text-[#1A2244] mt-1">Verify ID Documents - Sarah Jenkins</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function ArrowRight(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg
      {...props}
      xmlns="http://www.w3.org/2000/svg"
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M5 12h14" />
      <path d="m12 5 7 7-7 7" />
    </svg>
  );
}
