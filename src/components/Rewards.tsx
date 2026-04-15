import React from 'react';
import { StylizedIcon } from './StylizedIcon';
import { motion } from 'motion/react';
import { cn } from '../lib/utils';
import { Trophy, Star, Gift, Award, Scroll, CreditCard as CardIcon, ChevronRight, Zap } from 'lucide-react';

const achievements = [
  { id: 1, title: 'First Funding', desc: 'Successfully applied for your first business grant.', icon: 'cup', points: 500, status: 'completed' },
  { id: 2, title: 'Network Growth', desc: 'Referred 5 friends to the Nexus platform.', icon: 'gift', points: 250, status: 'in-progress', progress: 60 },
  { id: 3, title: 'Strategy Master', desc: 'Completed all AI advisor training modules.', icon: 'scroll', points: 1000, status: 'locked' },
  { id: 4, title: 'Top Trader', desc: 'Achieved a 70% win rate in the Trading Lab.', icon: 'star-trophy', points: 750, status: 'completed' },
  { id: 5, title: 'Business Pro', desc: 'Verified all business formation documents.', icon: 'award', points: 300, status: 'completed' },
  { id: 6, title: 'Credit King', desc: 'Reached a credit score of 750+.', icon: 'card', points: 500, status: 'in-progress', progress: 85 },
];

