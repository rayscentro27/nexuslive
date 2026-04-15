import React from 'react';
import { BotAvatar, botConfig, BotType } from './BotAvatar';
import { Sparkles, ArrowRight, MessageSquare, Zap } from 'lucide-react';

export function Bots({ onInteract }: { onInteract?: () => void }) {
  return (
    <div className="p-6 space-y-8 max-w-7xl mx-auto h-full flex flex-col">
      <div className="space-y-1 shrink-0">
        <div className="flex items-center gap-2">
          <h2 className="text-2xl font-bold text-[#1A2244]">Nexus AI Bots</h2>
          <Sparkles className="w-5 h-5 text-amber-500 animate-pulse" />
        </div>
        <p className="text-xs text-slate-500 font-medium">Meet your dedicated team of AI specialists designed to scale your business.</p>
      </div>

      <div className="flex-1 overflow-y-auto scrollbar-hide pr-1">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {(Object.keys(botConfig) as BotType[]).map((type) => {
            const config = botConfig[type];
            return (
              <div key={type} className="glass-card p-6 space-y-6 group hover:border-[#5B7CFA]/30 transition-all">
                <div className="flex items-center gap-6">
                  <BotAvatar type={type} size="lg" />
                  <div className="space-y-1">
                    <h3 className="text-lg font-bold text-[#1A2244]">{config.name}</h3>
                    <p className="text-[10px] font-bold text-[#5B7CFA] uppercase tracking-widest">{config.role}</p>
                  </div>
                </div>

                <p className="text-xs text-slate-500 font-medium leading-relaxed">
                  {config.description}
                </p>

                <div className="pt-4 border-t border-slate-50 flex items-center justify-between">
                  <div className="flex gap-2">
                    <button className="p-2 bg-slate-50 rounded-lg text-slate-400 hover:text-[#5B7CFA] hover:bg-white transition-all">
                      <MessageSquare className="w-4 h-4" />
                    </button>
                    <button className="p-2 bg-slate-50 rounded-lg text-slate-400 hover:text-[#5B7CFA] hover:bg-white transition-all">
                      <Zap className="w-4 h-4" />
                    </button>
                  </div>
                  <button 
                    onClick={onInteract}
                    className="flex items-center gap-2 text-[10px] font-bold text-[#5B7CFA] hover:underline"
                  >
                    Interact <ArrowRight className="w-3 h-3" />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Hero Section */}
      <div className="glass-card p-8 bg-gradient-to-br from-[#5B7CFA] to-[#3A5EE5] border-none relative overflow-hidden shrink-0">
        <div className="absolute top-0 right-0 w-64 h-64 bg-white/10 rounded-full -mr-24 -mt-24 blur-3xl" />
        <div className="relative z-10 flex items-center justify-between">
          <div className="space-y-2">
            <h3 className="text-2xl font-black text-white">Need a custom bot?</h3>
            <p className="text-blue-100 text-sm font-medium max-w-md">Our AI engineers can build a specialized specialist for your unique business needs.</p>
            <button className="mt-4 px-6 py-2.5 bg-white text-[#5B7CFA] rounded-xl font-bold shadow-lg hover:bg-blue-50 transition-all text-sm">
              Contact AI Team
            </button>
          </div>
          <div className="hidden md:flex -space-x-4">
            {['dashboard', 'funding', 'setup'].map((type, i) => (
              <div key={type} className="w-20 h-20 rounded-2xl border-4 border-white/20 overflow-hidden shadow-2xl transform hover:-translate-y-2 transition-all" style={{ zIndex: 3 - i }}>
                <img 
                  src={botConfig[type as BotType].avatar} 
                  alt={type} 
                  className="w-full h-full object-cover bg-white" 
                  referrerPolicy="no-referrer"
                />
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
