import React, { useEffect, useState } from 'react';
import {
  ArrowRight,
  CheckCircle2,
  TrendingUp,
  ShieldCheck,
  FileText,
  Zap,
  Lock,
  AlertCircle,
  Loader2
} from 'lucide-react';
import { cn } from '../lib/utils';
import { BotAvatar } from './BotAvatar';
import { useAuth } from './AuthProvider';
import {
  getProfile, getTasks, getActivity, getCreditReport,
  UserProfile, Task, ActivityItem, CreditReport
} from '../lib/db';

export function Dashboard() {
  const { user } = useAuth();
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [activity, setActivity] = useState<ActivityItem[]>([]);
  const [credit, setCredit] = useState<CreditReport | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!user) return;
    (async () => {
      const [profileRes, tasksRes, activityRes, creditRes] = await Promise.all([
        getProfile(user.id),
        getTasks(user.id),
        getActivity(user.id, 5),
        getCreditReport(user.id),
      ]);
      setProfile(profileRes.data);
      setTasks(tasksRes.data);
      setActivity(activityRes.data);
      setCredit(creditRes.data);
      setLoading(false);
    })();
  }, [user]);

  // Derived display values — fall back to sensible defaults when DB is fresh
  const readinessScore = profile?.readiness_score ?? 65;
  const userName = profile?.full_name ?? user?.user_metadata?.full_name ?? user?.email?.split('@')[0] ?? 'there';
  const subscriptionPlan = profile?.subscription_plan ?? 'free';

  const primaryTask = tasks.find(t => t.is_primary && t.status !== 'complete');
  const nextStep = primaryTask?.title ?? 'Complete Business Details';

  const pendingTasks = tasks.filter(t => t.status !== 'complete');

  const creditScore = credit?.score ?? null;
  const fundingMin = credit?.funding_range_min ?? 13000;
  const fundingMax = credit?.funding_range_max ?? 75000;
  const utilization = credit?.utilization_percent ?? null;

  const fundingLevel = profile?.current_funding_level ?? 1;
  const roadmapSteps = [
    { label: 'L1: Foundation',       completed: fundingLevel > 1,  active: fundingLevel === 1, locked: false },
    { label: 'L2: 0% Cards',         completed: fundingLevel > 2,  active: fundingLevel === 2, locked: fundingLevel < 2 },
    { label: 'L3: Business Credit',  completed: fundingLevel > 3,  active: fundingLevel === 3, locked: fundingLevel < 3 },
    { label: 'L4: SBA & Term Loans', completed: false,             active: fundingLevel === 4, locked: fundingLevel < 4 },
  ];

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <Loader2 className="w-6 h-6 animate-spin text-[#5B7CFA]" />
      </div>
    );
  }

  return (
    <div className="p-3 space-y-3 max-w-7xl mx-auto h-full flex flex-col overflow-y-auto no-scrollbar">
      {/* Global Progress Bar */}
      <div className="shrink-0 space-y-1">
        <div className="flex justify-between items-end">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded-lg bg-blue-50 flex items-center justify-center text-[#5B7CFA]">
              <TrendingUp className="w-3.5 h-3.5" />
            </div>
            <div>
              <p className="text-[8px] font-black text-slate-400 uppercase tracking-widest">Overall Progress</p>
              <h2 className="text-[10px] font-black text-[#1A2244]">Path to $100k Funding</h2>
            </div>
          </div>
          <div className="text-right">
            <span className="text-lg font-black text-[#5B7CFA]">{readinessScore}%</span>
            <p className="text-[8px] font-bold text-slate-400 uppercase tracking-widest">Readiness</p>
          </div>
        </div>
        <div className="w-full h-2 bg-nexus-100 rounded-full overflow-hidden shadow-inner p-0.5">
          <div
            className="h-full bg-gradient-to-r from-[#5B7CFA] to-[#3A5EE5] rounded-full shadow-[0_0_8px_rgba(91,124,250,0.4)] transition-all duration-1000"
            style={{ width: `${readinessScore}%` }}
          />
        </div>
      </div>

      {/* Hero Section */}
      <div className="glass-card p-3 relative overflow-hidden shrink-0 bg-gradient-to-br from-white to-blue-50/30 border-2 border-[#5B7CFA]/10">
        <div className="absolute top-0 right-0 w-48 h-48 bg-blue-500/5 rounded-full -mr-16 -mt-16 blur-3xl" />
        <div className="relative z-10 space-y-2.5">
          {/* Status Row */}
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <div className="flex items-center gap-2 bg-white px-2.5 py-1 rounded-xl border border-slate-100 shadow-sm">
                <div className="w-4 h-4 rounded-full bg-blue-50 flex items-center justify-center text-[#5B7CFA]">
                  <Zap className="w-2.5 h-2.5 fill-current" />
                </div>
                <span className="text-[9px] font-black text-[#1A2244] uppercase tracking-widest">
                  {readinessScore}% Ready
                </span>
              </div>
              <div className="flex items-center gap-2 bg-green-50 px-2.5 py-1 rounded-xl border border-green-100 shadow-sm">
                <TrendingUp className="w-3 h-3 text-green-600" />
                <span className="text-[9px] font-black text-green-700 uppercase tracking-widest">
                  ${(fundingMin / 1000).toFixed(0)}k–${(fundingMax / 1000).toFixed(0)}k Potential
                </span>
              </div>
            </div>

            <div className="flex items-center gap-2 bg-white/60 backdrop-blur-sm px-2.5 py-0.5 rounded-xl border border-white/80 shadow-sm">
              <div className="text-right">
                <p className="text-[6px] font-black text-[#5B7CFA] uppercase tracking-widest leading-none">AI Advisor</p>
                <p className="text-[8px] text-slate-500 font-bold leading-tight">
                  {pendingTasks.length > 0 ? `${pendingTasks.length} tasks waiting` : 'All caught up!'}
                </p>
              </div>
              <BotAvatar type="dashboard" size="xs" />
            </div>
          </div>

          {/* Next Step */}
          <div className="flex items-center justify-between gap-4 bg-white/40 p-1.5 rounded-xl border border-white/60">
            <div className="flex items-center gap-2.5 pl-1.5">
              <div className="w-7 h-7 rounded-lg bg-[#5B7CFA]/10 flex items-center justify-center text-[#5B7CFA]">
                <ArrowRight className="w-3.5 h-3.5" />
              </div>
              <div>
                <p className="text-[7px] font-black text-slate-400 uppercase tracking-widest">Next Step</p>
                <h3 className="text-xs font-black text-[#1A2244] leading-tight">{nextStep}</h3>
              </div>
            </div>
            <button className="bg-[#5B7CFA] text-white px-5 py-2 rounded-lg text-[10px] font-black uppercase tracking-widest shadow-lg shadow-blue-500/20 hover:bg-[#4A6BEB] transition-all flex items-center gap-2 group">
              Take Action
              <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-1 transition-transform" />
            </button>
          </div>
        </div>
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-3 shrink-0">
        {/* Action Center Card */}
        <div className="lg:col-span-4 glass-card p-3 space-y-3 relative overflow-hidden border-2 border-[#5B7CFA]/10">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Zap className="w-3.5 h-3.5 text-[#5B7CFA]" />
              <h3 className="text-xs font-black text-[#1A2244]">Action Center</h3>
            </div>
            <span className="text-[7px] font-black text-slate-400 uppercase tracking-widest">
              {pendingTasks.length} Tasks
            </span>
          </div>

          {primaryTask ? (
            <div className="p-2.5 rounded-xl bg-[#5B7CFA]/5 border border-[#5B7CFA]/20 space-y-1.5">
              <div className="flex items-center justify-between">
                <span className="px-1 py-0.5 bg-[#5B7CFA] text-white text-[6px] font-black uppercase rounded-md">Primary</span>
                <span className="text-[7px] font-black text-green-600 uppercase tracking-widest">+{primaryTask.readiness_impact}%</span>
              </div>
              <div className="flex items-center justify-between gap-2">
                <h4 className="text-[10px] font-black text-[#1A2244] leading-tight">{primaryTask.title}</h4>
                <button className="w-6 h-6 rounded-lg bg-[#5B7CFA] text-white flex items-center justify-center shrink-0">
                  <ArrowRight className="w-3 h-3" />
                </button>
              </div>
            </div>
          ) : (
            <div className="p-2.5 rounded-xl bg-green-50 border border-green-100 text-center">
              <CheckCircle2 className="w-4 h-4 text-green-500 mx-auto mb-1" />
              <p className="text-[9px] font-bold text-green-700">Primary tasks complete!</p>
            </div>
          )}

          <div className="space-y-1.5">
            {pendingTasks.filter(t => !t.is_primary).slice(0, 2).map((task) => (
              <div key={task.id} className="flex items-center justify-between p-1.5 rounded-lg bg-white/40 border border-white/60 shadow-sm group cursor-pointer">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full border border-slate-200 flex items-center justify-center group-hover:border-[#5B7CFA]">
                    <div className="w-1.5 h-1.5 rounded-full bg-[#5B7CFA] opacity-0 group-hover:opacity-100" />
                  </div>
                  <p className="text-[9px] font-bold text-[#1A2244] truncate max-w-[120px]">{task.title}</p>
                </div>
                <span className="text-[7px] font-black text-green-500 uppercase tracking-widest">+{task.readiness_impact}%</span>
              </div>
            ))}
          </div>
        </div>

        {/* Credit Analysis Card */}
        <div className="lg:col-span-5 glass-card p-3 space-y-3">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-3.5 h-3.5 text-green-500" />
            <h3 className="text-xs font-black text-[#1A2244]">Credit Analysis</h3>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-0.5">
              <p className="text-[7px] font-bold text-slate-400 uppercase tracking-widest">Funding Range</p>
              <h4 className="text-base font-black text-[#1A2244]">
                ${(fundingMin / 1000).toFixed(0)}k – ${(fundingMax / 1000).toFixed(0)}k
              </h4>
            </div>
            <div className="text-right space-y-0.5">
              {creditScore && (
                <>
                  <p className="text-[7px] font-black text-green-500 uppercase tracking-widest">Credit Score</p>
                  <p className="text-xs font-black text-[#1A2244]">{creditScore}</p>
                </>
              )}
            </div>
          </div>

          {utilization != null && utilization > 10 ? (
            <div className="p-2 rounded-lg bg-amber-50 border border-amber-100 flex items-start gap-1.5">
              <AlertCircle className="w-3 h-3 text-amber-500 shrink-0 mt-0.5" />
              <p className="text-[9px] text-amber-800 font-medium leading-tight">
                Utilization at {utilization.toFixed(0)}%. Drop to &lt;10% for <span className="font-black">+12% Readiness</span>.
              </p>
            </div>
          ) : (
            <div className="p-2 rounded-lg bg-blue-50 border border-blue-100 flex items-start gap-1.5">
              <ShieldCheck className="w-3 h-3 text-blue-500 shrink-0 mt-0.5" />
              <p className="text-[9px] text-blue-800 font-medium leading-tight">
                Upload your credit report to unlock personalized funding insights.
              </p>
            </div>
          )}

          <button className="w-full py-2 rounded-lg bg-[#5B7CFA] text-white text-[9px] font-black uppercase tracking-widest shadow-lg shadow-blue-500/20 hover:bg-[#4A6BEB] transition-all">
            Optimize Credit
          </button>
        </div>

        {/* Roadmap Mini */}
        <div className="lg:col-span-3 glass-card p-3 space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-black text-[#1A2244]">Roadmap</h3>
            <span className="text-[7px] font-black text-[#5B7CFA] uppercase tracking-widest">Level {fundingLevel}</span>
          </div>
          <div className="space-y-2">
            {roadmapSteps.map((step, i) => (
              <div key={i} className={cn(
                "flex items-center gap-2 p-1.5 rounded-lg border",
                step.active ? "bg-blue-50/50 border-blue-100" :
                step.completed ? "border-green-100/50 bg-green-50/20" :
                "border-slate-50 opacity-50"
              )}>
                {step.completed ? <CheckCircle2 className="w-2.5 h-2.5 text-green-500" /> :
                 step.locked ? <Lock className="w-2.5 h-2.5 text-slate-300" /> :
                 <div className="w-2.5 h-2.5 rounded-full border-2 border-[#5B7CFA]" />}
                <p className="text-[8px] font-bold text-[#1A2244]">{step.label}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Bottom Row: Activity & Profile */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-3 flex-1 min-h-0">
        <div className="lg:col-span-7 glass-card p-3 space-y-2 flex flex-col overflow-hidden">
          <div className="flex items-center justify-between shrink-0">
            <h3 className="text-xs font-black text-[#1A2244]">Recent Activity</h3>
            <button className="text-[7px] font-black text-slate-400 uppercase tracking-widest">View All</button>
          </div>
          <div className="space-y-2.5 overflow-y-auto no-scrollbar pr-1 flex-1">
            {activity.length > 0 ? (
              activity.map((item) => (
                <div key={item.id} className="flex gap-2.5">
                  <div className="shrink-0">
                    <div className="w-7 h-7 rounded-lg bg-blue-50 flex items-center justify-center text-[#5B7CFA]">
                      <Zap className="w-3.5 h-3.5" />
                    </div>
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between">
                      <p className="text-[9px] font-bold text-[#1A2244] truncate">{item.actor}</p>
                      <span className="text-[7px] font-bold text-slate-400 ml-2 shrink-0">
                        {new Date(item.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </span>
                    </div>
                    <p className="text-[9px] text-slate-500 font-medium truncate">{item.action}</p>
                  </div>
                </div>
              ))
            ) : (
              // Static fallback activity for fresh accounts
              [
                { actor: 'James Mitchell', action: "Analyzed credit report. Found 2 new disputes.", time: '10m' },
                { actor: 'Nexus AI', action: "Business entity filed Articles of Incorporation.", time: '2h' },
                { actor: 'Nexus AI', action: "Credit report data parsed. 5 items found.", time: '4h' }
              ].map((item, i) => (
                <div key={i} className="flex gap-2.5">
                  <div className="shrink-0">
                    <div className="w-7 h-7 rounded-lg bg-blue-50 flex items-center justify-center text-[#5B7CFA]">
                      <FileText className="w-3.5 h-3.5" />
                    </div>
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between">
                      <p className="text-[9px] font-bold text-[#1A2244] truncate">{item.actor}</p>
                      <span className="text-[7px] font-bold text-slate-400">{item.time}</span>
                    </div>
                    <p className="text-[9px] text-slate-500 font-medium truncate">{item.action}</p>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        <div className="lg:col-span-5 glass-card p-3 space-y-3 flex flex-col">
          <div className="flex items-center gap-2.5 shrink-0">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[#5B7CFA] to-[#3A5EE5] flex items-center justify-center text-white font-black text-sm">
              {userName.charAt(0).toUpperCase()}
            </div>
            <div>
              <h3 className="text-[10px] font-black text-[#1A2244]">{userName}</h3>
              <p className="text-[7px] text-slate-400 font-bold uppercase tracking-widest">{subscriptionPlan} plan</p>
            </div>
          </div>

          <div className="space-y-2 flex-1">
            <div className="flex items-baseline justify-between">
              <span className="text-xl font-black text-[#1A2244]">{readinessScore}%</span>
              <span className="text-[7px] font-bold text-slate-400 uppercase tracking-widest">Readiness Score</span>
            </div>
            <div className="w-full h-1 bg-nexus-100 rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-blue-400 to-indigo-500 transition-all duration-500"
                style={{ width: `${readinessScore}%` }}
              />
            </div>
            <button className="w-full py-1.5 rounded-lg bg-white border border-slate-100 text-[#1A2244] text-[8px] font-black uppercase tracking-widest shadow-sm hover:bg-slate-50 transition-all">
              Account Settings
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
