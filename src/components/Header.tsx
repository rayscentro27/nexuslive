import React from 'react';
import { Bell, Search, Video, Coins, Rocket } from 'lucide-react';

export function Header() {
  return (
    <header className="h-20 flex items-center justify-between px-8 sticky top-0 z-40 bg-white/80 backdrop-blur-md border-b border-slate-100">
      <div className="flex items-center gap-4 flex-1 max-w-xl">
        <div className="relative w-full">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input 
            type="text" 
            placeholder="Search anything..." 
            className="w-full bg-slate-50 border border-slate-100 rounded-2xl py-2.5 pl-11 pr-4 text-sm font-medium focus:outline-none focus:ring-4 focus:ring-blue-500/5 transition-all"
          />
        </div>
      </div>

      <div className="flex items-center gap-6">
        <div className="flex items-center gap-4 px-4 py-2 bg-slate-50 border border-slate-100 rounded-xl shadow-sm">
          <div className="flex items-center gap-2">
            <span className="text-sm font-bold text-[#1A2244]">3</span>
            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Ss</span>
          </div>
          <div className="w-px h-4 bg-slate-200" />
          <Video className="w-4 h-4 text-[#5B7CFA]" />
          <div className="w-px h-4 bg-slate-200" />
          <div className="flex items-center gap-2">
            <Coins className="w-4 h-4 text-amber-500" />
            <span className="text-sm font-bold text-[#1A2244]">1,290</span>
          </div>
          <div className="w-px h-4 bg-slate-200" />
          <Rocket className="w-4 h-4 text-[#5B7CFA]" />
        </div>

        <button className="relative p-2 text-slate-400 hover:text-[#5B7CFA] transition-colors">
          <Bell className="w-5 h-5" />
          <span className="absolute top-2 right-2 w-2 h-2 bg-[#5B7CFA] border-2 border-white rounded-full" />
        </button>

        <div className="flex items-center gap-3 pl-4 border-l border-slate-100">
          <div className="text-right">
            <p className="text-sm font-bold text-[#1A2244] leading-none">Michael Thompson</p>
            <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mt-1">Owner / Admin</p>
          </div>
          <div className="w-10 h-10 rounded-xl bg-[#C5C9F7] border-2 border-white shadow-sm overflow-hidden">
            <img 
              src="https://api.dicebear.com/7.x/notionists/svg?seed=Michael&backgroundColor=c5c9f7" 
              alt="Avatar" 
              className="w-full h-full object-cover"
              referrerPolicy="no-referrer"
            />
          </div>
        </div>
      </div>
    </header>
  );
}
