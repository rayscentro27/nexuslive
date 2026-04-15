import React from 'react';
import { 
  Bell, 
  Search, 
  Command, 
  Activity, 
  ShieldCheck, 
  Globe,
  ChevronDown
} from 'lucide-react';

export function AdminHeader() {
  return (
    <header className="h-16 bg-white border-b border-slate-200 flex items-center justify-between px-8 sticky top-0 z-40">
      <div className="flex items-center gap-8">
        <div className="relative group">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 group-focus-within:text-[#5B7CFA] transition-colors" />
          <input 
            type="text" 
            placeholder="Search system, clients, or AI logs..." 
            className="bg-slate-50 border border-slate-200 rounded-xl py-2 pl-10 pr-12 text-xs font-medium text-slate-600 focus:outline-none focus:ring-2 focus:ring-[#5B7CFA]/20 focus:border-[#5B7CFA]/50 w-80 transition-all"
          />
          <div className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-1 px-1.5 py-0.5 rounded bg-white border border-slate-200">
            <Command className="w-2.5 h-2.5 text-slate-400" />
            <span className="text-[9px] font-black text-slate-400">K</span>
          </div>
        </div>

        <div className="flex items-center gap-6 border-l border-slate-200 pl-8">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
            <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest">System Live</span>
          </div>
          <div className="flex items-center gap-2">
            <Activity className="w-4 h-4 text-[#5B7CFA]" />
            <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest">98.2% Efficiency</span>
          </div>
        </div>
      </div>

      <div className="flex items-center gap-4">
        <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-50 border border-slate-200">
          <Globe className="w-3.5 h-3.5 text-slate-400" />
          <span className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Production</span>
        </div>

        <button className="p-2.5 text-slate-400 hover:text-[#1A2244] hover:bg-slate-50 rounded-xl transition-all relative">
          <Bell className="w-5 h-5" />
          <span className="absolute top-2.5 right-2.5 w-2 h-2 bg-[#5B7CFA] rounded-full border-2 border-white" />
        </button>

        <div className="h-8 w-[1px] bg-slate-200 mx-2" />

        <button className="flex items-center gap-3 pl-2 group">
          <div className="text-right">
            <p className="text-xs font-black text-[#1A2244] leading-none">Admin Root</p>
            <p className="text-[9px] font-bold text-[#5B7CFA] uppercase tracking-widest mt-1">Superuser</p>
          </div>
          <div className="w-10 h-10 rounded-xl bg-slate-100 border border-slate-200 overflow-hidden group-hover:border-[#5B7CFA] transition-all">
            <img src="https://api.dicebear.com/7.x/avataaars/svg?seed=Admin" alt="Admin" />
          </div>
          <ChevronDown className="w-4 h-4 text-slate-400 group-hover:text-[#1A2244] transition-colors" />
        </button>
      </div>
    </header>
  );
}
