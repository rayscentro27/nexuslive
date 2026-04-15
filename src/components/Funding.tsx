import React, { useState, useEffect } from 'react';
import { CheckCircle2, ArrowRight, Shield, Zap, FileText, Play, Eye, Settings, Loader2 } from 'lucide-react';
import { cn } from '../lib/utils';
import { useAuth } from './AuthProvider';
import { getProfile, getFundingApplications, getTasks, UserProfile, FundingApplication, Task } from '../lib/db';

function statusColors(status: string) {
  switch (status.toLowerCase()) {
    case 'approved':  return { text: 'text-green-600',  bg: 'bg-green-50' };
    case 'pending':   return { text: 'text-blue-600',   bg: 'bg-blue-50' };
    case 'submitted': return { text: 'text-amber-600',  bg: 'bg-amber-50' };
    case 'rejected':  return { text: 'text-red-600',    bg: 'bg-red-50' };
    default:          return { text: 'text-slate-600',  bg: 'bg-slate-50' };
  }
}

function formatAmount(n: number | null) {
  if (n === null) return '—';
  return '$' + n.toLocaleString();
}

export function Funding() {
  const { user } = useAuth();
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [applications, setApplications] = useState<FundingApplication[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!user) return;
    Promise.all([
      getProfile(user.id),
      getFundingApplications(user.id),
      getTasks(user.id),
    ]).then(([{ data: p }, { data: apps }, { data: t }]) => {
      setProfile(p);
      setApplications(apps);
      setTasks(t);
      setLoading(false);
    });
  }, [user]);

  const readiness = profile?.readiness_score ?? 0;
  const circumference = 314;
  const offset = circumference * (1 - readiness / 100);

  // Derive checklist from tasks (primary tasks only)
  const primaryTasks = tasks.filter(t => t.is_primary).slice(0, 4);
  const checklistItems = primaryTasks.length > 0 ? primaryTasks : [
    { id: '1', title: 'Business EIN & Formation Docs', status: 'pending' },
    { id: '2', title: 'Last 3 Months Bank Statements', status: 'pending' },
    { id: '3', title: 'Business Website & Email', status: 'pending' },
    { id: '4', title: "Personal ID (Driver's License)", status: 'pending' },
  ] as any[];

  const readinessLabel = readiness >= 80 ? "You're ready to apply!" : readiness >= 50 ? "Almost there!" : "Keep building your profile";
  const readinessDesc = readiness >= 80
    ? "Your profile meets requirements for $50k+ funding."
    : readiness >= 50
    ? "Complete your remaining tasks to unlock higher funding."
    : "Complete your setup steps to improve your funding readiness.";

  return (
    <div className="p-4 max-w-6xl mx-auto space-y-4 h-full flex flex-col overflow-y-auto no-scrollbar">
      <div className="flex flex-col space-y-1 shrink-0">
        <h1 className="text-xl font-black text-[#1A2244]">Funding Application</h1>
        <p className="text-[10px] text-slate-500 font-bold uppercase tracking-widest">Apply for business capital with AI-guided precision.</p>
      </div>

      {loading ? (
        <div className="flex-1 flex items-center justify-center">
          <Loader2 className="w-6 h-6 text-slate-300 animate-spin" />
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 flex-1">
          {/* Left Column */}
          <div className="lg:col-span-2 space-y-4">
            {/* Readiness Card */}
            <div className="glass-card p-5 bg-gradient-to-br from-white to-blue-50/30 relative overflow-hidden">
              <div className="flex items-center gap-6 relative z-10">
                <div className="relative w-28 h-28 flex items-center justify-center shrink-0">
                  <svg className="w-full h-full transform -rotate-90">
                    <circle cx="56" cy="56" r="50" fill="none" stroke="#E8EEFF" strokeWidth="8" />
                    <circle
                      cx="56" cy="56" r="50" fill="none"
                      stroke={readiness >= 80 ? "#22c55e" : readiness >= 50 ? "#5B7CFA" : "#f59e0b"}
                      strokeWidth="8"
                      strokeDasharray={circumference}
                      strokeDashoffset={offset}
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
                    <h2 className="text-lg font-black text-[#1A2244]">{readinessLabel}</h2>
                    <p className="text-[11px] text-slate-500 font-medium">{readinessDesc}</p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {primaryTasks.filter(t => t.status === 'complete').slice(0, 2).map(t => (
                      <span key={t.id} className="px-2 py-0.5 bg-green-50 text-green-600 text-[8px] font-black uppercase rounded-md flex items-center gap-1.5">
                        <CheckCircle2 className="w-3 h-3" /> {t.title}
                      </span>
                    ))}
                    {primaryTasks.filter(t => t.status === 'complete').length === 0 && (
                      <span className="px-2 py-0.5 bg-slate-50 text-slate-400 text-[8px] font-black uppercase rounded-md">
                        No tasks completed yet
                      </span>
                    )}
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
                {checklistItems.map((item: any) => {
                  const done = item.status === 'complete' || item.status === 'completed';
                  return (
                    <div key={item.id} className="flex items-center justify-between p-3 bg-slate-50/50 rounded-xl border border-slate-100 group hover:border-[#5B7CFA]/20 transition-all">
                      <div className="flex items-center gap-3">
                        {done ? (
                          <CheckCircle2 className="w-4 h-4 text-green-500 shrink-0" />
                        ) : (
                          <div className="w-4 h-4 border-2 border-slate-200 rounded-full shrink-0" />
                        )}
                        <span className={cn("text-xs font-bold", done ? "text-slate-700" : "text-slate-400")}>
                          {item.title}
                        </span>
                      </div>
                      {!done && (
                        <button className="text-[9px] font-black text-[#5B7CFA] px-3 py-1 bg-white rounded-lg border border-blue-100 shadow-sm uppercase tracking-widest">
                          Complete
                        </button>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Right Column */}
          <div className="space-y-4">
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
                {readiness >= 80
                  ? `"Based on your ${readiness}% readiness, you're in a strong position. I recommend applying to Chase Business first — highest approval odds for your profile."`
                  : `"Your readiness is at ${readiness}%. Complete your remaining checklist items to unlock premium lender options and improve approval odds."`
                }
              </p>
              <button className="w-full bg-nexus-500 text-white font-bold py-3 rounded-xl shadow-lg hover:bg-nexus-600 transition-all relative z-10">
                Apply Now
              </button>
            </div>

            {/* Guidance Modes */}
            <div className="glass-card p-5 space-y-4">
              <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider">Guidance Mode</h3>
              <div className="grid grid-cols-1 gap-2">
                {[
                  { icon: Eye, label: 'Watch', desc: 'Video tutorial' },
                  { icon: Play, label: 'Guided', desc: 'Step-by-step' },
                  { icon: Settings, label: 'Auto', desc: 'AI-assisted' },
                ].map((mode, i) => (
                  <button key={i} className="flex items-center gap-3 p-3 hover:bg-slate-50 rounded-xl transition-all group text-left">
                    <div className="w-10 h-10 bg-slate-100 text-slate-500 rounded-xl flex items-center justify-center group-hover:bg-blue-50 group-hover:text-[#5B7CFA] transition-all">
                      <mode.icon className="w-5 h-5" />
                    </div>
                    <div>
                      <p className="font-bold text-slate-700 group-hover:text-[#5B7CFA]">{mode.label}</p>
                      <p className="text-[10px] text-slate-400 font-bold uppercase">{mode.desc}</p>
                    </div>
                  </button>
                ))}
              </div>
            </div>

            {/* Application Tracker */}
            <div className="glass-card p-5 space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider">Tracker</h3>
                <span className="text-[10px] font-bold text-slate-400">{applications.length} apps</span>
              </div>
              {applications.length > 0 ? (
                <div className="space-y-4">
                  {applications.slice(0, 5).map(app => {
                    const { text, bg } = statusColors(app.status);
                    const amount = app.approved_amount ?? app.requested_amount;
                    return (
                      <div key={app.id} className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <div className={cn("w-10 h-10 rounded-xl flex items-center justify-center font-black text-sm", bg, text)}>
                            {(app.lender_name ?? '?')[0].toUpperCase()}
                          </div>
                          <div>
                            <p className="text-sm font-bold text-slate-900">{app.lender_name ?? 'Unknown'}</p>
                            <p className="text-xs text-slate-500">{formatAmount(amount)}</p>
                          </div>
                        </div>
                        <span className={cn("text-[10px] font-bold uppercase px-2 py-1 rounded-lg", bg, text)}>
                          {app.status}
                        </span>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="text-center py-4">
                  <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">No applications yet</p>
                  <p className="text-xs text-slate-400 mt-1">Submit your first application to track it here</p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