export function Rewards() {
  return (
    <div className="p-6 space-y-8 max-w-7xl mx-auto h-full flex flex-col">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 shrink-0">
        <div className="space-y-1">
          <h2 className="text-3xl font-black text-[#1A2244] tracking-tight">Nexus Rewards</h2>
          <p className="text-sm text-slate-500 font-medium">Earn points and unlock exclusive business perks.</p>
        </div>
        <div className="flex items-center gap-4 bg-white p-2 rounded-2xl shadow-sm border border-slate-100">
          <div className="flex items-center gap-2 px-4 py-2 bg-amber-50 rounded-xl">
            <Star className="w-5 h-5 text-amber-500 fill-amber-500" />
            <span className="text-xl font-black text-amber-600">3,450</span>
          </div>
          <button className="bg-[#5B7CFA] text-white px-6 py-2.5 rounded-xl font-bold text-sm shadow-lg shadow-blue-500/20 hover:bg-[#4A6BEB] transition-all">
            Redeem
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto scrollbar-hide space-y-8 pr-1">
        {/* Featured Reward */}
        <div className="glass-card p-8 bg-gradient-to-br from-[#1A2244] to-[#2D3748] text-white relative overflow-hidden shrink-0">
          <div className="absolute top-0 right-0 w-96 h-96 bg-blue-500/10 rounded-full -mr-32 -mt-32 blur-3xl" />
          <div className="relative z-10 flex flex-col md:flex-row items-center gap-8">
            <div className="shrink-0">
              <motion.div
                animate={{ y: [0, -10, 0] }}
                transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
              >
                <StylizedIcon name="star-trophy" size="xl" className="drop-shadow-[0_20px_40px_rgba(251,191,36,0.3)]" />
              </motion.div>
            </div>
            <div className="space-y-4 text-center md:text-left">
              <div className="space-y-1">
                <span className="px-3 py-1 bg-blue-500/20 text-blue-300 text-[10px] font-black uppercase tracking-widest rounded-full border border-blue-500/30">New Milestone</span>
                <h3 className="text-3xl font-black tracking-tight">Elite Founder Status</h3>
                <p className="text-slate-400 text-sm max-w-md">You're only 550 points away from unlocking Elite status. Get priority access to venture capital networks and zero-fee trading.</p>
              </div>
              <div className="flex flex-wrap justify-center md:justify-start gap-3">
                <div className="flex items-center gap-2 px-4 py-2 bg-white/5 rounded-xl border border-white/10">
                  <Zap className="w-4 h-4 text-amber-400" />
                  <span className="text-xs font-bold">2x Points Active</span>
                </div>
                <div className="flex items-center gap-2 px-4 py-2 bg-white/5 rounded-xl border border-white/10">
                  <Trophy className="w-4 h-4 text-blue-400" />
                  <span className="text-xs font-bold">Rank #12 in GA</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Achievements Grid */}
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <h3 className="text-xl font-bold text-[#1A2244]">Achievements</h3>
            <div className="flex gap-2">
              {['All', 'Completed', 'Locked'].map((filter) => (
                <button key={filter} className={cn(
                  "px-4 py-1.5 rounded-xl text-[10px] font-bold uppercase tracking-widest transition-all",
                  filter === 'All' ? "bg-[#1A2244] text-white" : "bg-slate-100 text-slate-500 hover:bg-slate-200"
                )}>
                  {filter}
                </button>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {achievements.map((item) => (
              <motion.div
                key={item.id}
                whileHover={{ y: -5 }}
                className={cn(
                  "glass-card p-6 flex flex-col gap-4 group transition-all",
                  item.status === 'locked' && "opacity-60 grayscale"
                )}
              >
                <div className="flex items-start justify-between">
                  <div className="p-2 bg-slate-50 rounded-2xl group-hover:bg-white transition-all">
                    <StylizedIcon name={item.icon as any} size="md" />
                  </div>
                  <div className="flex flex-col items-end">
                    <span className="text-[10px] font-black text-amber-600 bg-amber-50 px-2 py-1 rounded-lg">+{item.points} PTS</span>
                    {item.status === 'completed' && (
                      <span className="mt-2 text-[8px] font-black text-green-600 uppercase tracking-widest">Unlocked</span>
                    )}
                  </div>
                </div>
                
                <div className="space-y-1">
                  <h4 className="font-black text-[#1A2244] text-lg">{item.title}</h4>
                  <p className="text-xs text-slate-500 font-medium leading-relaxed">{item.desc}</p>
                </div>

                {item.status === 'in-progress' && (
                  <div className="space-y-2 mt-2">
                    <div className="flex justify-between text-[10px] font-bold text-slate-400 uppercase tracking-widest">
                      <span>Progress</span>
                      <span>{item.progress}%</span>
                    </div>
                    <div className="w-full h-2 bg-slate-100 rounded-full overflow-hidden">
                      <motion.div 
                        initial={{ width: 0 }}
                        animate={{ width: `${item.progress}%` }}
                        className="h-full bg-[#5B7CFA]" 
                      />
                    </div>
                  </div>
                )}

                {item.status === 'locked' ? (
                  <button className="mt-auto w-full py-2.5 bg-slate-100 text-slate-400 font-bold text-xs rounded-xl cursor-not-allowed">
                    Locked
                  </button>
                ) : (
                  <button className="mt-auto w-full py-2.5 bg-slate-50 text-[#5B7CFA] font-bold text-xs rounded-xl border border-slate-100 group-hover:bg-[#5B7CFA] group-hover:text-white transition-all flex items-center justify-center gap-2">
                    {item.status === 'completed' ? 'View Details' : 'Continue'}
                    <ChevronRight className="w-4 h-4" />
                  </button>
                )}
              </motion.div>
            ))}
          </div>
        </div>

        {/* Rewards Shop Preview */}
        <div className="glass-card p-6 space-y-6">
          <div className="flex items-center justify-between">
            <h3 className="text-xl font-bold text-[#1A2244]">Redeem Perks</h3>
            <button className="text-sm font-bold text-[#5B7CFA] hover:underline">View Shop</button>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {[
              { title: '0% Funding Fee', cost: 5000, icon: CardIcon, color: 'text-blue-500', bg: 'bg-blue-50' },
              { title: 'Priority AI Support', cost: 2500, icon: Zap, color: 'text-amber-500', bg: 'bg-amber-50' },
            ].map((perk, i) => (
              <div key={i} className="flex items-center justify-between p-4 bg-slate-50 rounded-2xl border border-slate-100 hover:border-blue-200 transition-all cursor-pointer group">
                <div className="flex items-center gap-4">
                  <div className={cn("w-12 h-12 rounded-xl flex items-center justify-center", perk.bg)}>
                    <perk.icon className={cn("w-6 h-6", perk.color)} />
                  </div>
                  <div>
                    <p className="font-bold text-[#1A2244]">{perk.title}</p>
                    <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">{perk.cost} Points</p>
                  </div>
                </div>
                <button className="p-2 bg-white rounded-xl shadow-sm border border-slate-100 group-hover:bg-blue-500 group-hover:text-white transition-all">
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
