import React from 'react';
import { CheckCircle2, Circle, ArrowRight, Shield, Zap, FileText, Play, Eye, Settings, HelpCircle, Clock } from 'lucide-react';
import { cn } from '../lib/utils';
import { BotAvatar } from './BotAvatar';

export function Funding() {
  const readiness = 82;

  return (
    <div className="p-4 max-w-6xl mx-auto space-y-4 h-full flex flex-col overflow-y-auto no-scrollbar">
      <div className="flex flex-col space-y-1 shrink-0">
        <h1 className="text-xl font-black text-[#1A2244]">Funding Application</h1>
        <p className="text-[10px] text-slate-500 font-bold uppercase tracking-widest">Apply for business capital with AI-guided precision.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 flex-1">
        {/* Left Column: Readiness & Checklist */}
        <div className="lg:col-span-2 space-y-4">
          {/* Readiness Card */}
          <div className="glass-card p-5 bg-gradient-to-br from-white to-blue-50/30 relative overflow-hidden">
            <div className="flex items-center gap-6 relative z-10">
              <div className="relative w-28 h-28 flex items-center justify-center shrink-0">
                <svg className="w-full h-full transform -rotate-90">
                  <circle cx="56" cy="56" r="50" fill="none" stroke="#E8EEFF" strokeWidth="8" />
                  <circle
                    cx="56"
                    cy="56"
                    r="50"
                    fill="none"
                    stroke="#5B7CFA"
                    strokeWidth="8"
                    strokeDasharray={314}
                    strokeDashoffset={314 * (1 - readiness / 100)}
                    strokeLinecap="round"
                  />
                </svg>
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                  <span className="text-xl font-black text-[#1A2244]">{readiness}%</span>
                  <span className="text-[8px] font-black text-slate-400 uppercase">Ready</span>
                </div>
              </div>
              <div className="space-y-3">
                <div className="space-y-1">
                  <h2 className="text-lg font-black text-[#1A2244]">You're ready to apply!</h2>
                  <p className="text-[11px] text-slate-500 font-medium">Your profile meets requirements for $50k+ funding.</p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <span className="px-2 py-0.5 bg-green-50 text-green-600 text-[8px] font-black uppercase rounded-md flex items-center gap-1.5">
                    <CheckCircle2 className="w-3 h-3" /> EIN Verified
                  </span>
                  <span className="px-2 py-0.5 bg-green-50 text-green-600 text-[8px] font-black uppercase rounded-md flex items-center gap-1.5">
                    <CheckCircle2 className="w-3 h-3" /> Docs Verified
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Prep Checklist */}
          <div className="glass-card p-5 space-y-4">
            <h3 className="text-sm font-black text-[#1A2244] flex items-center gap-2">
              <FileText className="w-4 h-4 text-[#5B7CFA]" />
              Application Prep Checklist
            </h3>
            <div className="space-y-2">
              {[
                { label: 'Business EIN & Formation Docs', status: 'completed' },
                { label: 'Last 3 Months Bank Statements', status: 'completed' },
                { label: 'Business Website & Email', status: 'completed' },
                { label: 'Personal ID (Driver\'s License)', status: 'pending' },
              ].map((item, i) => (
                <div key={i} className="flex items-center justify-between p-3 bg-slate-50/50 rounded-xl border border-slate-100 group hover:border-[#5B7CFA]/20 transition-all">
                  <div className="flex items-center gap-3">
                    {item.status === 'completed' ? (
                      <CheckCircle2 className="w-4 h-4 text-green-500" />
                    ) : (
                      <div className="w-4 h-4 border-2 border-slate-200 rounded-full" />
                    )}
                    <span className={cn("text-xs font-bold", item.status === 'completed' ? "text-slate-700" : "text-slate-400")}>
                      {item.label}
                    </span>
                  </div>
                  {item.status === 'pending' && (
                    <button className="text-[9px] font-black text-[#5B7CFA] px-3 py-1 bg-white rounded-lg border border-blue-100 shadow-sm uppercase tracking-widest">
                      Upload
                    </button>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right Column: AI Recommendation & Tracker */}
        <div className="space-y-8">
          {/* AI Recommendation */}
          <div className="glass-card p-6 bg-nexus-950 text-white space-y-6 relative overflow-hidden">
            <div className="absolute top-0 right-0 w-32 h-32 bg-nexus-500/20 rounded-full -mr-16 -mt-16 blur-2xl" />
            <div className="flex items-center gap-3 relative z-10">
              <div className="w-10 h-10 bg-nexus-500 rounded-xl flex items-center justify-center">
                <Zap className="w-6 h-6" />
              </div>
              <h3 className="font-bold">AI Recommendation</h3>
            </div>
            <p className="text-sm text-nexus-100 leading-relaxed relative z-10">
              "Based on your profile, I recommend applying to <span className="text-nexus-400 font-bold">Chase Business</span> first. They have the highest approval odds for your industry right now."
            </p>
            <button className="w-full bg-nexus-500 text-white font-bold py-3 rounded-xl shadow-lg hover:bg-nexus-600 transition-all relative z-10">
              Apply Now
            </button>
          </div>

          {/* Guidance Modes */}
          <div className="glass-card p-6 space-y-4">
            <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider">Guidance Mode</h3>
            <div className="grid grid-cols-1 gap-2">
              {[
                { icon: Eye, label: 'Watch', desc: 'Video tutorial' },
                { icon: Play, label: 'Guided', desc: 'Step-by-step' },
                { icon: Settings, label: 'Auto', desc: 'AI-assisted' },
              ].map((mode, i) => (
                <button key={i} className="flex items-center gap-3 p-3 hover:bg-slate-50 rounded-xl transition-all group text-left">
                  <div className="w-10 h-10 bg-slate-100 text-slate-500 rounded-xl flex items-center justify-center group-hover:bg-nexus-50 group-hover:text-nexus-600 transition-all">
                    <mode.icon className="w-5 h-5" />
                  </div>
                  <div>
                    <p className="font-bold text-slate-700 group-hover:text-nexus-700">{mode.label}</p>
                    <p className="text-[10px] text-slate-400 font-bold uppercase">{mode.desc}</p>
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* Application Tracker */}
          <div className="glass-card p-6 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider">Tracker</h3>
              <button className="text-[10px] font-bold text-nexus-600">View All</button>
            </div>
            <div className="space-y-4">
              {[
                { bank: 'Chase Business', status: 'Approved', amount: '$25,000', color: 'text-green-600', bgColor: 'bg-green-50' },
                { bank: 'Amex Blue', status: 'Pending', amount: '$15,000', color: 'text-blue-600', bgColor: 'bg-blue-50' },
              ].map((app, i) => (
                <div key={i} className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className={cn("w-10 h-10 rounded-xl flex items-center justify-center font-black", app.bgColor, app.color)}>
                      {app.bank[0]}
                    </div>
                    <div>
                      <p className="text-sm font-bold text-slate-900">{app.bank}</p>
                      <p className="text-xs text-slate-500">{app.amount}</p>
                    </div>
                  </div>
                  <span className={cn("text-[10px] font-bold uppercase px-2 py-1 rounded-lg", app.bgColor, app.color)}>
                    {app.status}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
