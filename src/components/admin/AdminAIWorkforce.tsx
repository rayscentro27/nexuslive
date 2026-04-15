import React, { useState } from 'react';
import { 
  Cpu, 
  MessageSquare, 
  Settings, 
  Play, 
  Pause, 
  RotateCcw, 
  Save,
  UserPlus,
  Activity,
  Zap,
  ShieldCheck,
  Search,
  MoreHorizontal,
  ChevronRight,
  Bot
} from 'lucide-react';
import { cn } from '../../lib/utils';

export function AdminAIWorkforce() {
  const [selectedAI, setSelectedAI] = useState('credit-ai');

  const aiEmployees = [
    { id: 'credit-ai', name: 'Credit AI', role: 'Credit Optimization', status: 'active', efficiency: '98.2%', tasks: 142, description: 'Analyzes credit reports and generates dispute letters automatically.' },
    { id: 'funding-ai', name: 'Funding AI', role: 'Capital Strategy', status: 'active', efficiency: '94.5%', tasks: 84, description: 'Matches clients with funding products based on readiness score.' },
    { id: 'setup-ai', name: 'Setup AI', role: 'Business Formation', status: 'active', efficiency: '99.1%', tasks: 215, description: 'Handles LLC filings, EIN applications, and bank setup workflows.' },
    { id: 'trading-ai', name: 'Trading AI', role: 'Market Analysis', status: 'idle', efficiency: '92.8%', tasks: 0, description: 'Monitors market signals and executes trades based on approved strategies.' },
  ];

  const currentAI = aiEmployees.find(ai => ai.id === selectedAI);

  return (
    <div className="p-8 space-y-8 bg-slate-50/50 min-h-full text-slate-600">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-black text-[#1A2244] tracking-tight">AI Workforce</h1>
          <p className="text-slate-500 font-medium mt-1 text-sm">Manage autonomous employees, edit prompts, and monitor performance.</p>
        </div>
        <button className="px-6 py-2 rounded-xl bg-[#5B7CFA] text-white text-xs font-black uppercase tracking-widest shadow-lg shadow-blue-500/20 hover:bg-[#4A6BEB] transition-all flex items-center gap-2">
          <UserPlus className="w-4 h-4" />
          Deploy New AI
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* AI List */}
        <div className="lg:col-span-4 space-y-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input 
              type="text" 
              placeholder="Search workforce..." 
              className="w-full bg-white border border-slate-200 rounded-xl py-2 pl-10 pr-4 text-xs font-medium text-slate-600 focus:outline-none focus:border-[#5B7CFA]/50 transition-all shadow-sm"
            />
          </div>
          
          <div className="space-y-3">
            {aiEmployees.map((ai) => (
              <button
                key={ai.id}
                onClick={() => setSelectedAI(ai.id)}
                className={cn(
                  "w-full p-4 rounded-2xl border transition-all text-left group relative overflow-hidden shadow-sm",
                  selectedAI === ai.id 
                    ? "bg-[#5B7CFA] border-[#5B7CFA] shadow-lg shadow-blue-500/20" 
                    : "bg-white border-slate-200 hover:border-slate-300"
                )}
              >
                {selectedAI === ai.id && (
                  <div className="absolute top-0 right-0 w-24 h-24 bg-white/10 rounded-full -mr-12 -mt-12 blur-2xl" />
                )}
                <div className="relative z-10 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className={cn(
                      "w-10 h-10 rounded-xl flex items-center justify-center",
                      selectedAI === ai.id ? "bg-white/20 text-white" : "bg-slate-50 text-[#5B7CFA]"
                    )}>
                      <Bot className="w-6 h-6" />
                    </div>
                    <div>
                      <h4 className={cn("text-sm font-black", selectedAI === ai.id ? "text-white" : "text-[#1A2244]")}>{ai.name}</h4>
                      <p className={cn("text-[9px] font-bold uppercase tracking-widest mt-0.5", selectedAI === ai.id ? "text-blue-100" : "text-slate-400")}>{ai.role}</p>
                    </div>
                  </div>
                  <div className={cn(
                    "w-2 h-2 rounded-full",
                    ai.status === 'active' ? (selectedAI === ai.id ? "bg-white" : "bg-green-500") : "bg-slate-300"
                  )} />
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* AI Control Panel */}
        <div className="lg:col-span-8 space-y-8">
          {currentAI && (
            <div className="bg-white border border-slate-200 rounded-3xl overflow-hidden flex flex-col shadow-sm">
              <div className="p-6 border-b border-slate-100 flex items-center justify-between bg-slate-50/30">
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 rounded-2xl bg-blue-50 flex items-center justify-center text-[#5B7CFA] shadow-inner">
                    <Bot className="w-7 h-7" />
                  </div>
                  <div>
                    <h3 className="text-xl font-black text-[#1A2244] leading-none">{currentAI.name}</h3>
                    <p className="text-[10px] font-black text-[#5B7CFA] uppercase tracking-widest mt-1.5">{currentAI.role}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button className="p-2.5 bg-slate-50 text-slate-400 rounded-xl hover:text-[#1A2244] transition-all border border-slate-200">
                    <Pause className="w-5 h-5" />
                  </button>
                  <button className="p-2.5 bg-slate-50 text-slate-400 rounded-xl hover:text-[#1A2244] transition-all border border-slate-200">
                    <RotateCcw className="w-5 h-5" />
                  </button>
                  <button className="p-2.5 bg-[#5B7CFA] text-white rounded-xl hover:bg-[#4A6BEB] transition-all shadow-lg shadow-blue-500/20">
                    <Save className="w-5 h-5" />
                  </button>
                </div>
              </div>

              <div className="p-8 space-y-8">
                {/* Performance Stats */}
                <div className="grid grid-cols-3 gap-6">
                  <div className="p-4 rounded-2xl bg-slate-50 border border-slate-100">
                    <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest">Efficiency</p>
                    <h4 className="text-xl font-black text-green-600 mt-1">{currentAI.efficiency}</h4>
                  </div>
                  <div className="p-4 rounded-2xl bg-slate-50 border border-slate-100">
                    <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest">Tasks Completed</p>
                    <h4 className="text-xl font-black text-[#1A2244] mt-1">{currentAI.tasks}</h4>
                  </div>
                  <div className="p-4 rounded-2xl bg-slate-50 border border-slate-100">
                    <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest">System Load</p>
                    <h4 className="text-xl font-black text-[#5B7CFA] mt-1">42%</h4>
                  </div>
                </div>

                {/* Description */}
                <div className="space-y-2">
                  <h4 className="text-[10px] font-black text-slate-400 uppercase tracking-widest">AI Description</h4>
                  <p className="text-sm text-slate-500 leading-relaxed bg-slate-50 p-4 rounded-2xl border border-slate-100 italic">
                    "{currentAI.description}"
                  </p>
                </div>

                {/* Prompt Editor */}
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <h4 className="text-[10px] font-black text-slate-400 uppercase tracking-widest">System Prompt (Personality & Logic)</h4>
                    <span className="text-[9px] font-bold text-[#5B7CFA] uppercase tracking-widest">v4.2.1 Stable</span>
                  </div>
                  <div className="relative group">
                    <textarea 
                      className="w-full h-64 bg-white border border-slate-200 rounded-2xl p-6 text-xs font-mono text-slate-600 focus:outline-none focus:border-[#5B7CFA]/50 transition-all leading-relaxed no-scrollbar shadow-inner"
                      defaultValue={`You are ${currentAI.name}, the ${currentAI.role} for Nexus. 

Your core mission is to assist clients in the ${currentAI.role} phase of their funding journey. 

TONE GUIDELINES:
- Professional yet encouraging
- Data-driven and precise
- Action-oriented

LOGIC PARAMETERS:
- Always check client readiness score before suggesting funding products
- If readiness < 70%, prioritize setup and credit tasks
- Use technical financial terminology but explain simply if asked`}
                    />
                    <div className="absolute bottom-4 right-4 flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                      <span className="text-[9px] font-bold text-slate-400 uppercase tracking-widest">1,240 tokens</span>
                    </div>
                  </div>
                </div>

                {/* Recent Activity Logs */}
                <div className="space-y-4">
                  <h4 className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Recent Activity Logs</h4>
                  <div className="space-y-2">
                    {[
                      { time: '12:42:05', event: 'Processed credit report for Marcus Chen', status: 'success' },
                      { time: '12:38:12', event: 'Generated dispute letter #42-B', status: 'success' },
                      { time: '12:15:44', event: 'System sync with TransUnion API', status: 'warning' },
                    ].map((log, i) => (
                      <div key={i} className="flex items-center justify-between p-3 rounded-xl bg-slate-50 border border-slate-100 text-[10px]">
                        <div className="flex items-center gap-3">
                          <span className="font-mono text-slate-400">{log.time}</span>
                          <span className="font-bold text-slate-600">{log.event}</span>
                        </div>
                        <span className={cn(
                          "font-black uppercase tracking-widest",
                          log.status === 'success' ? "text-green-600" : "text-amber-600"
                        )}>{log.status}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
