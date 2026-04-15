import React, { useState } from 'react';
import { CheckCircle2, Circle, Play, ArrowRight, Clock, AlertCircle, Zap, ChevronDown, ChevronUp } from 'lucide-react';
import { cn } from '../lib/utils';

interface Task {
  id: string;
  title: string;
  duration: string;
  status: 'pending' | 'completed' | 'in-progress';
  priority: 'high' | 'medium' | 'low';
  description?: string;
  impact: string;
  isPrimary?: boolean;
}

const tasks: Task[] = [
  {
    id: '1',
    title: 'Review Your Credit Analysis',
    duration: '8 min',
    status: 'pending',
    priority: 'high',
    description: '5 dispute opportunities found in your latest report.',
    impact: '+5%'
  },
  {
    id: '2',
    title: 'Enter Your Business Details',
    duration: '5-10 min',
    status: 'in-progress',
    priority: 'high',
    description: '1 of 4 fields left to complete.',
    impact: '+8%',
    isPrimary: true
  },
  {
    id: '3',
    title: 'Watch Business Funding Guide',
    duration: '10 min',
    status: 'pending',
    priority: 'medium',
    impact: '+2%'
  },
  {
    id: '4',
    title: 'Upload Business Documents',
    duration: '5 min',
    status: 'pending',
    priority: 'high',
    description: '0 of 3 documents uploaded.',
    impact: '+4%'
  },
  {
    id: '5',
    title: 'Generate Dispute Letters',
    duration: '15 min',
    status: 'pending',
    priority: 'high',
    impact: '+6%'
  },
  {
    id: '6',
    title: 'LLC Formation Verified',
    duration: '20 min',
    status: 'completed',
    priority: 'high',
    impact: '+10%'
  },
  {
    id: '7',
    title: 'EIN Obtained',
    duration: '10 min',
    status: 'completed',
    priority: 'high',
    impact: '+5%'
  }
];

export function ActionCenter() {
  const [isCompletedExpanded, setIsCompletedExpanded] = useState(false);
  const progress = 38;

  const primaryTask = tasks.find(t => t.isPrimary);
  const remainingTasks = tasks.filter(t => !t.isPrimary && t.status !== 'completed');
  const completedTasks = tasks.filter(t => t.status === 'completed');

  return (
    <div className="p-3 max-w-6xl mx-auto space-y-3 h-full flex flex-col overflow-y-auto no-scrollbar">
      <div className="flex flex-col space-y-0.5 shrink-0">
        <h1 className="text-xl font-black text-[#1A2244]">Action Center</h1>
        <p className="text-[10px] text-slate-500 font-medium">The engine of your funding journey. Complete tasks to advance.</p>
      </div>

      {/* Progress Bar & Momentum - Reduced height by 50% */}
      <div className="glass-card p-2.5 space-y-1.5 shrink-0 bg-gradient-to-br from-white to-blue-50/30">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-blue-50 flex items-center justify-center text-[#5B7CFA]">
              <Zap className="w-3.5 h-3.5" />
            </div>
            <div>
              <span className="text-[7px] font-black text-slate-400 uppercase tracking-widest">Funding Momentum</span>
              <h2 className="text-[11px] font-black text-[#1A2244]">3 tasks left before funding unlock</h2>
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

      {/* Task Grid - 2 Column Structure */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-3 flex-1 min-h-0">
        {/* Left: Primary Task - Reduced height by ~25% */}
        <div className="lg:col-span-5 space-y-2">
          <h2 className="text-[11px] font-black text-slate-400 uppercase tracking-widest px-1">Next Best Action</h2>
          {primaryTask && (
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
                  <p className="text-[10px] text-slate-500 font-medium">{primaryTask.description}</p>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-[9px] font-black text-green-600 bg-green-50 px-1.5 py-0.5 rounded-md uppercase tracking-widest">{primaryTask.impact} Readiness</span>
                  <span className="flex items-center gap-1 text-[9px] text-slate-400 font-bold">
                    <Clock className="w-2.5 h-2.5" />
                    {primaryTask.duration}
                  </span>
                </div>
              </div>
              <button className="w-full mt-3 bg-[#5B7CFA] text-white py-2.5 rounded-xl text-[10px] font-black uppercase tracking-widest shadow-lg shadow-blue-500/20 hover:bg-[#4A6BEB] transition-all flex items-center justify-center gap-2">
                Continue Journey
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          )}
        </div>

        {/* Right: Remaining Tasks */}
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
                      <span className="text-[8px] font-black text-green-600 uppercase tracking-widest">{task.impact}</span>
                      <span className="text-[8px] text-slate-400 font-bold uppercase tracking-widest">{task.duration}</span>
                    </div>
                  </div>
                </div>
                <button className="p-1.5 bg-slate-50 text-slate-400 rounded-lg hover:bg-[#5B7CFA] hover:text-white transition-all shadow-sm">
                  <ArrowRight className="w-3 h-3" />
                </button>
              </div>
            ))}

            {/* Collapsible Completed Tasks */}
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
                <div className="mt-1.5 space-y-1.5 animate-in fade-in slide-in-from-top-1 duration-200">
                  {completedTasks.map((task) => (
                    <div 
                      key={task.id}
                      className="glass-card p-2 flex items-center justify-between bg-slate-50/30 opacity-70"
                    >
                      <div className="flex items-center gap-2.5">
                        <CheckCircle2 className="w-3.5 h-3.5 text-green-500" />
                        <h3 className="text-[11px] font-bold text-slate-500 line-through">{task.title}</h3>
                      </div>
                      <span className="text-[8px] font-black text-green-600 uppercase tracking-widest">{task.impact}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
