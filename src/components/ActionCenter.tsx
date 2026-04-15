import React, { useState, useEffect } from 'react';
import { CheckCircle2, Circle, Play, ArrowRight, Clock, Zap, ChevronDown, ChevronUp, Loader2 } from 'lucide-react';
import { cn } from '../lib/utils';
import { useAuth } from './AuthProvider';
import { getTasks, updateTaskStatus, Task } from '../lib/db';

// Fallback tasks shown when database is empty or not yet connected
const STARTER_TASKS: Omit<Task, 'id' | 'user_id' | 'created_at'>[] = [
  { title: 'Review Your Credit Analysis',      category: 'credit',          status: 'pending',   priority: 2, readiness_impact: 5,  is_primary: false, duration_minutes: 8,   description: '5 dispute opportunities found in your latest report.',   due_date: null, completed_at: null },
  { title: 'Enter Your Business Details',       category: 'business_setup',  status: 'in_progress', priority: 1, readiness_impact: 8, is_primary: true,  duration_minutes: 10,  description: '1 of 4 fields left to complete.',                        due_date: null, completed_at: null },
  { title: 'Watch Business Funding Guide',      category: 'general',         status: 'pending',   priority: 4, readiness_impact: 2,  is_primary: false, duration_minutes: 10,  description: null,                                                      due_date: null, completed_at: null },
  { title: 'Upload Business Documents',         category: 'business_setup',  status: 'pending',   priority: 2, readiness_impact: 4,  is_primary: false, duration_minutes: 5,   description: '0 of 3 documents uploaded.',                              due_date: null, completed_at: null },
  { title: 'Generate Dispute Letters',          category: 'credit',          status: 'pending',   priority: 2, readiness_impact: 6,  is_primary: false, duration_minutes: 15,  description: null,                                                      due_date: null, completed_at: null },
  { title: 'LLC Formation Verified',            category: 'business_setup',  status: 'complete',  priority: 1, readiness_impact: 10, is_primary: false, duration_minutes: 20,  description: null,                                                      due_date: null, completed_at: new Date().toISOString() },
  { title: 'EIN Obtained',                      category: 'business_setup',  status: 'complete',  priority: 1, readiness_impact: 5,  is_primary: false, duration_minutes: 10,  description: null,                                                      due_date: null, completed_at: new Date().toISOString() },
];

