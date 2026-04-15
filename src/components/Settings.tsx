import React from 'react';
import { 
  User, 
  Shield, 
  CreditCard, 
  Building2, 
  Bell, 
  Link as LinkIcon, 
  Edit2, 
  Upload, 
  Trash2,
  ChevronRight,
  LogOut,
  Smartphone,
  Download,
  Plus,
  HelpCircle,
  Mail,
  MessageSquare
} from 'lucide-react';
import { cn } from '../lib/utils';
import { BotAvatar } from './BotAvatar';

const tabs = [
  { id: 'profile', label: 'Profile', icon: User },
  { id: 'security', label: 'Security', icon: Shield },
  { id: 'billing', label: 'Billing', icon: CreditCard },
  { id: 'business', label: 'Business Info', icon: Building2 },
  { id: 'notifications', label: 'Notifications', icon: Bell },
  { id: 'integrations', label: 'Integrations', icon: LinkIcon },
];

export function Settings() {
  const [activeTab, setActiveTab] = React.useState('profile');

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto h-full flex flex-col">
      <div className="space-y-0.5 shrink-0">
        <h2 className="text-2xl font-bold text-[#1A2244]">Settings</h2>
        <p className="text-xs text-slate-500 font-medium">Manage your profile, security, billing, and business information.</p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1.5 p-1 bg-slate-100 rounded-xl w-fit shrink-0">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={cn(
                "flex items-center gap-2 px-4 py-1.5 rounded-lg text-[10px] font-bold transition-all",
                isActive ? "bg-white text-[#5B7CFA] shadow-sm" : "text-slate-500 hover:text-slate-700"
              )}
            >
              <Icon className="w-3.5 h-3.5" />
              {tab.label}
            </button>
          );
        })}
      </div>

      <div className="flex-1 overflow-y-auto scrollbar-hide space-y-6 pr-1">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column: Form Sections */}
          <div className="lg:col-span-2 space-y-6">
            {/* Profile Information */}
            <div className="glass-card p-6 space-y-6 relative overflow-hidden">
              <div className="absolute -top-4 -right-4 opacity-10">
                <BotAvatar type="setup" size="xl" />
              </div>
              <div className="flex items-center justify-between relative z-10">
                <h3 className="text-base font-bold text-[#1A2244]">Profile Information</h3>
                <button className="text-[10px] font-bold text-[#5B7CFA] hover:underline flex items-center gap-1">
                  Edit <Edit2 className="w-2.5 h-2.5" />
                </button>
              </div>

              <div className="flex items-center gap-6">
                <div className="relative group">
                  <div className="w-16 h-16 rounded-2xl bg-[#C5C9F7] overflow-hidden border-2 border-white shadow-sm">
                    <img 
                      src="https://api.dicebear.com/7.x/notionists/svg?seed=Michael&backgroundColor=c5c9f7" 
                      alt="Avatar" 
                      referrerPolicy="no-referrer"
                    />
                  </div>
                  <button className="absolute -bottom-1 -right-1 p-1.5 bg-[#5B7CFA] text-white rounded-lg shadow-lg hover:scale-110 transition-transform">
                    <Upload className="w-3 h-3" />
                  </button>
                </div>
                <div className="space-y-0.5">
                  <div className="flex items-center gap-2">
                    <p className="text-lg font-bold text-[#1A2244]">Mike Thompson</p>
                    <span className="px-1.5 py-0.5 rounded-md bg-green-50 text-green-600 text-[8px] font-bold uppercase tracking-widest">Verified</span>
                  </div>
                  <p className="text-xs text-slate-500 font-medium">mike@aceresources.com</p>
                  <p className="text-xs font-bold text-slate-700">ACE Resources LLC</p>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <label className="text-[8px] font-bold text-slate-400 uppercase tracking-widest">Full Name</label>
                  <input type="text" defaultValue="Mike Thompson" className="w-full bg-slate-50 border border-slate-100 rounded-lg px-3 py-2 text-xs font-medium focus:outline-none focus:ring-2 focus:ring-blue-500/10" />
                </div>
                <div className="space-y-1.5">
                  <label className="text-[8px] font-bold text-slate-400 uppercase tracking-widest">Email</label>
                  <input type="email" defaultValue="mike@aceresources.com" className="w-full bg-slate-50 border border-slate-100 rounded-lg px-3 py-2 text-xs font-medium focus:outline-none focus:ring-2 focus:ring-blue-500/10" />
                </div>
                <div className="space-y-1.5">
                  <label className="text-[8px] font-bold text-slate-400 uppercase tracking-widest">Phone</label>
                  <input type="text" defaultValue="(555) 123-4567" className="w-full bg-slate-50 border border-slate-100 rounded-lg px-3 py-2 text-xs font-medium focus:outline-none focus:ring-2 focus:ring-blue-500/10" />
                </div>
                <div className="space-y-1.5">
                  <label className="text-[8px] font-bold text-slate-400 uppercase tracking-widest">Role</label>
                  <select className="w-full bg-slate-50 border border-slate-100 rounded-lg px-3 py-2 text-xs font-medium focus:outline-none focus:ring-2 focus:ring-blue-500/10 appearance-none">
                    <option>Owner / Administrator</option>
                    <option>Manager</option>
                    <option>Staff</option>
                  </select>
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-[8px] font-bold text-slate-400 uppercase tracking-widest">Business Logo</label>
                <div className="p-4 bg-slate-50 border-2 border-dashed border-slate-200 rounded-xl flex items-center justify-between group hover:border-[#5B7CFA]/30 transition-all cursor-pointer">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-white rounded-lg flex items-center justify-center border border-slate-100 shadow-sm">
                      <Building2 className="w-5 h-5 text-slate-300" />
                    </div>
                    <div className="text-left">
                      <p className="text-xs font-bold text-[#1A2244]">ACE Resources</p>
                      <p className="text-[8px] text-slate-400 font-bold uppercase tracking-widest">PNG, JPG up to 5MB</p>
                    </div>
                  </div>
                  <div className="flex gap-1.5">
                    <button className="p-1.5 text-slate-400 hover:text-[#5B7CFA] hover:bg-white rounded-lg transition-all"><Upload className="w-3.5 h-3.5" /></button>
                    <button className="p-1.5 text-slate-400 hover:text-red-500 hover:bg-white rounded-lg transition-all"><Trash2 className="w-3.5 h-3.5" /></button>
                  </div>
                </div>
              </div>
            </div>

            {/* Subscription & Billing */}
            <div className="glass-card p-6 space-y-6">
              <div className="flex items-center justify-between">
                <h3 className="text-base font-bold text-[#1A2244]">Subscription & Billing</h3>
                <span className="px-2 py-0.5 rounded-md bg-green-50 text-green-600 text-[8px] font-bold uppercase tracking-widest">Active</span>
              </div>

              <div className="p-4 bg-slate-50 border border-slate-100 rounded-xl flex items-center justify-between">
                <div className="space-y-0.5">
                  <p className="text-xs font-bold text-[#1A2244]">Nexus Pro</p>
                  <p className="text-[10px] text-slate-500 font-medium">Next billing date: May 1, 2025</p>
                </div>
                <p className="text-xl font-black text-[#1A2244]">$97<span className="text-[10px] font-bold text-slate-400">/mo</span></p>
              </div>

              <div className="space-y-3">
                <div className="flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2">
                    <div className="w-1.5 h-1.5 bg-[#5B7CFA] rounded-full" />
                    <span className="text-slate-600 font-bold">Monthly subscription</span>
                  </div>
                  <span className="font-black text-[#1A2244]">$97/mo</span>
                </div>
                <div className="flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2">
                    <div className="w-1.5 h-1.5 bg-[#5B7CFA] rounded-full" />
                    <span className="text-slate-600 font-bold">Funding success fee</span>
                  </div>
                  <span className="font-black text-[#1A2244]">10% of funds</span>
                </div>
              </div>

              <button className="w-full py-3 bg-[#5B7CFA] text-white font-black text-xs rounded-xl shadow-lg shadow-blue-500/20 hover:bg-[#4A6BEB] transition-all">Manage Subscription</button>
            </div>
          </div>

          {/* Right Column: Quick Actions & Preferences */}
          <div className="space-y-6">
            {/* Quick Actions */}
            <div className="glass-card p-5 space-y-5">
              <h3 className="text-sm font-bold text-[#1A2244]">Quick Actions</h3>
              <div className="space-y-1.5">
                <button className="w-full flex items-center justify-between p-2.5 bg-slate-50 border border-slate-100 rounded-lg hover:bg-slate-100 transition-all group">
                  <div className="flex items-center gap-2.5">
                    <Shield className="w-3.5 h-3.5 text-slate-400 group-hover:text-[#5B7CFA]" />
                    <span className="text-[10px] font-bold text-slate-700">Change Password</span>
                  </div>
                  <ChevronRight className="w-3.5 h-3.5 text-slate-300" />
                </button>
                <button className="w-full flex items-center justify-between p-2.5 bg-slate-50 border border-slate-100 rounded-lg hover:bg-slate-100 transition-all group">
                  <div className="flex items-center gap-2.5">
                    <Smartphone className="w-3.5 h-3.5 text-slate-400 group-hover:text-[#5B7CFA]" />
                    <span className="text-[10px] font-bold text-slate-700">2-Factor Auth</span>
                  </div>
                  <div className="w-6 h-3 bg-[#5B7CFA] rounded-full relative">
                    <div className="absolute right-0.5 top-0.5 w-2 h-2 bg-white rounded-full shadow-sm" />
                  </div>
                </button>
                <button className="w-full flex items-center justify-between p-2.5 bg-slate-50 border border-slate-100 rounded-lg hover:bg-slate-100 transition-all group">
                  <div className="flex items-center gap-2.5">
                    <Download className="w-3.5 h-3.5 text-slate-400 group-hover:text-[#5B7CFA]" />
                    <span className="text-[10px] font-bold text-slate-700">Download My Data</span>
                  </div>
                  <ChevronRight className="w-3.5 h-3.5 text-slate-300" />
                </button>
              </div>
              <button className="w-full py-2 text-[10px] font-black text-red-500 uppercase tracking-widest flex items-center justify-center gap-2 hover:bg-red-50 rounded-lg transition-all">
                <LogOut className="w-3.5 h-3.5" /> Sign Out
              </button>
            </div>

            {/* Payment Methods */}
            <div className="glass-card p-5 space-y-5">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-bold text-[#1A2244]">Payment Methods</h3>
                <button className="text-[10px] font-bold text-[#5B7CFA] flex items-center gap-1 hover:underline">
                  <Plus className="w-2.5 h-2.5" /> Add
                </button>
              </div>
              <div className="space-y-2">
                <div className="p-3 bg-slate-50 border border-slate-100 rounded-lg flex items-center justify-between group cursor-pointer hover:bg-slate-100 transition-all">
                  <div className="flex items-center gap-2.5">
                    <div className="w-8 h-5 bg-[#1A2244] rounded flex items-center justify-center text-[6px] font-bold text-white">VISA</div>
                    <div>
                      <p className="text-[10px] font-bold text-[#1A2244]">Visa •••• 4242</p>
                      <p className="text-[8px] text-slate-400 font-bold">Exp 12/2026</p>
                    </div>
                  </div>
                  <span className="text-[8px] font-bold text-slate-400 uppercase tracking-widest">Default</span>
                </div>
                <div className="p-3 bg-slate-50 border border-slate-100 rounded-lg flex items-center justify-between group cursor-pointer hover:bg-slate-100 transition-all">
                  <div className="flex items-center gap-2.5">
                    <div className="w-8 h-5 bg-blue-50 rounded flex items-center justify-center text-[6px] font-bold text-[#5B7CFA] uppercase">ACH</div>
                    <div>
                      <p className="text-[10px] font-bold text-[#1A2244]">Bank Account (ACH)</p>
                      <p className="text-[8px] text-slate-400 font-bold">•••• 6789</p>
                    </div>
                  </div>
                  <span className="text-[8px] font-bold text-green-600 uppercase tracking-widest">Verified</span>
                </div>
              </div>
            </div>

            {/* Notification Preferences */}
            <div className="glass-card p-5 space-y-5">
              <h3 className="text-sm font-bold text-[#1A2244]">Notifications</h3>
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2.5">
                    <div className="w-7 h-7 rounded-lg bg-slate-50 flex items-center justify-center">
                      <Mail className="w-3.5 h-3.5 text-slate-400" />
                    </div>
                    <div className="text-left">
                      <p className="text-[10px] font-bold text-[#1A2244]">Email</p>
                      <p className="text-[8px] text-slate-400 font-medium">Tasks & funding</p>
                    </div>
                  </div>
                  <div className="w-6 h-3 bg-[#5B7CFA] rounded-full relative">
                    <div className="absolute right-0.5 top-0.5 w-2 h-2 bg-white rounded-full shadow-sm" />
                  </div>
                </div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2.5">
                    <div className="w-7 h-7 rounded-lg bg-slate-50 flex items-center justify-center">
                      <MessageSquare className="w-3.5 h-3.5 text-slate-400" />
                    </div>
                    <div className="text-left">
                      <p className="text-[10px] font-bold text-[#1A2244]">SMS</p>
                      <p className="text-[8px] text-slate-400 font-medium">Real-time alerts</p>
                    </div>
                  </div>
                  <div className="w-6 h-3 bg-[#5B7CFA] rounded-full relative">
                    <div className="absolute right-0.5 top-0.5 w-2 h-2 bg-white rounded-full shadow-sm" />
                  </div>
                </div>
              </div>
            </div>

            {/* Support & Help */}
            <div className="glass-card p-5 space-y-3">
              <h3 className="text-sm font-bold text-[#1A2244]">Support & Help</h3>
              <div className="space-y-1">
                <button className="w-full flex items-center justify-between p-2 hover:bg-slate-50 rounded-lg transition-all group">
                  <div className="flex items-center gap-2.5">
                    <HelpCircle className="w-3.5 h-3.5 text-slate-400 group-hover:text-[#5B7CFA]" />
                    <span className="text-[10px] font-bold text-slate-700">Help Center</span>
                  </div>
                  <ChevronRight className="w-3.5 h-3.5 text-slate-300" />
                </button>
                <button className="w-full flex items-center justify-between p-2 hover:bg-slate-50 rounded-lg transition-all group">
                  <div className="flex items-center gap-2.5">
                    <Mail className="w-3.5 h-3.5 text-slate-400 group-hover:text-[#5B7CFA]" />
                    <span className="text-[10px] font-bold text-slate-700">Contact Support</span>
                  </div>
                  <ChevronRight className="w-3.5 h-3.5 text-slate-300" />
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
