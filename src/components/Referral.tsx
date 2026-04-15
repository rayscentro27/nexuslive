import React from 'react';
import { 
  Users, 
  Copy, 
  QrCode, 
  TrendingUp, 
  DollarSign, 
  Mail, 
  MessageCircle, 
  Facebook, 
  MessageSquare, 
  ChevronRight,
  CheckCircle2,
  Clock,
  Zap,
  Award,
  ArrowUpRight
} from 'lucide-react';
import { cn } from '../lib/utils';
import { BotAvatar } from './BotAvatar';

const leaderboard = [
  { rank: 1, name: 'Mike Thompson', referrals: 8, earnings: '$1,540', avatar: 'Mike' },
  { rank: 2, name: 'Sarah Patel', referrals: 8, earnings: '$1,065', avatar: 'Sarah' },
  { rank: 3, name: 'Amanda Nguyen', referrals: 5, earnings: '$925', avatar: 'Amanda' },
];

const activity = [
  { name: 'John Carter', referrals: 3, date: 'Apr 4', status: 'Successful', amount: '$450', avatar: 'John' },
  { name: 'Jenny Lee', referrals: 8, date: 'Apr 1', status: 'Pending', amount: '$50', avatar: 'Jenny' },
  { name: 'Amanda Nguyen', referrals: 3, date: 'Apr 18', status: 'Registered', avatar: 'Amanda' },
];

