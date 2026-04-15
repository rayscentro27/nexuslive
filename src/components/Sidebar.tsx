import React from 'react';
import { cn } from '../lib/utils';
import { 
  Home, 
  Zap, 
  FileText, 
  MessageSquare, 
  CreditCard, 
  Map, 
  PlusCircle, 
  User, 
  Settings,
  ChevronDown,
  Shield,
  Building2,
  Sparkles,
  Trophy,
  Lock
} from 'lucide-react';

interface SidebarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
}

const menuItems = [
  { id: 'home', label: 'Home', icon: Home },
  { id: 'action-center', label: 'Actions', icon: Zap, badge: '3' },
  { id: 'messages', label: 'Messages', icon: MessageSquare },
  { id: 'documents', label: 'Documents', icon: FileText },
  { id: 'funding', label: 'Funding', icon: CreditCard },
  { id: 'account', label: 'Account', icon: User },
  { id: 'roadmap', label: 'Roadmap', icon: Map },
  { id: 'settings', label: 'Settings', icon: Settings },
  { id: 'divider', label: '', icon: Home, isDivider: true },
  { id: 'business-setup', label: 'Business Setup', icon: Building2 },
  { id: 'credit', label: 'Credit Analysis', icon: Shield },
  { id: 'grants', label: 'Grants Finder', icon: PlusCircle, isLocked: true },
  { id: 'trading', label: 'Trading Lab', icon: Zap, isLocked: true },
  { id: 'referral', label: 'Refer & Earn', icon: Zap },
  { id: 'rewards', label: 'Rewards', icon: Trophy },
  { id: 'auth', label: 'Auth (Demo)', icon: Shield },
];

export function Sidebar({ activeTab, setActiveTab }: SidebarProps) {
  return (
    <div className="w-64 h-screen flex flex-col p-6 fixed left-0 top-0 z-50 bg-transparent">
      {/* Logo */}
      <div className="flex items-center gap-3 mb-10 px-2">
        <div className="w-10 h-10 bg-[#5B7CFA] rounded-xl flex items-center justify-center shadow-lg shadow-blue-500/20">
          <span className="text-white font-black text-2xl">N</span>
        </div>
        <span className="text-2xl font-bold tracking-tight text-[#1A2244]">Nexus</span>
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-1 overflow-y-auto no-scrollbar">
        {menuItems.map((item) => {
          if ('isDivider' in item && item.isDivider) {
            return <div key={item.id} className="h-px bg-slate-200/50 my-4 mx-4" />;
          }

          const isActive = activeTab === item.id;
          const Icon = item.icon;
          const isLocked = 'isLocked' in item && item.isLocked;
          
          return (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={cn(
                "w-full flex items-center gap-3 px-4 py-2.5 rounded-2xl transition-all duration-200 group relative",
                isActive 
                  ? "bg-white text-[#5B7CFA] shadow-[0_4px_12px_rgba(0,0,0,0.05)]" 
                  : "text-[#4A5568] hover:bg-white/40",
                isLocked && "opacity-60 grayscale-[0.5]"
              )}
            >
              <div className={cn(
                "w-8 h-8 rounded-full flex items-center justify-center transition-colors",
                isActive ? "bg-[#5B7CFA] text-white" : "text-[#5B7CFA]"
              )}>
                <Icon className="w-4 h-4" />
              </div>
              <span className={cn(
                "font-semibold text-sm tracking-tight",
                isActive ? "text-[#1A2244]" : "text-[#4A5568]"
              )}>
                {item.label}
              </span>
              {isLocked ? (
                <Lock className="ml-auto w-3 h-3 text-slate-400" />
              ) : 'badge' in item && item.badge && (
                <span className="ml-auto bg-blue-100 text-[#5B7CFA] text-[10px] font-black px-2 py-0.5 rounded-lg">
                  {item.badge}
                </span>
              )}
            </button>
          );
        })}
      </nav>

      {/* Nexus Pro Card */}
      <div className="mt-auto pt-6">
        <div className="bg-white/40 backdrop-blur-xl border border-white/60 p-5 rounded-[2rem] shadow-xl shadow-blue-500/5 space-y-4">
          <div className="space-y-1">
            <h3 className="text-lg font-bold text-[#1A2244]">Nexus Pro</h3>
            <p className="text-[11px] font-bold text-[#5B7CFA]">You're on the Mo Plan</p>
          </div>
          <p className="text-[10px] text-slate-500 leading-relaxed font-medium">
            Utilize with our expert support for readiness.
          </p>
          <button className="w-full bg-[#5B7CFA] text-white text-xs font-bold py-3 rounded-2xl shadow-lg shadow-blue-500/30 hover:bg-[#4A6BEB] transition-all">
            Upgrade Plan
          </button>
        </div>
      </div>
    </div>
  );
}
