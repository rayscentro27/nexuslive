import React from 'react';
import { 
  Building2, 
  TrendingUp, 
  Users, 
  DollarSign, 
  Search, 
  Filter, 
  ArrowUpRight,
  Zap,
  Briefcase,
  Target,
  Settings,
  ShieldCheck,
  Activity
} from 'lucide-react';
import { cn } from '../../lib/utils';

export function AdminMyBusiness() {
  return (
    <div className="p-8 space-y-8 bg-slate-50/50 min-h-full text-slate-600">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-black text-[#1A2244] tracking-tight">My Business</h1>
          <p className="text-slate-500 font-medium mt-1 text-sm">Manage your own business profile, funding readiness, and internal operations.</p>
        </div>
        <div className="flex items-center gap-3">
          <button className="px-6 py-2 rounded-xl bg-white border border-slate-200 text-[#1A2244] text-xs font-black uppercase tracking-widest hover:bg-slate-50 transition-all shadow-sm">
            Company Profile
          </button>
          <button className="px-6 py-2 rounded-xl bg-[#5B7CFA] text-white text-xs font-black uppercase tracking-widest shadow-lg shadow-blue-500/20 hover:bg-[#4A6BEB] transition-all flex items-center gap-2">
            <Settings className="w-4 h-4" />
            Settings
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Readiness Overview */}
        <div className="lg:col-span-8 space-y-8">
          <div className="bg-white border border-slate-200 rounded-3xl p-8 shadow-sm relative overflow-hidden group">
            <div className="absolute top-0 right-0 w-96 h-96 bg-gradient-to-br from-[#5B7CFA]/5 to-transparent rounded-full -mr-48 -mt-48 blur-3xl" />
            <div className="relative z-10">
              <div className="flex items-center justify-between mb-8">
                <div className="flex items-center gap-4">
                  <div className="w-14 h-14 rounded-2xl bg-blue-50 flex items-center justify-center text-[#5B7CFA] shadow-inner">
                    <Activity className="w-8 h-8" />
                  </div>
                  <div>
                    <h3 className="text-lg font-black text-[#1A2244]">Business Readiness</h3>
                    <p className="text-xs font-medium text-slate-500 mt-1">Your internal funding eligibility and operational health.</p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-3xl font-black text-[#5B7CFA]">92%</p>
                  <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mt-1">Overall Score</p>
                </div>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {[
                  { label: 'Entity Structure', score: 100, status: 'Verified' },
                  { label: 'Credit Profile', score: 85, status: 'Optimizing' },
                  { label: 'Financial Health', score: 90, status: 'Strong' },
                ].map((item, i) => (
                  <div key={i} className="p-6 rounded-2xl bg-slate-50 border border-slate-100 space-y-4">
                    <div className="flex justify-between items-center">
                      <span className="text-[10px] font-black text-slate-500 uppercase tracking-widest">{item.label}</span>
                      <span className="text-[10px] font-black text-green-600 uppercase tracking-widest">{item.status}</span>
                    </div>
                    <div className="flex items-baseline gap-2">
                      <h4 className="text-2xl font-black text-[#1A2244]">{item.score}%</h4>
                    </div>
                    <div className="h-1.5 bg-slate-200 rounded-full overflow-hidden">
                      <div className="h-full bg-[#5B7CFA] rounded-full" style={{ width: `${item.score}%` }} />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Internal Operations */}
          <div className="bg-white border border-slate-200 rounded-3xl overflow-hidden shadow-sm">
            <div className="p-6 border-b border-slate-100 flex items-center justify-between bg-slate-50/30">
              <h3 className="text-sm font-black text-[#1A2244] uppercase tracking-widest">Internal Operations</h3>
              <button className="text-[10px] font-black text-[#5B7CFA] uppercase tracking-widest">Manage All</button>
            </div>
            <div className="p-6 grid grid-cols-1 md:grid-cols-2 gap-6">
              {[
                { title: 'Team Management', desc: 'Manage internal staff and permissions.', icon: Users },
                { title: 'Financial Tracking', desc: 'Monitor internal revenue and expenses.', icon: DollarSign },
                { title: 'Compliance', desc: 'Ensure all business filings are up to date.', icon: ShieldCheck },
                { title: 'Strategic Goals', desc: 'Track and manage quarterly objectives.', icon: Target },
              ].map((op, i) => (
                <div key={i} className="flex items-start gap-4 p-4 rounded-2xl bg-slate-50 border border-slate-100 hover:border-[#5B7CFA]/30 transition-all group">
                  <div className="w-10 h-10 rounded-xl bg-white border border-slate-200 flex items-center justify-center text-[#5B7CFA] group-hover:shadow-sm transition-all">
                    <op.icon className="w-5 h-5" />
                  </div>
                  <div>
                    <h4 className="text-sm font-black text-[#1A2244]">{op.title}</h4>
                    <p className="text-xs text-slate-500 mt-1 leading-relaxed">{op.desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Quick Actions & Alerts */}
        <div className="lg:col-span-4 space-y-8">
          <div className="bg-white border border-slate-200 rounded-3xl p-6 shadow-sm space-y-6">
            <h3 className="text-sm font-black text-[#1A2244] uppercase tracking-widest">Quick Actions</h3>
            <div className="space-y-3">
              {[
                'Update Financials',
                'Review Team Access',
                'Compliance Check',
                'Strategic Review'
              ].map((action, i) => (
                <button key={i} className="w-full py-3 px-4 rounded-xl bg-slate-50 border border-slate-100 text-[10px] font-black text-slate-600 uppercase tracking-widest hover:bg-white hover:border-[#5B7CFA]/30 hover:text-[#5B7CFA] transition-all text-left flex items-center justify-between group">
                  {action}
                  <ArrowUpRight className="w-4 h-4 opacity-0 group-hover:opacity-100 transition-all" />
                </button>
              ))}
            </div>
          </div>

          <div className="bg-white border border-slate-200 rounded-3xl p-6 shadow-sm space-y-6">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-amber-50 flex items-center justify-center text-amber-600">
                <Zap className="w-4 h-4" />
              </div>
              <h3 className="text-sm font-black text-[#1A2244] uppercase tracking-widest">System Alerts</h3>
            </div>
            <div className="space-y-4">
              <div className="p-4 rounded-2xl bg-amber-50 border border-amber-100">
                <p className="text-[10px] font-black text-amber-600 uppercase tracking-widest">Action Required</p>
                <p className="text-xs text-amber-700 mt-1 font-medium">Annual report filing due in 12 days.</p>
              </div>
              <div className="p-4 rounded-2xl bg-blue-50 border border-blue-100">
                <p className="text-[10px] font-black text-[#5B7CFA] uppercase tracking-widest">Update</p>
                <p className="text-xs text-blue-700 mt-1 font-medium">Internal credit score increased by 12 pts.</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
