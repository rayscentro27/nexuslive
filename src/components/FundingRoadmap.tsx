import React from 'react';
import { CheckCircle2, Circle, Lock, ArrowRight, TrendingUp, Flag, Clock, AlertCircle, Zap } from 'lucide-react';
import { cn } from '../lib/utils';

interface Stage {
  id: string;
  title: string;
  description: string;
  status: 'completed' | 'current' | 'locked';
  range?: string;
  timeline?: string;
  tasks?: string[];
}

const stages: Stage[] = [
  {
    id: '1',
    title: 'Level 1: Foundation',
    description: 'Nexus AI will review your progress and business formation.',
    status: 'completed',
    timeline: 'Completed'
  },
  {
    id: '2',
    title: 'Level 2: 0% Interest Cards',
    description: 'Start with 0% interest cards for first-year funding.',
    status: 'current',
    range: '$19,000 - $53,000',
    timeline: 'Active',
    tasks: ['Generate Dispute Letters', 'Upload EIN Document', 'Review Business ID']
  },
  {
    id: '3',
    title: 'Level 3: Business Credit Lines',
    description: 'Access funding for business expansion and inventory.',
    status: 'locked',
    timeline: 'Locked'
  },
  {
    id: '4',
    title: 'Level 4: SBA & Term Loans',
    description: 'Unlock high-limit loans for larger investments.',
    status: 'locked',
    timeline: 'Locked'
  }
];

