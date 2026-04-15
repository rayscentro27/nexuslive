import React, { useState, useEffect } from 'react';
import { Cpu, Play, Pause, RotateCcw, Save, UserPlus, Search, Bot, Loader2 } from 'lucide-react';
import { cn } from '../../lib/utils';
import { getBotProfiles, BotProfile } from '../../lib/db';

export function AdminAIWorkforce() {
  const [bots, setBots] = useState<BotProfile[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getBotProfiles().then(({ data }) => {
      setBots(data);
      if (data.length > 0) setSelectedId(data[0].agent_key);
      setLoading(false);
    });
  }, []);

  const current = bots.find(b => b.agent_key === selectedId);

  return (
    <div className="p-8 space-y-8 bg-slate-50/50 min-h-full text-slate-600">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-black text-[#1A2244] tracking-tight">AI Workforce</h1>
          <p className="text-slate-500 font-medium mt-1 text-sm">Manage autonomous employees, edit prompts, and monitor performance.</p>
        </div>
        <button className="px-6 py-2 rounded-xl bg-[#5B7CFA] text-white text-xs font-black uppercase tracking-widest shadow-lg shadow-blue-500/20 hover:bg-[#4A6BEB] transition-all flex items-center gap-2">
          <UserPlus className="w-4 h-4" /> Deploy New AI
        </button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-24"><Loader2 className="w-6 h-6 text-slate-300 animate-spin" /></div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          {/* Bot List */}
          <div className="lg:col-span-4 space-y-4">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
              <input type="text" placeholder="Search workforce..."
                className="w-full bg-white border border-slate-200 rounded-xl py-2 pl-10 pr-4 text-xs font-medium text-slate-600 focus:outline-none focus:border-[#5B7CFA]/50 shadow-sm" />
            </div>
            <div className="space-y-3">
              {bots.map(bot => (
                <button key={bot.agent_key} onClick={() => setSelectedId(bot.agent_key)}
                  className={cn(
                    "w-full p-4 rounded-2xl border transition-all text-left relative overflow-hidden shadow-sm",
                    selectedId === bot.agent_key
                      ? "bg-[#5B7CFA] border-[#5B7CFA] shadow-lg shadow-blue-500/20"
                      : "bg-white border-slate-200 hover:border-slate-300"
                  )}>
                  {selectedId === bot.agent_key && (
                    <div className="absolute top-0 right-0 w-24 h-24 bg-white/10 rounded-full -mr-12 -mt-12 blur-2xl" />
                  )}
                  <div className="relative z-10 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className={cn("w-10 h-10 rounded-xl flex items-center justify-center",
                        selectedId === bot.agent_key ? "bg-white/20 text-white" : "bg-slate-50 text-[#5B7CFA]")}>
                        <Bot className="w-6 h-6" />
                      </div>
                      <div>
                        <h4 className={cn("text-sm font-black", selectedId === bot.agent_key ? "text-white" : "text-[#1A2244]")}>{bot.name}</h4>
                        <p className={cn("text-[9px] font-bold uppercase tracking-widest mt-0.5",
                          selectedId === bot.agent_key ? "text-blue-100" : "text-slate-400")}>{bot.role}</p>
                      </div>
                    </div>
                    <div className={cn("w-2 h-2 rounded-full",
                      bot.status === 'active' ? (selectedId === bot.agent_key ? "bg-white" : "bg-green-500") :
                      bot.status === 'idle' ? "bg-amber-400" : "bg-slate-300")} />
                  </div>
                </button>
              ))}
              {bots.length === 0 && (
                <p className="text-[10px] font-bold text-slate-400 text-center py-8 uppercase tracking-widest">No bots configured</p>
              )}
            </div>
          </div>

          {/* Control Panel */}
          <div className="lg:col-span-8">
            {current ? (
              <div className="bg-white border border-slate-200 rounded-3xl overflow-hidden shadow-sm">
                <div className="p-6 border-b border-slate-100 flex items-center justify-between bg-slate-50/30">
                  <div className="flex items-center gap-4">
                    <div className="w-12 h-12 rounded-2xl bg-blue-50 flex items-center justify-center text-[#5B7CFA]">
                      <Bot className="w-7 h-7" />
                    </div>
                    <div>
                      <h3 className="text-xl font-black text-[#1A2244]">{current.name}</h3>
                      <p className="text-[10px] font-black text-[#5B7CFA] uppercase tracking-widest mt-1">{current.role}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <button className="p-2.5 bg-slate-50 text-slate-400 rounded-xl hover:text-[#1A2244] border border-slate-200 transition-all">
                      <Pause className="w-5 h-5" />
                    </button>
                    <button className="p-2.5 bg-slate-50 text-slate-400 rounded-xl hover:text-[#1A2244] border border-slate-200 transition-all">
                      <RotateCcw className="w-5 h-5" />
                    </button>
                    <button className="p-2.5 bg-[#5B7CFA] text-white rounded-xl hover:bg-[#4A6BEB] shadow-lg shadow-blue-500/20 transition-all">
                      <Save className="w-5 h-5" />
                    </button>
                  </div>
                </div>
                <div className="p-8 space-y-8">
                  <div className="grid grid-cols-3 gap-6">
                    <div className="p-4 rounded-2xl bg-slate-50 border border-slate-100">
                      <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest">Efficiency</p>
                      <h4 className="text-xl font-black text-green-600 mt-1">
                        {current.efficiency != null ? `${current.efficiency}%` : '—'}
                      </h4>
                    </div>
                    <div className="p-4 rounded-2xl bg-slate-50 border border-slate-100">
                      <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest">Status</p>
                      <h4 className={cn("text-xl font-black mt-1 capitalize",
                        current.status === 'active' ? "text-green-600" :
                        current.status === 'idle' ? "text-amber-600" : "text-slate-400")}>
                        {current.status}
                      </h4>
                    </div>
                    <div className="p-4 rounded-2xl bg-slate-50 border border-slate-100">
                      <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest">Division</p>
                      <h4 className="text-xl font-black text-[#1A2244] mt-1 text-sm">{current.division ?? '—'}</h4>
                    </div>
                  </div>

                  {current.description && (
                    <div className="space-y-2">
                      <h4 className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Description</h4>
                      <p className="text-sm text-slate-500 leading-relaxed bg-slate-50 p-4 rounded-2xl border border-slate-100 italic">
                        "{current.description}"
                      </p>
                    </div>
                  )}

                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <h4 className="text-[10px] font-black text-slate-400 uppercase tracking-widest">System Prompt</h4>
                      <span className="text-[9px] font-bold text-[#5B7CFA] uppercase tracking-widest">Editable</span>
                    </div>
                    <textarea
                      className="w-full h-48 bg-white border border-slate-200 rounded-2xl p-6 text-xs font-mono text-slate-600 focus:outline-none focus:border-[#5B7CFA]/50 transition-all leading-relaxed no-scrollbar shadow-inner"
                      defaultValue={`You are ${current.name}, the ${current.role} for Nexus.\n\nYour mission is to help clients achieve their funding goals.\n\nGuidelines:\n- Professional yet encouraging\n- Data-driven and precise\n- Action-oriented`}
                    />
                  </div>
                </div>
              </div>
            ) : (
              <div className="bg-white border border-slate-200 rounded-3xl flex items-center justify-center min-h-[400px]">
                <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Select a bot to manage</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
