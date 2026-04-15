import React from 'react';
import { 
  Building2, 
  MapPin, 
  Globe, 
  Eye, 
  ShieldCheck, 
  TrendingUp,
  Search,
  Settings,
  FileText,
  ArrowRight,
  CheckCircle2,
  Clock,
  AlertCircle,
  MoreHorizontal,
  Plus
} from 'lucide-react';
import { cn } from '../lib/utils';
import { BotAvatar } from './BotAvatar';

const sections = [
  {
    id: 'business',
    title: 'Business',
    icon: Building2,
    items: [
      { label: 'NexusOne Inc.', sub: 'LLC', status: 'verified' },
      { label: 'EN101 349127', sub: 'EIN', status: 'verified' },
    ]
  },
  {
    id: 'presence',
    title: 'Presence',
    icon: MapPin,
    items: [
      { label: '1234 Peachtree St NE', sub: 'Address', status: 'verified' },
      { label: '190% Next 30, Atl, T.S, Dorwes', sub: 'Phone', status: 'verified' },
    ]
  },
  {
    id: 'website',
    title: 'Website',
    icon: Globe,
    items: [
      { label: 'http://pove.atomait.com', sub: 'URL', status: 'verified' },
      { label: '+1 855-455-7300', sub: 'Contact', status: 'verified' },
    ]
  },
  {
    id: 'visibility',
    title: 'Visibility',
    icon: Eye,
    items: [
      { label: 'Google indexing', sub: 'Status', type: 'toggle', active: true },
      { label: 'Domain email', sub: 'Setup', type: 'toggle', active: false },
    ]
  },
  {
    id: 'compliance',
    title: 'Compliance',
    icon: ShieldCheck,
    items: [
      { label: 'DUNS', sub: 'Number', status: 'verified' },
      { label: 'Secretary of State', sub: 'Status', status: 'pending' },
    ]
  },
  {
    id: 'credit',
    title: 'Credit Foundation',
    icon: TrendingUp,
    items: [
      { label: 'DUNS', sub: 'Report', status: 'verified' },
      { label: 'Tradelines', sub: 'Pending', status: 'pending' },
    ]
  }
];

export function BusinessSetup() {
  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between shrink-0">
        <div className="space-y-0.5">
          <h2 className="text-2xl font-bold text-[#1A2244]">Business Setup</h2>
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Business readiness</span>
            <span className="px-1.5 py-0.5 rounded-md bg-green-50 text-green-600 text-[8px] font-bold uppercase tracking-widest">Readiness 65%</span>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button className="flex items-center gap-2 px-4 py-2 bg-white border border-slate-100 rounded-xl text-xs font-bold text-[#1A2244] shadow-sm hover:bg-slate-50 transition-all">
            <Search className="w-3.5 h-3.5" />
            View audit
          </button>
          <button className="p-2 bg-white border border-slate-100 rounded-xl text-slate-400 hover:text-[#5B7CFA] transition-all shadow-sm">
            <Settings className="w-4 h-4" />
          </button>
          <button className="p-2 bg-white border border-slate-100 rounded-xl text-slate-400 hover:text-[#5B7CFA] transition-all shadow-sm">
            <FileText className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="glass-card p-6 space-y-4 shrink-0 relative overflow-hidden">
        <div className="flex items-center justify-between relative z-10">
          <h3 className="text-sm font-bold text-[#1A2244]">Identity</h3>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1.5 px-1.5 py-0.5 rounded-md bg-green-50 text-green-600 text-[8px] font-black">
              <CheckCircle2 className="w-3.5 h-3.5" />
              65%
            </div>
            <BotAvatar type="setup" size="sm" />
          </div>
        </div>
        <div className="w-full h-2 bg-slate-100 rounded-full overflow-hidden relative z-10">
          <div className="w-[65%] h-full bg-gradient-to-r from-[#5B7CFA] to-[#3A5EE5] shadow-[0_0_8px_rgba(91,124,250,0.4)]" />
        </div>
      </div>

      {/* Grid of Sections */}
      <div className="flex-1 overflow-y-auto scrollbar-hide pr-1">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {sections.map((section) => {
            const Icon = section.icon;
            return (
              <div key={section.id} className="glass-card p-5 space-y-4 group hover:border-[#5B7CFA]/20 transition-all">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg bg-blue-50 flex items-center justify-center text-[#5B7CFA] group-hover:scale-110 transition-transform">
                      <Icon className="w-4 h-4" />
                    </div>
                    <h3 className="text-sm font-bold text-[#1A2244]">{section.title}</h3>
                  </div>
                  <button className="p-1 text-slate-300 hover:text-slate-500 transition-all">
                    <MoreHorizontal className="w-4 h-4" />
                  </button>
                </div>

                <div className="space-y-2">
                  {section.items.map((item, i) => (
                    <div key={i} className="flex items-center justify-between p-3 bg-slate-50/50 border border-slate-100 rounded-xl group/item hover:bg-white hover:shadow-sm transition-all">
                      <div className="flex flex-col">
                        <span className="text-xs font-bold text-[#1A2244] truncate max-w-[180px]">{item.label}</span>
                        <span className="text-[8px] text-slate-400 font-bold uppercase tracking-widest">{item.sub}</span>
                      </div>
                      
                      {item.type === 'toggle' ? (
                        <div className={cn(
                          "w-8 h-4 rounded-full relative transition-all",
                          item.active ? "bg-[#5B7CFA]" : "bg-slate-200"
                        )}>
                          <div className={cn(
                            "absolute top-0.5 w-3 h-3 bg-white rounded-full shadow-sm transition-all",
                            item.active ? "right-0.5" : "left-0.5"
                          )} />
                        </div>
                      ) : (
                        <div className="flex items-center gap-2">
                          {item.status === 'verified' && (
                            <span className="px-1.5 py-0.5 rounded-md bg-green-50 text-green-600 text-[8px] font-bold uppercase tracking-widest">Verified</span>
                          )}
                          {item.status === 'pending' && (
                            <span className="px-1.5 py-0.5 rounded-md bg-amber-50 text-amber-600 text-[8px] font-bold uppercase tracking-widest">Pending</span>
                          )}
                          <button className="p-1 text-slate-300 hover:text-[#5B7CFA] transition-all">
                            <ArrowRight className="w-3 h-3" />
                          </button>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Footer Action */}
      <div className="glass-card p-4 bg-blue-50/50 border-blue-100/50 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-4">
          <div className="w-10 h-10 rounded-xl bg-white shadow-sm flex items-center justify-center">
            <AlertCircle className="w-5 h-5 text-amber-500" />
          </div>
          <div>
            <p className="text-xs font-bold text-[#1A2244]">Next Action: <span className="text-slate-500 font-medium">Complete Domain Email.</span></p>
            <p className="text-[8px] text-slate-400 font-bold uppercase tracking-widest">Starting this will increase your readiness score</p>
          </div>
        </div>
        <button className="bg-[#5B7CFA] text-white px-8 py-2.5 rounded-xl font-black text-xs shadow-lg shadow-blue-500/20 hover:bg-[#4A6BEB] transition-all flex items-center gap-3 group">
          Start
          <div className="w-6 h-6 bg-white/20 rounded-lg flex items-center justify-center group-hover:translate-x-1 transition-all">
            <ArrowRight className="w-3.5 h-3.5" />
          </div>
        </button>
      </div>
    </div>
  );
}