export function ActionCenter() {
  const { user } = useAuth();
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [isCompletedExpanded, setIsCompletedExpanded] = useState(false);

  useEffect(() => {
    if (!user) return;
    (async () => {
      const { data } = await getTasks(user.id);
      // If DB has no tasks yet (pre-migration or empty account), use starters as display
      setTasks(
        data.length > 0
          ? data
          : STARTER_TASKS.map((t, i) => ({ ...t, id: String(i), user_id: user.id, created_at: new Date().toISOString() }))
      );
      setLoading(false);
    })();
  }, [user]);

  const handleComplete = async (taskId: string) => {
    if (!user || taskId.length <= 1) return; // skip fake starter IDs
    const { data } = await updateTaskStatus(taskId, 'complete');
    if (data) setTasks(prev => prev.map(t => t.id === taskId ? data : t));
  };

  const primaryTask = tasks.find(t => t.is_primary && t.status !== 'complete');
  const remainingTasks = tasks.filter(t => !t.is_primary && t.status !== 'complete');
  const completedTasks = tasks.filter(t => t.status === 'complete');

  const totalImpact = tasks.reduce((sum, t) => sum + t.readiness_impact, 0);
  const completedImpact = completedTasks.reduce((sum, t) => sum + t.readiness_impact, 0);
  const progress = totalImpact > 0 ? Math.round((completedImpact / totalImpact) * 100) : 0;

  return (
    <div className="p-3 max-w-6xl mx-auto space-y-3 h-full flex flex-col overflow-y-auto no-scrollbar">
      <div className="flex flex-col space-y-0.5 shrink-0">
        <h1 className="text-xl font-black text-[#1A2244]">Action Center</h1>
        <p className="text-[10px] text-slate-500 font-medium">The engine of your funding journey. Complete tasks to advance.</p>
      </div>

      {/* Progress Bar */}
      <div className="glass-card p-2.5 space-y-1.5 shrink-0 bg-gradient-to-br from-white to-blue-50/30">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-blue-50 flex items-center justify-center text-[#5B7CFA]">
              <Zap className="w-3.5 h-3.5" />
            </div>
            <div>
              <span className="text-[7px] font-black text-slate-400 uppercase tracking-widest">Funding Momentum</span>
              <h2 className="text-[11px] font-black text-[#1A2244]">
                {remainingTasks.length + (primaryTask ? 1 : 0)} tasks left before funding unlock
              </h2>
            </div>
          </div>
          <div className="text-right">
            <span className="text-base font-black text-[#5B7CFA]">{progress}%</span>
            <p className="text-[6px] font-bold text-slate-400 uppercase tracking-widest">Completion</p>
          </div>
        </div>
        <div className="h-1.5 bg-nexus-100 rounded-full overflow-hidden p-0.5">
          <div
            className="h-full bg-gradient-to-r from-[#5B7CFA] to-[#3A5EE5] rounded-full shadow-[0_0_4px_rgba(91,124,250,0.3)] transition-all duration-500"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      {loading ? (
        <div className="flex-1 flex items-center justify-center">
          <Loader2 className="w-6 h-6 animate-spin text-[#5B7CFA]" />
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-3 flex-1 min-h-0">
          {/* Primary Task */}
          <div className="lg:col-span-5 space-y-2">
            <h2 className="text-[11px] font-black text-slate-400 uppercase tracking-widest px-1">Next Best Action</h2>
            {primaryTask ? (
              <div className="glass-card p-3.5 border-2 border-[#5B7CFA]/20 bg-blue-50/10 relative overflow-hidden h-full flex flex-col justify-between">
                <div className="absolute top-0 left-0 w-1 h-full bg-[#5B7CFA]" />
                <div className="space-y-2.5">
                  <div className="flex items-center justify-between">
                    <div className="w-8 h-8 rounded-lg bg-blue-50 text-[#5B7CFA] flex items-center justify-center">
                      <Play className="w-4 h-4 fill-current" />
                    </div>
                    <span className="px-1.5 py-0.5 bg-[#5B7CFA] text-white text-[7px] font-black uppercase rounded-md">Primary</span>
                  </div>
                  <div className="space-y-0.5">
                    <h3 className="text-base font-black text-[#1A2244] leading-tight">{primaryTask.title}</h3>
                    {primaryTask.description && (
                      <p className="text-[10px] text-slate-500 font-medium">{primaryTask.description}</p>
                    )}
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-[9px] font-black text-green-600 bg-green-50 px-1.5 py-0.5 rounded-md uppercase tracking-widest">
                      +{primaryTask.readiness_impact}% Readiness
                    </span>
                    {primaryTask.duration_minutes && (
                      <span className="flex items-center gap-1 text-[9px] text-slate-400 font-bold">
                        <Clock className="w-2.5 h-2.5" />{primaryTask.duration_minutes} min
                      </span>
                    )}
                  </div>
                </div>
                <button
                  onClick={() => handleComplete(primaryTask.id)}
                  className="w-full mt-3 bg-[#5B7CFA] text-white py-2.5 rounded-xl text-[10px] font-black uppercase tracking-widest shadow-lg shadow-blue-500/20 hover:bg-[#4A6BEB] transition-all flex items-center justify-center gap-2"
                >
                  Mark Complete
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>
            ) : (
              <div className="glass-card p-6 text-center text-slate-400">
                <CheckCircle2 className="w-8 h-8 text-green-400 mx-auto mb-2" />
                <p className="text-xs font-bold">All primary tasks done!</p>
              </div>
            )}
          </div>

          {/* Remaining Tasks */}
          <div className="lg:col-span-7 flex flex-col space-y-2">
            <div className="flex items-center justify-between px-1">
              <h2 className="text-[11px] font-black text-slate-400 uppercase tracking-widest">Remaining Tasks</h2>
              <span className="text-[9px] font-bold text-slate-400">{remainingTasks.length} Pending</span>
            </div>

            <div className="space-y-1.5 overflow-y-auto no-scrollbar pr-1">
              {remainingTasks.map((task) => (
                <div
                  key={task.id}
                  className="glass-card p-2 flex items-center justify-between group hover:border-[#5B7CFA]/20 transition-all bg-white/50"
                >
                  <div className="flex items-center gap-2.5 min-w-0">
                    <div className="w-6 h-6 rounded-lg bg-slate-50 text-slate-400 flex items-center justify-center shrink-0 group-hover:bg-blue-50 group-hover:text-[#5B7CFA] transition-colors">
                      <Circle className="w-3.5 h-3.5" />
                    </div>
                    <div className="min-w-0">
                      <h3 className="text-[11px] font-black text-[#1A2244] truncate">{task.title}</h3>
                      <div className="flex items-center gap-2">
                        <span className="text-[8px] font-black text-green-600 uppercase tracking-widest">+{task.readiness_impact}%</span>
                        {task.duration_minutes && (
                          <span className="text-[8px] text-slate-400 font-bold uppercase tracking-widest">{task.duration_minutes} min</span>
                        )}
                      </div>
                    </div>
                  </div>
                  <button
                    onClick={() => handleComplete(task.id)}
                    className="p-1.5 bg-slate-50 text-slate-400 rounded-lg hover:bg-[#5B7CFA] hover:text-white transition-all shadow-sm"
                  >
                    <ArrowRight className="w-3 h-3" />
                  </button>
                </div>
              ))}

              {/* Completed Tasks */}
              <div className="pt-1">
                <button
                  onClick={() => setIsCompletedExpanded(!isCompletedExpanded)}
                  className="w-full flex items-center justify-between p-1.5 text-[9px] font-black text-slate-400 uppercase tracking-widest hover:text-slate-600 transition-colors"
                >
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="w-3 h-3 text-green-500" />
                    Completed Tasks ({completedTasks.length})
                  </div>
                  {isCompletedExpanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                </button>

                {isCompletedExpanded && (
                  <div className="mt-1.5 space-y-1.5">
                    {completedTasks.map((task) => (
                      <div
                        key={task.id}
                        className="glass-card p-2 flex items-center justify-between bg-slate-50/30 opacity-70"
                      >
                        <div className="flex items-center gap-2.5">
                          <CheckCircle2 className="w-3.5 h-3.5 text-green-500" />
                          <h3 className="text-[11px] font-bold text-slate-500 line-through">{task.title}</h3>
                        </div>
                        <span className="text-[8px] font-black text-green-600 uppercase tracking-widest">+{task.readiness_impact}%</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
