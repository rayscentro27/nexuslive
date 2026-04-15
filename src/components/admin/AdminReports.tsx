import React, { useEffect, useState } from 'react';
import { BarChart3, TrendingUp, PieChart, Download, ArrowUpRight, Activity, Users, DollarSign, Loader2, FileText } from 'lucide-react';
import { cn } from '../../lib/utils';
import { getAllClients, getAllDocuments, getAllFundingApplications } from '../../lib/db';

export function AdminReports() {
  const [clientCount, setClientCount] = useState(0);
  const [docCount, setDocCount] = useState(0);
  const [pipeline, setPipeline] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([getAllClients(), getAllDocuments(), getAllFundingApplications()]).then(
      ([{ data: c }, { data: d }, { data: a }]) => {
        setClientCount(c.length);
        setDocCount(d.length);
        setPipeline(a.reduce((s, app) => s + (app.requested_amount ?? 0), 0));
        setLoading(false);
      }
    );
  }, []);

  const fmtMoney = (n: number) => {
    if (n >= 1_000_000) return '$' + (n / 1_000_000).toFixed(1) + 'M';
    if (n >= 1_000) return '$' + (n / 1_000).toFixed(0) + 'k';
    return '$' + n;
  };

  const stats = [
    { label: 'Total Clients', value: loading ? '—' : String(clientCount), icon: Users, color: 'blue' },
    { label: 'Pipeline Value', value: loading ? '—' : fmtMoney(pipeline), icon: DollarSign, color: 'green' },
    { label: 'Documents', value: loading ? '—' : String(docCount), icon: FileText, color: 'purple' },
  ];

  const reports = [
    { id: 1, name: 'Client Growth Report', category: 'Growth', format: 'PDF' },
    { id: 2, name: 'Funding Pipeline Report', category: 'Funding', format: 'XLSX' },
    { id: 3, name: 'Document Status Report', category: 'Operations', format: 'PDF' },
    { id: 4, name: 'AI Performance Report', category: 'Operations', format: 'PDF' },
  ];

  return (
    <div className="p-8 space-y-8 bg-slate-50/50 min-h-full text-slate-600">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-black text-[#1A2244] tracking-tight">Reports & Analytics</h1>
          <p className="text-slate-500 font-medium mt-1 text-sm">Comprehensive data insights across all platform operations.</p>
        </div>
        <button className="px-6 py-2 rounded-xl bg-[#5B7CFA] text-white text-xs font-black uppercase tracking-widest shadow-lg shadow-blue-500/20 hover:bg-[#4A6BEB] transition-all flex items-center gap-2">
          <Download className="w-4 h-4" /> Export Data
        </button>
      </div>

      {/* Live Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
        {stats.map((stat, i) => (
          <div key={i} className="bg-white border border-slate-200 p-8 rounded-3xl shadow-sm relative overflow-hidden group">
            <div className="absolute top-0 right-0 w-32 h-32 bg-gradient-to-br from-slate-50 to-transparent rounded-full -mr-16 -mt-16" />
            <div className="relative z-10">
              <div className="flex items-center justify-between mb-4">
                <div className={cn("w-12 h-12 rounded-2xl flex items-center justify-center shadow-sm",
                  stat.color === 'blue' ? "bg-blue-50 text-[#5B7CFA]" :
                  stat.color === 'green' ? "bg-green-50 text-green-600" :
                  "bg-purple-50 text-purple-600")}>
                  <stat.icon className="w-6 h-6" />
                </div>
                <ArrowUpRight className="w-4 h-4 text-slate-200" />
              </div>
              <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">{stat.label}</p>
              <h3 className="text-3xl font-black text-[#1A2244] mt-1">{stat.value}</h3>
              <p className="text-[10px] text-slate-400 mt-1">Live from database</p>
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Chart Placeholder */}
        <div className="lg:col-span-8 bg-white border border-slate-200 rounded-3xl p-8 shadow-sm">
          <div className="flex items-center justify-between mb-8">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-blue-50 flex items-center justify-center text-[#5B7CFA]">
                <BarChart3 className="w-4 h-4" />
              </div>
              <h3 className="text-sm font-black text-[#1A2244] uppercase tracking-widest">Performance Trends</h3>
            </div>
            <div className="flex items-center gap-2">
              {['7 Days', '30 Days', '90 Days'].map((t, i) => (
                <button key={t} className={cn("px-3 py-1.5 rounded-lg text-[10px] font-black uppercase tracking-widest",
                  i === 0 ? "bg-slate-50 border border-slate-100 text-[#5B7CFA]" : "bg-white border border-slate-200 text-slate-400")}>
                  {t}
                </button>
              ))}
            </div>
          </div>
          <div className="h-64 bg-slate-50 rounded-2xl border border-slate-100 flex flex-col items-center justify-center relative overflow-hidden shadow-inner">
            <div className="absolute inset-0 opacity-20">
              <div className="w-full h-full" style={{ backgroundImage: 'radial-gradient(circle, #5B7CFA 1px, transparent 1px)', backgroundSize: '30px 30px' }} />
            </div>
            <TrendingUp className="w-12 h-12 text-[#5B7CFA]/20" />
            <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mt-2">Charts coming soon</p>
            <p className="text-xs text-slate-300 mt-1">{loading ? 'Loading...' : `${clientCount} clients · ${docCount} docs · ${fmtMoney(pipeline)} pipeline`}</p>
          </div>
        </div>

        {/* Report Templates */}
        <div className="lg:col-span-4 bg-white border border-slate-200 rounded-3xl overflow-hidden shadow-sm">
          <div className="p-6 border-b border-slate-100 flex items-center justify-between bg-slate-50/30">
            <h3 className="text-sm font-black text-[#1A2244] uppercase tracking-widest">Report Templates</h3>
          </div>
          <div className="divide-y divide-slate-50">
            {reports.map(report => (
              <div key={report.id} className="p-4 hover:bg-slate-50/50 transition-all group">
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-3">
                    <div className="w-8 h-8 rounded-lg bg-slate-100 flex items-center justify-center text-slate-400 group-hover:text-[#5B7CFA] transition-colors">
                      <PieChart className="w-4 h-4" />
                    </div>
                    <div>
                      <h4 className="text-xs font-bold text-[#1A2244]">{report.name}</h4>
                      <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest mt-1">
                        {report.category} · {report.format}
                      </p>
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