export function Referral() {
  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto h-full flex flex-col">
      <div className="flex items-center justify-between shrink-0">
        <div className="space-y-0.5">
          <h2 className="text-2xl font-bold text-[#1A2244]">Refer & Earn</h2>
          <p className="text-xs text-slate-500 font-medium">Earn up to $550 for each referral</p>
        </div>
        <div className="flex items-center gap-3">
          <p className="text-slate-500 font-medium text-xs">Progress: <span className="text-[#1A2244] font-bold">42%</span></p>
          <div className="w-24 h-2 bg-nexus-100 rounded-full overflow-hidden shadow-inner">
            <div className="w-[42%] h-full bg-[#5B7CFA]" />
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto scrollbar-hide space-y-6 pr-1">
        {/* Hero Banner */}
        <div className="glass-card overflow-hidden relative min-h-[200px] group shadow-xl shrink-0">
          <img 
            src="https://picsum.photos/seed/referral-hero/1200/400" 
            alt="Referral Hero" 
            className="w-full h-full object-cover absolute inset-0 group-hover:scale-105 transition-transform duration-700"
            referrerPolicy="no-referrer"
          />
          <div className="absolute inset-0 bg-gradient-to-r from-[#1A2244]/40 to-transparent pointer-events-none" />
          <div className="absolute bottom-6 left-6 space-y-3 max-w-lg">
            <h3 className="text-2xl font-black text-white tracking-tight leading-tight">
              Invite your friends and <br />
              <span className="text-blue-400">earn $550</span> per referral
            </h3>
            <button className="bg-white text-[#1A2244] px-6 py-2.5 rounded-xl text-xs font-bold shadow-xl flex items-center gap-2 hover:bg-slate-50 transition-all">
              Invite Friends Now
              <ArrowUpRight className="w-4 h-4" />
            </button>
          </div>
          {/* Referral Bot */}
          <div className="absolute bottom-2 right-2 w-32 h-32 opacity-90 group-hover:scale-110 transition-transform duration-500">
            <BotAvatar type="referral" size="xl" className="bg-transparent shadow-none" />
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column: Link & Summary */}
          <div className="lg:col-span-2 space-y-6">
            {/* Share Link */}
            <div className="glass-card p-6 space-y-4">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-blue-50 flex items-center justify-center text-[#5B7CFA]">
                  <Users className="w-4 h-4" />
                </div>
                <h3 className="text-sm font-bold text-[#1A2244]">Share Your Referral Link</h3>
              </div>
              <div className="flex flex-col md:flex-row gap-3">
                <div className="flex-1 bg-slate-50 border border-slate-100 rounded-xl px-4 py-2.5 text-slate-600 font-medium text-xs flex items-center justify-between">
                  <span className="truncate">https://app.nexus.com/signup?ref=XYZ123</span>
                  <div className="flex gap-1.5">
                    <button className="p-1.5 hover:bg-slate-200 rounded-lg transition-colors"><Copy className="w-3.5 h-3.5" /></button>
                    <button className="p-1.5 hover:bg-slate-200 rounded-lg transition-colors"><QrCode className="w-3.5 h-3.5" /></button>
                  </div>
                </div>
                <button className="bg-[#5B7CFA] text-white px-6 py-2.5 rounded-xl text-xs font-bold shadow-lg shadow-blue-500/20 hover:bg-[#4A6BEB] transition-all">Copy Link</button>
              </div>
            </div>

            {/* Earnings Summary */}
            <div className="glass-card p-6 space-y-6">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-lg bg-green-50 flex items-center justify-center text-green-600">
                    <DollarSign className="w-4 h-4" />
                  </div>
                  <h3 className="font-bold text-[#1A2244] text-base">Earnings Summary</h3>
                </div>
                <ChevronRight className="w-4 h-4 text-slate-400" />
              </div>
              
              <div className="space-y-2">
                <p className="text-[8px] font-bold text-slate-400 uppercase tracking-widest">Total Earned</p>
                <p className="text-4xl font-black text-[#1A2244] tracking-tight">$1,540</p>
                <div className="w-full h-2 bg-nexus-100 rounded-full overflow-hidden mt-4">
                  <div className="w-3/4 h-full bg-gradient-to-r from-[#5B7CFA] to-[#3A5EE5]" />
                </div>
                <div className="flex justify-between text-[8px] font-bold text-slate-400 uppercase tracking-widest pt-1">
                  <span>0%</span>
                  <span>30%</span>
                  <span>50%</span>
                  <span>100%</span>
                </div>
              </div>

              <div className="grid grid-cols-3 gap-4 pt-6 border-t border-slate-100">
                <div className="space-y-1">
                  <p className="text-[8px] font-bold text-slate-500 uppercase tracking-widest">Referral</p>
                  <p className="text-lg font-black text-green-600">$975</p>
                  <p className="text-[8px] text-slate-400 font-bold">10 refs</p>
                </div>
                <div className="space-y-1">
                  <p className="text-[8px] font-bold text-slate-500 uppercase tracking-widest">Funding</p>
                  <p className="text-lg font-black text-green-600">$655</p>
                  <p className="text-[8px] text-slate-400 font-bold">$28k Funded</p>
                </div>
                <div className="space-y-1">
                  <p className="text-[8px] font-bold text-slate-500 uppercase tracking-widest">Unpaid</p>
                  <p className="text-lg font-black text-[#1A2244]">$250</p>
                  <button className="text-[8px] font-bold text-[#5B7CFA] uppercase tracking-widest hover:underline">Details</button>
                </div>
              </div>
            </div>
          </div>

          {/* Right Column: Program & Leaderboard */}
          <div className="space-y-6">
            {/* Program Info */}
            <div className="glass-card p-6 space-y-6">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-purple-50 flex items-center justify-center text-purple-600">
                  <Award className="w-4 h-4" />
                </div>
                <h3 className="text-sm font-bold text-[#1A2244]">Program</h3>
              </div>
              <div className="space-y-4">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-green-500" />
                    <p className="text-xs font-bold text-[#1A2244]">Referral Commission</p>
                  </div>
                  <p className="text-[10px] text-slate-500 pl-6 leading-relaxed">$75 per referral</p>
                </div>

                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-green-500" />
                    <p className="text-xs font-bold text-[#1A2244]">Funding Commission</p>
                  </div>
                  <p className="text-[10px] text-slate-500 pl-6 leading-relaxed">Earn 2% of funded amount</p>
                </div>
              </div>
              <button className="w-full py-2 bg-slate-50 text-[#1A2244] font-bold text-[10px] rounded-xl border border-slate-100 hover:bg-slate-100 transition-all">Milestones</button>
            </div>

            {/* Leaderboard */}
            <div className="glass-card p-6 space-y-6">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-amber-50 flex items-center justify-center text-amber-600">
                  <TrendingUp className="w-4 h-4" />
                </div>
                <h3 className="text-sm font-bold text-[#1A2244]">Leaderboard</h3>
              </div>
              <div className="space-y-4">
                {leaderboard.map((user) => (
                  <div key={user.rank} className="flex items-center gap-3 group cursor-pointer">
                    <div className={cn(
                      "w-6 h-6 rounded-full flex items-center justify-center text-[8px] font-black shadow-sm",
                      user.rank === 1 ? "bg-amber-100 text-amber-600" : "bg-slate-100 text-slate-600"
                    )}>
                      {user.rank}
                    </div>
                    <div className="w-10 h-10 rounded-xl bg-[#C5C9F7] overflow-hidden shrink-0 shadow-md group-hover:scale-105 transition-transform">
                      <img 
                        src={`https://api.dicebear.com/7.x/notionists/svg?seed=${user.avatar}&backgroundColor=c5c9f7`} 
                        alt={user.name} 
                        referrerPolicy="no-referrer"
                      />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-bold text-[#1A2244] truncate">{user.name}</p>
                      <p className="text-[8px] font-bold text-slate-400 uppercase tracking-widest">{user.referrals} refs • {user.earnings}</p>
                    </div>
                  </div>
                ))}
              </div>
              <button className="w-full py-2 bg-slate-50 text-[#1A2244] font-bold text-[10px] rounded-xl border border-slate-100 hover:bg-slate-100 transition-all">View All</button>
            </div>
          </div>
        </div>

        {/* Referral Activity */}
        <div className="glass-card overflow-hidden shrink-0">
          <div className="p-6 border-b border-slate-100 flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-slate-50 flex items-center justify-center text-slate-400">
              <Clock className="w-4 h-4" />
            </div>
            <h3 className="text-sm font-bold text-[#1A2244]">Referral Activity</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-slate-50/50 text-left">
                  <th className="px-6 py-3 text-[8px] font-bold text-slate-500 uppercase tracking-widest">Referred</th>
                  <th className="px-6 py-3 text-[8px] font-bold text-slate-500 uppercase tracking-widest text-center">Date</th>
                  <th className="px-6 py-3 text-[8px] font-bold text-slate-500 uppercase tracking-widest text-right">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50">
                {activity.map((item, idx) => (
                  <tr key={idx} className="hover:bg-slate-50/30 transition-colors group">
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-4">
                        <div className="w-10 h-10 rounded-xl bg-[#C5C9F7] overflow-hidden shrink-0 shadow-sm group-hover:scale-105 transition-transform">
                          <img 
                            src={`https://api.dicebear.com/7.x/notionists/svg?seed=${item.avatar}&backgroundColor=c5c9f7`} 
                            alt={item.name} 
                            referrerPolicy="no-referrer"
                          />
                        </div>
                        <div>
                          <p className="text-sm font-bold text-[#1A2244]">{item.name}</p>
                          <p className="text-[8px] font-bold text-slate-400 uppercase tracking-widest">{item.referrals} referrals</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-xs text-slate-600 text-center font-bold">{item.date}</td>
                    <td className="px-6 py-4 text-right">
                      <div className="space-y-0.5">
                        <div className="flex items-center justify-end gap-1.5">
                          {item.status === 'Successful' && <CheckCircle2 className="w-3 h-3 text-green-500" />}
                          {item.status === 'Pending' && <Clock className="w-3 h-3 text-amber-500" />}
                          <span className={cn(
                            "text-[8px] font-black uppercase tracking-widest",
                            item.status === 'Successful' ? "text-green-600" : 
                            item.status === 'Pending' ? "text-amber-600" : 
                            "text-slate-400"
                          )}>
                            {item.status}
                          </span>
                        </div>
                        {item.amount && <p className="text-sm font-black text-[#1A2244]">{item.amount}</p>}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Invite Friends Footer */}
        <div className="glass-card p-6 space-y-6 shrink-0">
          <div className="flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-blue-50 flex items-center justify-center text-[#5B7CFA]">
                <MessageSquare className="w-5 h-5" />
              </div>
              <h3 className="text-xl font-black text-[#1A2244]">Invite More Friends</h3>
            </div>
            <div className="flex items-center gap-4">
              <span className="text-[8px] font-bold text-slate-500 uppercase tracking-widest">Earn $550 per referral</span>
              <div className="flex gap-1.5">
                {[...Array(10)].map((_, i) => (
                  <div key={i} className={cn("w-5 h-5 rounded-full flex items-center justify-center text-[8px] font-black shadow-sm", i < 3 ? "bg-green-500 text-white" : "bg-slate-100 text-slate-400")}>
                    {i < 3 ? <CheckCircle2 className="w-3 h-3" /> : i + 1}
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
            <button className="bg-slate-50 text-[#1A2244] py-2.5 text-[10px] rounded-xl font-bold border border-slate-100 hover:bg-slate-100 transition-all">Email</button>
            <button className="bg-slate-50 text-[#1A2244] py-2.5 text-[10px] rounded-xl font-bold border border-slate-100 hover:bg-slate-100 transition-all">SMS</button>
            <button className="bg-slate-50 text-[#1A2244] py-2.5 text-[10px] rounded-xl font-bold border border-slate-100 hover:bg-slate-100 transition-all">Facebook</button>
            <button className="bg-slate-50 text-[#1A2244] py-2.5 text-[10px] rounded-xl font-bold border border-slate-100 hover:bg-slate-100 transition-all">Whatsapp</button>
            <button className="bg-slate-50 text-[#1A2244] py-2.5 text-[10px] rounded-xl font-bold border border-slate-100 hover:bg-slate-100 transition-all">Messenger</button>
            <button className="bg-[#5B7CFA] text-white py-2.5 text-[10px] rounded-xl font-black shadow-lg shadow-blue-500/20 hover:bg-[#4A6BEB] transition-all">Invite All</button>
          </div>
        </div>
      </div>
    </div>
  );
}
