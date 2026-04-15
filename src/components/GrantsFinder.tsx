import React from 'react';
import { 
  Search, 
  Filter, 
  Heart, 
  Code, 
  Plus, 
  Zap, 
  Building2, 
  Users, 
  Globe,
  ChevronRight,
  Bot,
  MessageSquare,
  MessageCircle,
  Mail,
  Facebook,
  CheckCircle2,
  Clock,
  Lock
} from 'lucide-react';
import { cn } from '../lib/utils';
import { BotAvatar } from './BotAvatar';

const grants = [
  { id: 1, title: 'Women Entrepreneurs Fund', amount: 'Up to $25,000', status: 'Eligible', date: 'Apr 15, 2024', location: 'Nationwide', image: 'idea' },
  { id: 2, title: 'Small Business Growth Grant', amount: 'Up to $50,000', status: 'Eligible', date: 'Apr 30, 2024', location: 'Nationwide', image: 'growth' },
  { id: 3, title: 'Minority Business Initiative', amount: '$15,000', status: 'In Review', date: 'Mar 25, 2024', location: 'Nationwide', image: 'business' },
  { id: 4, title: 'InnovateTech Startup Grant', amount: 'Up to $100,000', status: 'Not Eligible', date: 'Apr 10, 2024', location: 'Contents', image: 'tech' },
];

const opportunities = [
  { title: 'Green Energy Innovation Grant', amount: '$40,000', date: 'Mar 25, 2024', status: 'In-Progress' },
  { title: 'Local Business Relief Support', amount: 'Up to $20,000', date: 'Apr 3, 2024', status: 'Registered' },
  { title: 'TechAdvance R&D Grant', amount: '$75,000', date: 'Apr 15, 2024', status: 'Pending' },
];

