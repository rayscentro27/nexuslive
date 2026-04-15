import React, { useEffect, useState } from 'react';
import { CheckCircle2, Lock, ArrowRight, TrendingUp, Flag, AlertCircle, Zap, Loader2 } from 'lucide-react';
import { cn } from '../lib/utils';
import { useAuth } from './AuthProvider';
import { getFundingStages, FundingStage, FundingAction } from '../lib/db';

type StageWithActions = FundingStage & { funding_actions: FundingAction[] };

// Static fallback stages shown before DB is populated
const STATIC_STAGES: StageWithActions[] = [
  { id: '1', user_id: '', stage_number: 1, title: 'Level 1: Business Foundation', description: 'Establish your legal entity, EIN, business address, and basic credit profile.', status: 'completed', funding_range_min: 0, funding_range_max: 19000, readiness_required: 20, projected_approvals: 3, timeline_weeks: 4, funding_actions: [] },
  { id: '2', user_id: '', stage_number: 2, title: 'Level 2: 0% Interest Cards', description: 'Qualify for 0% business credit cards based on personal credit and business credibility.', status: 'current', funding_range_min: 19000, funding_range_max: 53000, readiness_required: 65, projected_approvals: 5, timeline_weeks: 8, funding_actions: [
    { id: 'a', stage_id: '2', user_id: '', title: 'Generate Dispute Letters', description: null, status: 'pending', readiness_impact: 8, sort_order: 1 },
    { id: 'b', stage_id: '2', user_id: '', title: 'Upload EIN Document', description: null, status: 'pending', readiness_impact: 5, sort_order: 2 },
    { id: 'c', stage_id: '2', user_id: '', title: 'Review Business ID', description: null, status: 'in_progress', readiness_impact: 4, sort_order: 3 },
  ] },
  { id: '3', user_id: '', stage_number: 3, title: 'Level 3: Business Credit Lines', description: 'Build dedicated business credit lines with net terms and bank credit products.', status: 'locked', funding_range_min: 50000, funding_range_max: 150000, readiness_required: 80, projected_approvals: 4, timeline_weeks: 16, funding_actions: [] },
  { id: '4', user_id: '', stage_number: 4, title: 'Level 4: SBA & Term Loans', description: 'Access SBA 7(a) loans, term loans, and institutional capital with proven revenue history.', status: 'locked', funding_range_min: 100000, funding_range_max: 500000, readiness_required: 90, projected_approvals: 2, timeline_weeks: 26, funding_actions: [] },
];

function fmtK(n: number) {
  return `$${(n / 1000).toFixed(0)}k`;
}

