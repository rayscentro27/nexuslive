import React from 'react';
import { User, Mail, Phone, Building2, Shield, CreditCard, Bell, Globe, LogOut, ChevronRight, CheckCircle2 } from 'lucide-react';
import { cn } from '../lib/utils';

export function Account() {
  const user = {
    name: 'Mike Thompson',
    email: 'mike@aceresources.com',
    company: 'ACE Resources LLC',
    role: 'Owner / Administrator',
    avatar: 'https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?auto=format&fit=facearea&facepad=2&w=256&h=256&q=80',
    credits: 100,
    balance: 1290
  };

  return (
    <div className="p-4 max-w-6xl mx-auto space-y-4 h-full flex flex-col overflow-y-auto no-scrollbar">
      <div className="flex flex-col space-y-1 shrink-0">
        <h1 className="text-xl font-black text-[#1A2244]">Review Profile</h1>
        <p className="text-[10px] text-slate-500 font-bold uppercase tracking-widest">Manage your personal and professional identity.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 flex-1">
        {/* Left Column: Profile Card */}
        <div className="lg:col-span-2 space-y-4">
          <div className="glass-card p-5">
            <div className="flex items-center gap-6">
              <div className="relative shrink-0">
                <img 
                  src={user.avatar} 
                  alt={user.name}
                  className="w-24 h-24 rounded-2xl object-cover border-2 border-white shadow-lg"
                  referrerPolicy="no-referrer"
                />
                <div className="absolute -bottom-1 -right-1 bg-green-500 text-white p-1 rounded-lg border-2 border-white">
                  <CheckCircle2 className="w-3 h-3" />
                </div>
              </div>
              <div className="flex-1 space-y-2">
                <div className="space-y-0.5">
                  <div className="flex items-center gap-2">
                    <h2 className="text-lg font-black text-[#1A2244]">{user.name}</h2>
                    <span className="px-1.5 py-0.5 bg-blue-50 text-blue-600 text-[8px] font-black uppercase rounded-md">Pro</span>
                  </div>
                  <p className="text-xs text-slate-500 font-bold uppercase tracking-widest">{user.role}</p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <div className="flex items-center gap-1.5 text-[10px] text-slate-600 bg-slate-50 px-2 py-1 rounded-lg">
                    <Mail className="w-3 h-3 text-[#5B7CFA]" />
                    {user.email}
                  </div>
                </div>
              </div>
              <button className="bg-white border border-slate-100 text-[#1A2244] px-4 py-2 rounded-xl text-[10px] font-black uppercase tracking-widest hover:bg-slate-50 transition-all shrink-0">
                Edit
              </button>
            </div>
          </div>

          {/* Business Info */}
          <div className="glass-card p-5 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-black text-[#1A2244] flex items-center gap-2">
                <Building2 className="w-4 h-4 text-[#5B7CFA]" />
                Business Information
              </h3>
              <button className="text-[10px] font-black text-[#5B7CFA] uppercase tracking-widest">Edit</button>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-0.5">
                <p className="text-[8px] font-black text-slate-400 uppercase tracking-widest">Entity Name</p>
                <p className="text-xs font-bold text-slate-700">{user.company}</p>
              </div>
              <div className="space-y-0.5">
                <p className="text-[8px] font-black text-slate-400 uppercase tracking-widest">Entity Type</p>
                <p className="text-xs font-bold text-slate-700">LLC</p>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Credits & Quick Actions */}
        <div className="space-y-6">
          <div className="glass-card p-8 bg-gradient-to-br from-nexus-600 to-nexus-700 text-white">
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <div className="p-2 bg-white/10 rounded-xl">
                  <CreditCard className="w-6 h-6" />
                </div>
                <span className="text-xs font-bold uppercase tracking-widest opacity-60">Nexus Credits</span>
              </div>
              <div className="space-y-1">
                <h4 className="text-4xl font-black">${user.balance.toLocaleString()}</h4>
                <p className="text-sm font-medium opacity-60">{user.credits} credits available</p>
              </div>
              <div className="space-y-2">
                <div className="h-2 bg-white/10 rounded-full overflow-hidden">
                  <div className="h-full bg-white w-2/3" />
                </div>
                <div className="flex justify-between text-[10px] font-bold uppercase opacity-60">
                  <span>100 Credits</span>
                  <span>50 Remaining</span>
                </div>
              </div>
              <button className="w-full bg-white text-nexus-700 font-bold py-3 rounded-xl shadow-lg hover:bg-nexus-50 transition-all">
                Add Credits
              </button>
            </div>
          </div>

          <div className="glass-card p-6 space-y-2">
            <h3 className="px-2 text-xs font-bold text-slate-400 uppercase tracking-wider mb-4">Quick Settings</h3>
            {[
              { icon: Shield, label: 'Security & Privacy', color: 'text-blue-500' },
              { icon: Bell, label: 'Notifications', color: 'text-amber-500' },
              { icon: Globe, label: 'Integrations', color: 'text-purple-500' },
            ].map((item, i) => (
              <button key={i} className="w-full flex items-center justify-between p-3 hover:bg-slate-50 rounded-xl transition-all group">
                <div className="flex items-center gap-3">
                  <item.icon className={cn("w-5 h-5", item.color)} />
                  <span className="font-semibold text-slate-700">{item.label}</span>
                </div>
                <ChevronRight className="w-4 h-4 text-slate-300 group-hover:text-slate-400" />
              </button>
            ))}
            <div className="pt-4 mt-4 border-t border-slate-100">
              <button className="w-full flex items-center gap-3 p-3 text-red-600 hover:bg-red-50 rounded-xl transition-all font-bold">
                <LogOut className="w-5 h-5" />
                Sign Out
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
