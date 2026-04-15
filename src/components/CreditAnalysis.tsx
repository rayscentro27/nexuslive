import React from 'react';
import { Shield, TrendingUp, AlertCircle, FileText, Upload, Download, ArrowRight, CheckCircle2, XCircle, Clock } from 'lucide-react';
import { cn } from '../lib/utils';

export function CreditAnalysis() {
  const score = 742;
  const fundingRange = "$13,000 – $75,000";

  return (
    <div className="p-4 max-w-6xl mx-auto space-y-4 h-full flex flex-col overflow-y-auto no-scrollbar">
      <div className="flex flex-col space-y-1 shrink-0">
        <h1 className="text-xl font-black text-[#1A2244]">Credit Analysis</h1>
        <div className="flex items-center gap-3">
          <span className="px-2 py-0.5 bg-green-50 text-green-600 text-[10px] font-black uppercase rounded-md flex items-center gap-1.5">
            <CheckCircle2 className="w-3 h-3" />
            Good
          </span>
          <p className="text-[10px] text-slate-500 font-bold uppercase tracking-widest">Funding Readiness: High</p>
        </div>
      </div>

      <div className="flex-1 space-y-4">
        {/* Main Stats Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* Funding Range Card */}
          <div className="lg:col-span-2 glass-card p-5 bg-gradient-to-br from-white to-blue-50/30">
            <div className="flex items-center justify-between mb-4">
              <div className="space-y-1">
                <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Estimated Funding Range</p>
                <h2 className="text-2xl font-black text-[#1A2244]">{fundingRange}</h2>
                <p className="text-[10px] text-slate-400 font-medium">Approval odds based on readiness</p>
              </div>
              <div className="text-right">
                <p className="text-[8px] font-black text-slate-400 uppercase tracking-widest">Last Updated</p>
                <p className="text-[10px] font-bold text-slate-600">2 hours ago</p>
              </div>
            </div>
            
            <div className="flex flex-wrap gap-2">
              <button className="bg-[#5B7CFA] text-white px-4 py-2 rounded-xl text-[10px] font-black uppercase tracking-widest shadow-lg shadow-blue-500/20 hover:bg-[#4A6BEB] transition-all flex items-center gap-2">
                Generate Dispute Letters
                <ArrowRight className="w-3 h-3" />
              </button>
              <button className="bg-white border border-slate-100 text-[#1A2244] px-4 py-2 rounded-xl text-[10px] font-black uppercase tracking-widest hover:bg-slate-50 transition-all flex items-center gap-2">
                <Download className="w-3 h-3" />
                Download
              </button>
            </div>
          </div>

          {/* Score Card */}
          <div className="glass-card p-4 flex flex-col items-center justify-center text-center space-y-2">
            <div className="relative w-20 h-20 flex items-center justify-center">
              <svg className="w-full h-full transform -rotate-90">
                <circle
                  cx="40"
                  cy="40"
                  r="36"
                  stroke="currentColor"
                  strokeWidth="5"
                  fill="transparent"
                  className="text-slate-100"
                />
                <circle
                  cx="40"
                  cy="40"
                  r="36"
                  stroke="currentColor"
                  strokeWidth="5"
                  fill="transparent"
                  strokeDasharray={226}
                  strokeDashoffset={226 - (226 * score) / 850}
                  className="text-[#5B7CFA]"
                />
              </svg>
              <div className="absolute inset-0 flex flex-col items-center justify-center">
                <span className="text-xl font-black text-[#1A2244]">{score}</span>
                <span className="text-[7px] font-black text-slate-400 uppercase">Experian</span>
              </div>
            </div>
            <div className="space-y-0.5">
              <h3 className="text-[11px] font-black text-[#1A2244]">Score Band: Good</h3>
              <p className="text-[9px] text-green-600 font-bold">+12 points</p>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Negative Items */}
          <div className="glass-card p-5 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="p-1.5 bg-red-50 text-red-600 rounded-lg">
                  <AlertCircle className="w-4 h-4" />
                </div>
                <h3 className="text-sm font-bold text-slate-900">Negative Items</h3>
              </div>
              <span className="text-xl font-black text-red-600">3</span>
            </div>
            <p className="text-xs text-slate-500">Opportunities to dispute derogatory marks</p>
            <ul className="space-y-1.5">
              <li className="flex items-center gap-2 text-xs text-slate-600">
                <div className="w-1 h-1 bg-red-400 rounded-full" />
                Late payments, collections, or inquiries
              </li>
              <li className="flex items-center gap-2 text-xs text-slate-600">
                <div className="w-1 h-1 bg-red-400 rounded-full" />
                Late payments, inquiries
              </li>
            </ul>
            <button className="w-full py-2 bg-slate-50 text-slate-600 text-xs font-bold rounded-xl hover:bg-slate-100 transition-all flex items-center justify-center gap-2">
              View Disputes
              <ArrowRight className="w-3 h-3" />
            </button>
          </div>

          {/* Usage */}
          <div className="glass-card p-5 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="p-1.5 bg-amber-50 text-amber-600 rounded-lg">
                  <TrendingUp className="w-4 h-4" />
                </div>
                <h3 className="text-sm font-bold text-slate-900">Usage</h3>
              </div>
              <span className="text-xl font-black text-amber-600">37%</span>
            </div>
            <p className="text-xs text-slate-500">Utilization across all accounts</p>
            <div className="space-y-1.5">
              <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
                <div className="h-full bg-amber-500" style={{ width: '37%' }} />
              </div>
              <div className="flex justify-between text-[10px] font-bold text-slate-400 uppercase">
                <span>Total Debt</span>
                <span className="text-slate-600">$34,000</span>
              </div>
            </div>
            <button className="w-full py-2 bg-slate-50 text-slate-600 text-xs font-bold rounded-xl hover:bg-slate-100 transition-all flex items-center justify-center gap-2">
              View Utilization
              <ArrowRight className="w-3 h-3" />
            </button>
          </div>
        </div>

        {/* History & Upload */}
        <div className="space-y-3">
          <div className="flex items-center justify-between px-2">
            <h2 className="text-lg font-bold text-slate-900">History & Upload</h2>
            <button className="text-xs font-bold text-nexus-600 hover:text-nexus-700 flex items-center gap-1">
              View All <ArrowRight className="w-3 h-3" />
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="glass-card p-6 border-dashed border-2 flex flex-col items-center justify-center text-center space-y-3 hover:bg-slate-50/50 transition-all cursor-pointer">
              <div className="w-10 h-10 bg-nexus-50 text-nexus-600 rounded-full flex items-center justify-center">
                <Upload className="w-5 h-5" />
              </div>
              <div className="space-y-0.5">
                <h3 className="text-sm font-bold text-slate-900">Upload New Report</h3>
                <p className="text-[10px] text-slate-500">Supported: PDF, JPG, PNG</p>
              </div>
            </div>

            <div className="glass-card p-5 flex flex-col justify-between">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-blue-50 text-blue-600 rounded-xl">
                    <FileText className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-slate-900">Experian-Report.pdf</h3>
                    <p className="text-[10px] text-slate-500">1.3 MB • Mar 22</p>
                  </div>
                </div>
                <button className="p-1.5 hover:bg-slate-100 rounded-lg text-slate-400">
                  <ArrowRight className="w-4 h-4" />
                </button>
              </div>
              <div className="mt-4 flex gap-2">
                <button className="flex-1 py-1.5 bg-slate-50 text-slate-600 text-[10px] font-bold rounded-lg hover:bg-slate-100">View</button>
                <button className="flex-1 py-1.5 bg-slate-50 text-slate-600 text-[10px] font-bold rounded-lg hover:bg-slate-100">Download</button>
              </div>
            </div>
          </div>
        </div>

        {/* Dispute Assistant */}
        <div className="glass-card overflow-hidden">
          <div className="p-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/30">
            <div className="flex items-center gap-2">
              <div className="p-1.5 bg-nexus-50 text-nexus-600 rounded-lg">
                <Shield className="w-4 h-4" />
              </div>
              <h2 className="text-base font-bold text-slate-900">Dispute Assistant</h2>
            </div>
            <span className="text-xs font-bold text-nexus-600">5 Opportunities</span>
          </div>
          <div className="divide-y divide-slate-100">
            {[
              { bank: 'Barclays Bank CC', reason: '180 Days Late ($437)', status: 'In Review' },
              { bank: 'Chase Freedom', reason: 'Incorrect Balance ($1,200)', status: 'Pending' },
            ].map((item, i) => (
              <div key={i} className="p-4 flex items-center justify-between hover:bg-slate-50/50 transition-all">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 bg-slate-100 rounded-full flex items-center justify-center text-slate-400">
                    <FileText className="w-4 h-4" />
                  </div>
                  <div>
                    <h4 className="text-sm font-bold text-slate-900">{item.bank}</h4>
                    <p className="text-xs text-slate-500">{item.reason}</p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <span className={cn(
                    "px-2 py-0.5 rounded-full text-[8px] font-bold uppercase tracking-wider",
                    item.status === 'In Review' ? "bg-blue-50 text-blue-600" : "bg-amber-50 text-amber-600"
                  )}>
                    {item.status}
                  </span>
                  <button className="p-1.5 text-slate-300 hover:text-slate-600">
                    <ArrowRight className="w-4 h-4" />
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