export function FundingRoadmap() {
  const { user } = useAuth();
  const [stages, setStages] = useState<StageWithActions[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!user) return;
    (async () => {
      const { data } = await getFundingStages(user.id);
      setStages(data.length > 0 ? data : STATIC_STAGES);
      setLoading(false);
    })();
  }, [user]);

  const completedStages = stages.filter(s => s.status === 'completed').length;
  const overallProgress = stages.length > 0 ? Math.round((completedStages / stages.length) * 100) : 32;
  const currentStage = stages.find(s => s.status === 'current');

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-8 h-full flex flex-col overflow-y-auto no-scrollbar">
      <div className="flex flex-col space-y-2 shrink-0">
        <h1 className="text-3xl font-black text-[#1A2244]">Funding Roadmap</h1>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 bg-blue-50 px-3 py-1 rounded-lg border border-blue-100">
            <TrendingUp className="w-4 h-4 text-[#5B7CFA]" />
            <span className="text-xs font-black text-[#5B7CFA] uppercase tracking-widest">Goal: $100,000+ Funding</span>
          </div>
          {currentStage && (
            <span className="text-sm text-slate-500 font-medium">Currently at {currentStage.title}</span>
          )}
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

      {loading ? (
        <div className="flex-1 flex items-center justify-center">
          <Loader2 className="w-6 h-6 animate-spin text-[#5B7CFA]" />
        </div>
      ) : (
        /* Roadmap Timeline */
        <div className="relative space-y-8 before:absolute before:left-[19px] before:top-4 before:bottom-4 before:w-1 before:bg-nexus-100 flex-1 pr-1">
          {stages.map((stage) => (
            <div key={stage.id} className="relative pl-14">
              {/* Timeline Marker */}
              <div className={cn(
                "absolute left-0 top-2 w-10 h-10 rounded-2xl flex items-center justify-center z-10 shadow-lg transition-all duration-500",
                stage.status === 'completed' ? "bg-green-500 text-white" :
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
                  <div className="text-right shrink-0">
                    {stage.funding_range_min != null && stage.funding_range_max != null && (
                      <>
                        <p className="text-[8px] font-black text-slate-400 uppercase tracking-widest">Funding Range</p>
                        <p className={cn(
                          "text-sm font-black",
                          stage.status === 'completed' ? "text-green-500" :
                          stage.status === 'current' ? "text-[#5B7CFA]" : "text-slate-400"
                        )}>
                          {fmtK(stage.funding_range_min)} – {fmtK(stage.funding_range_max)}
                        </p>
                      </>
                    )}
                  </div>
                </div>

                {/* Current Stage: Actions & CTA */}
                {stage.status === 'current' && (
                  <div className="mt-6 pt-6 border-t border-nexus-100 space-y-6 relative z-10">
                    <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 bg-blue-50/30 p-6 rounded-2xl border border-blue-100/50">
                      <div className="space-y-1">
                        <p className="text-[10px] font-black text-[#5B7CFA] uppercase tracking-widest">Projected Approvals</p>
                        {stage.funding_range_min != null && stage.funding_range_max != null && (
                          <h4 className="text-3xl font-black text-[#1A2244]">
                            {fmtK(stage.funding_range_min)} – {fmtK(stage.funding_range_max)}
                          </h4>
                        )}
                        <p className="text-[10px] text-slate-400 font-bold uppercase tracking-widest">
                          Requires {stage.readiness_required}% Readiness
                          {stage.timeline_weeks && ` • ~${stage.timeline_weeks} weeks`}
                        </p>
                      </div>
                      <button className="bg-[#5B7CFA] text-white py-3 px-6 rounded-xl text-xs font-black uppercase tracking-widest shadow-lg shadow-blue-500/20 hover:bg-[#4A6BEB] transition-all flex items-center gap-2">
                        View Funding Options
                        <ArrowRight className="w-4 h-4" />
                      </button>
                    </div>

                    {stage.funding_actions?.length > 0 && (
                      <div className="space-y-4">
                        <p className="text-[10px] font-black text-[#1A2244] uppercase tracking-widest flex items-center gap-2">
                          <Flag className="w-4 h-4 text-[#5B7CFA]" />
                          Required Action Steps to Next Level
                        </p>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                          {stage.funding_actions.map((action) => (
                            <div key={action.id} className="flex items-center justify-between p-3.5 bg-white border border-slate-100 rounded-xl hover:border-[#5B7CFA]/30 transition-all group shadow-sm">
                              <div className="flex items-center gap-3">
                                <div className={cn(
                                  "w-5 h-5 rounded-full border-2 flex items-center justify-center",
                                  action.status === 'complete' ? "border-green-400 bg-green-50" : "border-slate-200 group-hover:border-[#5B7CFA]"
                                )}>
                                  {action.status === 'complete'
                                    ? <CheckCircle2 className="w-3 h-3 text-green-500" />
                                    : <div className="w-2.5 h-2.5 rounded-full bg-[#5B7CFA] opacity-0 group-hover:opacity-100 transition-opacity" />
                                  }
                                </div>
                                <span className="text-xs font-bold text-slate-700">{action.title}</span>
                              </div>
                              <span className="text-[8px] font-black text-green-600 uppercase tracking-widest">+{action.readiness_impact}%</span>
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
                    <span>Reach {stage.readiness_required}% readiness to unlock this funding tier.</span>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