export function FundingRoadmap() {
  const overallProgress = 32;

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-8 h-full flex flex-col overflow-y-auto no-scrollbar">
      <div className="flex flex-col space-y-2 shrink-0">
        <h1 className="text-3xl font-black text-[#1A2244]">Funding Roadmap</h1>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 bg-blue-50 px-3 py-1 rounded-lg border border-blue-100">
            <TrendingUp className="w-4 h-4 text-[#5B7CFA]" />
            <span className="text-xs font-black text-[#5B7CFA] uppercase tracking-widest">Goal: $100,000+ Funding</span>
          </div>
          <span className="text-sm text-slate-500 font-medium">Currently at Level 2</span>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="shrink-0 space-y-2">
        <div className="flex justify-between text-[10px] font-black text-slate-400 uppercase tracking-widest">
          <span>Overall Roadmap Completion</span>
          <span>{overallProgress}%</span>
        </div>
        <div className="h-3 bg-nexus-100 rounded-full overflow-hidden p-0.5">
          <div 
            className="h-full bg-gradient-to-r from-[#5B7CFA] to-[#3A5EE5] rounded-full shadow-[0_0_8px_rgba(91,124,250,0.4)] transition-all duration-1000" 
            style={{ width: `${overallProgress}%` }}
          />
        </div>
      </div>

      {/* Roadmap Timeline */}
      <div className="relative space-y-8 before:absolute before:left-[19px] before:top-4 before:bottom-4 before:w-1 before:bg-nexus-100 flex-1 pr-1">
        {stages.map((stage, index) => (
          <div key={stage.id} className="relative pl-14">
            {/* Timeline Marker */}
            <div className={cn(
              "absolute left-0 top-2 w-10 h-10 rounded-2xl flex items-center justify-center z-10 shadow-lg transition-all duration-500",
              stage.status === 'completed' ? "bg-green-500 text-white rotate-0" :
              stage.status === 'current' ? "bg-[#5B7CFA] text-white shadow-blue-500/30 scale-110" :
              "bg-white border-2 border-slate-100 text-slate-300"
            )}>
              {stage.status === 'completed' ? <CheckCircle2 className="w-6 h-6" /> : 
               stage.status === 'locked' ? <Lock className="w-4 h-4" /> :
               <Zap className="w-5 h-5 animate-pulse" />}
            </div>

            {/* Stage Card */}
            <div className={cn(
              "glass-card p-6 transition-all duration-300 relative overflow-hidden",
              stage.status === 'current' ? "border-2 border-[#5B7CFA]/20 shadow-xl shadow-blue-500/5" : 
              stage.status === 'locked' ? "opacity-60 bg-slate-50/50" : "bg-white/40"
            )}>
              {stage.status === 'current' && (
                <div className="absolute top-0 right-0 w-32 h-32 bg-blue-500/5 rounded-full -mr-16 -mt-16 blur-2xl" />
              )}
              
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 relative z-10">
                <div className="space-y-1">
                  <div className="flex items-center gap-3">
                    <h3 className="text-xl font-black text-[#1A2244]">{stage.title}</h3>
                    {stage.status === 'completed' && (
                      <span className="px-2 py-0.5 bg-green-50 text-green-600 text-[8px] font-black uppercase rounded-md">Unlocked</span>
                    )}
                    {stage.status === 'current' && (
                      <span className="px-2 py-0.5 bg-[#5B7CFA] text-white text-[8px] font-black uppercase rounded-md animate-pulse">Active Level</span>
                    )}
                  </div>
                  <p className="text-sm text-slate-500 font-medium max-w-xl">{stage.description}</p>
                </div>
                <div className="text-right">
                  <p className="text-[8px] font-black text-slate-400 uppercase tracking-widest">Status</p>
                  <p className={cn(
                    "text-sm font-black uppercase tracking-widest",
                    stage.status === 'completed' ? "text-green-500" :
                    stage.status === 'current' ? "text-[#5B7CFA]" :
                    "text-slate-400"
                  )}>{stage.timeline}</p>
                </div>
              </div>

              {stage.status === 'current' && (
                <div className="mt-6 pt-6 border-t border-nexus-100 space-y-6 relative z-10">
                  <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 bg-blue-50/30 p-6 rounded-2xl border border-blue-100/50">
                    <div className="space-y-1">
                      <p className="text-[10px] font-black text-[#5B7CFA] uppercase tracking-widest">Projected Approvals</p>
                      <h4 className="text-3xl font-black text-[#1A2244]">{stage.range}</h4>
                      <p className="text-[10px] text-slate-400 font-bold uppercase tracking-widest">Based on 65% Readiness</p>
                    </div>
                    <button className="bg-[#5B7CFA] text-white py-3 px-6 rounded-xl text-xs font-black uppercase tracking-widest shadow-lg shadow-blue-500/20 hover:bg-[#4A6BEB] transition-all flex items-center gap-2">
                      View Funding Options
                      <ArrowRight className="w-4 h-4" />
                    </button>
                  </div>

                  {stage.tasks && (
                    <div className="space-y-4">
                      <p className="text-[10px] font-black text-[#1A2244] uppercase tracking-widest flex items-center gap-2">
                        <Flag className="w-4 h-4 text-[#5B7CFA]" />
                        Required Action Steps to Level 3
                      </p>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                        {stage.tasks.map((task, i) => (
                          <div key={i} className="flex items-center justify-between p-3.5 bg-white border border-slate-100 rounded-xl hover:border-[#5B7CFA]/30 transition-all group shadow-sm">
                            <div className="flex items-center gap-3">
                              <div className="w-5 h-5 rounded-full border-2 border-slate-200 flex items-center justify-center group-hover:border-[#5B7CFA] transition-colors">
                                <div className="w-2.5 h-2.5 rounded-full bg-[#5B7CFA] opacity-0 group-hover:opacity-100 transition-opacity" />
                              </div>
                              <span className="text-xs font-bold text-slate-700">{task}</span>
                            </div>
                            <button className="text-[10px] font-black text-[#5B7CFA] px-3 py-1 bg-blue-50 rounded-lg opacity-0 group-hover:opacity-100 transition-all uppercase tracking-widest">
                              Start
                            </button>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {stage.status === 'locked' && (
                <div className="mt-4 flex items-center gap-2 text-xs text-slate-400 font-medium">
                  <AlertCircle className="w-4 h-4" />
                  <span>Reach Level 3 readiness to unlock these funding products.</span>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
