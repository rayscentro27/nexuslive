import React from 'react';
import { 
  BarChart3, 
  TrendingUp, 
  PieChart, 
  Download, 
  Calendar, 
  Filter, 
  Search,
  ArrowUpRight,
  ArrowDownRight,
  Activity,
  Users,
  DollarSign
} from 'lucide-react';
import { cn } from '../../lib/utils';

export function AdminReports() {
  const reports = [
    { id: 1, name: 'Monthly Revenue Report', category: 'Financial', date: '2024-03-01', format: 'PDF' },
    { id: 2, name: 'Client Growth Analytics', category: 'Growth', date: '2024-02-28', format: 'XLSX' },
    { id: 3, name: 'AI Performance Metrics', category: 'Operations', date: '2024-02-25', format: 'PDF' },
    { id: 4, name: 'Funding Pipeline Forecast', category: 'Funding', date: '2024-02-20', format: 'PDF' },
  ];

  return (
    <div className="p-8 space-y-8 bg-slate-50/50 min-h-full text-slate-600">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-black text-[#1A2244] tracking-tight">Reports & Analytics</h1>
          <p className="text-slate-500 font-medium mt-1 text-sm">Comprehensive data insights across all platform operations.</p>
        </div>
        <div className="flex items-center gap-3">
          <button className="px-6 py-2 rounded-xl bg-white border border-slate-200 text-[#1A2244] text-xs font-black uppercase tracking-widest hover:bg-slate-50 transition-all shadow-sm">
            Schedule Report
          </button>
          <button className="px-6 py-2 rounded-xl bg-[#5B7CFA] text-white text-xs font-black uppercase tracking-widest shadow-lg shadow-blue-500/20 hover:bg-[#4A6BEB] transition-all flex items-center gap-2">
            <Download className="w-4 h-4" />
            Export Data
          </button>
        </div>
      </div>

      {/* Key Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
        {[
          { label: 'Revenue Growth', value: '$1.2M', change: '+15.4%', trend: 'up', icon: DollarSign, color: 'blue' },
          { label: 'Active Users', value: '2,842', change: '+8.2%', trend: 'up', icon: Users, color: 'green' },
          { label: 'System Efficiency', value: '94.2%', change: '-1.2%', trend: 'down', icon: Activity, color: 'purple' },
        ].map((stat, i) => (
          <div key={i} className="bg-white border border-slate-200 p-8 rounded-3xl shadow-sm relative overflow-hidden group">
            <div className="absolute top-0 right-0 w-32 h-32 bg-gradient-to-br from-slate-50 to-transparent rounded-full -mr-16 -mt-16 transition-all group-hover:scale-110" />
            <div className="relative z-10">
              <div className="flex items-center justify-between mb-4">
                <div className={cn(
                  "w-12 h-12 rounded-2xl flex items-center justify-center shadow-sm",
                  stat.color === 'blue' ? "bg-blue-50 text-[#5B7CFA]" :
                  stat.color === 'green' ? "bg-green-50 text-green-600" :
                  "bg-purple-50 text-purple-600"
                )}>
                  <stat.icon className="w-6 h-6" />
                </div>
                <div className={cn(
                  "flex items-center gap-1 text-[10px] font-black uppercase tracking-widest",
                  stat.trend === 'up' ? "text-green-600" : "text-red-600"
                )}>
                  {stat.trend === 'up' ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />}
                  {stat.change}
                </div>
              </div>
              <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">{stat.label}</p>
              <h3 className="text-3xl font-black text-[#1A2244] mt-1">{stat.value}</h3>
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Analytics Chart Placeholder */}
        <div className="lg:col-span-8 bg-white border border-slate-200 rounded-3xl p-8 shadow-sm">
          <div className="flex items-center justify-between mb-8">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-blue-50 flex items-center justify-center text-[#5B7CFA]">
                <BarChart3 className="w-4 h-4" />
              </div>
              <h3 className="text-sm font-black text-[#1A2244] uppercase tracking-widest">Performance Trends</h3>
            </div>
            <div className="flex items-center gap-2">
              <button className="px-3 py-1.5 rounded-lg bg-slate-50 border border-slate-100 text-[10px] font-black text-[#5B7CFA] uppercase tracking-widest">7 Days</button>
              <button className="px-3 py-1.5 rounded-lg bg-white border border-slate-200 text-[10px] font-black text-slate-400 uppercase tracking-widest">30 Days</button>
              <button className="px-3 py-1.5 rounded-lg bg-white border border-slate-200 text-[10px] font-black text-slate-400 uppercase tracking-widest">90 Days</button>
            </div>
          </div>
          <div className="h-64 bg-slate-50 rounded-2xl border border-slate-100 flex items-center justify-center relative overflow-hidden shadow-inner">
            <div className="absolute inset-0 opacity-20">
              <div className="w-full h-full" style={{ backgroundImage: 'radial-gradient(circle, #5B7CFA 1px, transparent 1px)', backgroundSize: '30px 30px' }} />
            </div>
            <TrendingUp className="w-12 h-12 text-[#5B7CFA]/20" />
            <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest absolute bottom-4">Interactive Analytics Visualization</p>
          </div>
        </div>

        {/* Recent Reports */}
        <div className="lg:col-span-4 bg-white border border-slate-200 rounded-3xl overflow-hidden shadow-sm">
          <div className="p-6 border-b border-slate-100 flex items-center justify-between bg-slate-50/30">
            <h3 className="text-sm font-black text-[#1A2244] uppercase tracking-widest">Recent Reports</h3>
            <button className="text-[10px] font-black text-[#5B7CFA] uppercase tracking-widest">View All</button>
          </div>
          <div className="divide-y divide-slate-50">
            {reports.map((report) => (
              <div key={report.id} className="p-4 hover:bg-slate-50/50 transition-all group">
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-3">
                    <div className="w-8 h-8 rounded-lg bg-slate-100 flex items-center justify-center text-slate-400 group-hover:text-[#5B7CFA] transition-colors">
                      <PieChart className="w-4 h-4" />
                    </div>
                    <div>
                      <h4 className="text-xs font-bold text-[#1A2244]">{report.name}</h4>
                      <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest mt-1">{report.category} • {report.date}</p>
                    </div>
                  </div>
                  <button className="p-2 text-slate-300 hover:text-[#5B7CFA] transition-colors">
                    <Download className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