export function GrantsFinder() {
  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto h-full flex flex-col">
      <div className="flex items-center justify-between shrink-0">
        <div className="space-y-0.5">
          <h2 className="text-2xl font-bold text-[#1A2244]">Grants Finder</h2>
          <p className="text-xs text-slate-500 font-medium">Discover and apply for grants to grow your business.</p>
        </div>
        <button className="bg-[#5B7CFA] text-white px-6 py-2 rounded-xl text-xs font-bold shadow-lg shadow-blue-500/20 hover:bg-[#4A6BEB] transition-all flex items-center gap-2">
          <Plus className="w-4 h-4" />
          Save Search
        </button>
      </div>

      <div className="flex-1 overflow-y-auto scrollbar-hide space-y-6 pr-1">
        {/* Hero Banner */}
        <div className="glass-card p-6 flex flex-col md:flex-row items-center justify-between bg-gradient-to-br from-blue-50 to-purple-50 border-slate-100 overflow-hidden relative shrink-0">
          <div className="space-y-4 relative z-10 max-w-2xl">
            <h3 className="text-2xl font-black text-[#1A2244] leading-tight">
              30 new grant opportunities found <br />
              <span className="text-[#5B7CFA]">for ACE Resources LLC</span>
            </h3>
            <p className="text-xs text-slate-500 font-medium leading-relaxed">Based on your business profile and funding needs, we've identified high-potential grants you qualify for.</p>
            <div className="flex flex-wrap gap-2">
              <span className="px-3 py-1 rounded-lg bg-[#5B7CFA] text-white text-[8px] font-bold uppercase tracking-widest">All</span>
              <span className="px-3 py-1 rounded-lg bg-white text-slate-600 text-[8px] font-bold uppercase tracking-widest border border-slate-100 shadow-sm">Startup</span>
              <span className="px-3 py-1 rounded-lg bg-white text-slate-600 text-[8px] font-bold uppercase tracking-widest border border-slate-100 shadow-sm">Minority</span>
              <span className="px-3 py-1 rounded-lg bg-white text-slate-600 text-[8px] font-bold uppercase tracking-widest border border-slate-100 shadow-sm">Women</span>
              <button className="flex items-center gap-1.5 px-3 py-1 rounded-lg bg-white text-[#5B7CFA] text-[8px] font-bold uppercase tracking-widest border border-slate-100 shadow-sm">
                Filters <Filter className="w-2.5 h-2.5" />
              </button>
            </div>
          </div>
          <div className="w-32 h-32 relative z-10 mt-4 md:mt-0">
            <BotAvatar type="grants" size="xl" className="bg-transparent shadow-none" />
          </div>
        </div>

        {/* Search Bar */}
        <div className="flex gap-3 shrink-0">
          <div className="relative flex-1">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input 
              type="text" 
              placeholder="Search grants..." 
              className="w-full bg-white border border-slate-200 rounded-xl py-2.5 pl-10 pr-4 text-xs font-medium focus:outline-none focus:ring-4 focus:ring-blue-500/5 transition-all shadow-sm"
            />
          </div>
          <button className="p-2.5 bg-white border border-slate-200 text-slate-400 hover:text-[#5B7CFA] rounded-xl shadow-sm transition-all"><Heart className="w-5 h-5" /></button>
          <button className="px-4 py-2.5 bg-white border border-slate-200 text-slate-700 hover:text-[#5B7CFA] flex items-center gap-2 rounded-xl shadow-sm transition-all">
            <Code className="w-4 h-4" />
            <span className="text-xs font-bold">Code</span>
          </button>
        </div>

        {/* Recommended Grants Grid */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-bold text-[#1A2244]">Recommended Grants</h3>
            <span className="text-[10px] text-slate-400 font-bold uppercase tracking-widest">30 results</span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {grants.map((grant) => (
              <div key={grant.id} className="glass-card p-4 flex gap-4 group hover:border-[#5B7CFA]/30 transition-all">
                <div className="w-24 h-24 rounded-xl bg-[#C5C9F7] overflow-hidden shrink-0 relative shadow-md">
                  <img 
                    src={`https://api.dicebear.com/7.x/notionists/svg?seed=${grant.image}&backgroundColor=c5c9f7`} 
                    alt={grant.title} 
                    className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-500"
                  />
                  <div className="absolute top-1.5 right-1.5 p-1 bg-white/90 backdrop-blur-sm rounded-md shadow-sm">
                    <Heart className="w-3 h-3 text-slate-300 group-hover:text-red-500 transition-colors" />
                  </div>
                </div>
                <div className="flex-1 space-y-3">
                  <div className="space-y-0.5">
                    <h4 className="text-xs font-bold text-[#1A2244] line-clamp-1">{grant.title}</h4>
                    <p className="text-xl font-black text-[#1A2244]">{grant.amount}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={cn(
                      "px-2 py-0.5 rounded-md text-[8px] font-bold uppercase tracking-widest flex items-center gap-1",
                      grant.status === 'Eligible' ? "bg-green-50 text-green-600" : 
                      grant.status === 'In Review' ? "bg-amber-50 text-amber-600" : 
                      "bg-slate-100 text-slate-500"
                    )}>
                      {grant.status === 'Eligible' && <CheckCircle2 className="w-3 h-3" />}
                      {grant.status === 'In Review' && <Clock className="w-3 h-3" />}
                      {grant.status === 'Not Eligible' && <Lock className="w-3 h-3" />}
                      {grant.status}
                    </span>
                  </div>
                  <div className="flex items-center justify-between pt-2 border-t border-slate-50">
                    <div className="space-y-0.5">
                      <p className="text-[8px] font-bold text-[#1A2244]">{grant.date}</p>
                      <p className="text-[8px] text-slate-400 font-bold uppercase tracking-widest">{grant.location}</p>
                    </div>
                    <button className={cn(
                      "px-4 py-1.5 text-[10px] font-black rounded-lg transition-all shadow-lg",
                      grant.status === 'Not Eligible' 
                        ? "bg-slate-100 text-slate-400 shadow-none cursor-not-allowed" 
                        : "bg-[#5B7CFA] text-white shadow-blue-500/10 hover:bg-[#4A6BEB]"
                    )}>
                      {grant.status === 'Not Eligible' ? 'Unlock' : 'Apply'}
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Bottom Section: Opportunities & Saved */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 glass-card p-6 space-y-6">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-[#1A2244]">Grant Opportunities</h3>
              <span className="text-[8px] text-slate-400 font-bold uppercase tracking-widest">Recent Updates</span>
            </div>
            <div className="space-y-3">
              {opportunities.map((opp, idx) => (
                <div key={idx} className="flex items-center gap-4 p-4 bg-slate-50 border border-slate-100 rounded-xl hover:bg-white hover:border-slate-200 transition-all group cursor-pointer">
                  <div className="w-10 h-10 rounded-lg bg-white border border-slate-100 flex items-center justify-center shrink-0 shadow-sm">
                    <Building2 className="w-5 h-5 text-[#5B7CFA]" />
                  </div>
                  <div className="flex-1">
                    <p className="text-xs font-bold text-[#1A2244] group-hover:text-[#5B7CFA] transition-colors">{opp.title}</p>
                    <p className="text-[8px] text-slate-400 font-bold uppercase tracking-widest mt-0.5">{opp.date}</p>
                  </div>
                  <div className="text-right space-y-1">
                    <p className="text-xs font-black text-[#1A2244]">{opp.amount}</p>
                    <span className={cn(
                      "px-2 py-0.5 rounded-md text-[8px] font-bold uppercase tracking-widest inline-block",
                      opp.status === 'In-Progress' ? "bg-blue-50 text-[#5B7CFA]" : 
                      opp.status === 'Registered' ? "bg-green-50 text-green-600" : 
                      "bg-amber-50 text-amber-600"
                    )}>
                      {opp.status}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="glass-card p-6 space-y-6">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-[#1A2244]">Saved Grants</h3>
              <button className="text-[8px] font-bold text-[#5B7CFA] uppercase tracking-widest hover:underline">View All</button>
            </div>
            <div className="space-y-4">
              {opportunities.map((opp, idx) => (
                <div key={idx} className="flex items-center gap-3 group cursor-pointer">
                  <div className="w-10 h-10 rounded-lg bg-slate-50 flex items-center justify-center shrink-0 border border-slate-100 group-hover:bg-white transition-colors">
                    <Building2 className="w-5 h-5 text-slate-300 group-hover:text-[#5B7CFA]" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-[10px] font-bold text-[#1A2244] truncate group-hover:text-[#5B7CFA] transition-colors">{opp.title}</p>
                    <p className="text-[8px] text-slate-400 font-bold uppercase tracking-widest mt-0.5">{opp.date} • <span className="text-green-600">In-Progress</span></p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* AI Assistant Banner */}
        <div className="glass-card p-6 flex flex-col lg:flex-row items-center justify-between bg-white border-slate-100 shadow-xl shrink-0">
          <div className="flex flex-col md:flex-row items-center gap-6 text-center md:text-left">
            <div className="w-20 h-20 bg-[#C5C9F7] rounded-2xl flex items-center justify-center shrink-0 overflow-hidden shadow-lg">
              <img 
                src="https://api.dicebear.com/7.x/bottts-neutral/svg?seed=NexusBotSmall&backgroundColor=c5c9f7&eyes=frame2" 
                alt="Bot" 
                className="w-14 h-14 object-contain drop-shadow-2xl"
              />
            </div>
            <div className="space-y-3">
              <h3 className="text-xl font-black text-[#1A2244] leading-tight">
                Our AI Assistant <br />
                <span className="text-[#5B7CFA] font-bold text-lg">can guide you through the process.</span>
              </h3>
              <div className="flex flex-wrap justify-center md:justify-start gap-2">
                <div className="flex items-center gap-2 px-3 py-1.5 bg-slate-50 border border-slate-100 rounded-lg shadow-sm hover:bg-white transition-colors">
                  <Mail className="w-3 h-3 text-[#5B7CFA]" />
                  <span className="text-[8px] font-bold text-[#1A2244] uppercase tracking-widest">Email</span>
                </div>
                <div className="flex items-center gap-2 px-3 py-1.5 bg-slate-50 border border-slate-100 rounded-lg shadow-sm hover:bg-white transition-colors">
                  <MessageSquare className="w-3 h-3 text-[#5B7CFA]" />
                  <span className="text-[8px] font-bold text-[#1A2244] uppercase tracking-widest">SMS</span>
                </div>
                <div className="flex items-center gap-2 px-3 py-1.5 bg-slate-50 border border-slate-100 rounded-lg shadow-sm hover:bg-white transition-colors">
                  <MessageCircle className="w-3 h-3 text-[#5B7CFA]" />
                  <span className="text-[8px] font-bold text-[#1A2244] uppercase tracking-widest">WhatsApp</span>
                </div>
              </div>
            </div>
          </div>
          <button className="mt-4 lg:mt-0 bg-[#5B7CFA] text-white px-6 py-3 rounded-xl text-sm font-black shadow-xl shadow-blue-500/20 hover:bg-[#4A6BEB] transition-all">
            Talk to Your AI
          </button>
        </div>
      </div>
    </div>
  );
}
