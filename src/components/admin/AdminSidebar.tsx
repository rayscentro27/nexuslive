import React from 'react';
import { 
  LayoutDashboard, 
  Users, 
  BarChart3, 
  Cpu, 
  FileCheck, 
  ShieldAlert, 
  TrendingUp, 
  Settings,
  LogOut,
  ChevronRight,
  Zap,
  Briefcase,
  MessageSquare,
  FileText,
  PieChart,
  Building2,
  Lightbulb
} from 'lucide-react';
import { cn } from '../../lib/utils';

interface AdminSidebarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
}

export function AdminSidebar({ activeTab, setActiveTab }: AdminSidebarProps) {
  const menuItems = [
    { id: 'dashboard', label: 'Overview', icon: LayoutDashboard },
    { id: 'clients', label: 'Clients', icon: Users },
    { id: 'pipeline', label: 'Pipeline', icon: BarChart3 },
    { id: 'credit', label: 'Credit Ops', icon: ShieldAlert },
    { id: 'funding', label: 'Funding Engine', icon: Zap },
    { id: 'opportunities', label: 'Business Opportunities', icon: Lightbulb },
    { id: 'documents', label: 'Documents', icon: FileText },
    { id: 'messages', label: 'Messages', icon: MessageSquare },
    { id: 'ai-workforce', label: 'AI Workforce', icon: Cpu },
    { id: 'trading', label: 'Trading Lab', icon: TrendingUp },
    { id: 'my-business', label: 'My Business', icon: Building2 },
    { id: 'reports', label: 'Reports', icon: PieChart },
  ];

  return (
    <aside className="w-64 bg-white text-slate-500 flex flex-col h-screen fixed left-0 top-0 z-50 border-r border-slate-200">
      <div className="p-6 flex items-center gap-3 border-b border-slate-100 bg-slate-50/50">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-[#5B7CFA] to-[#4A6BEB] flex items-center justify-center shadow-lg shadow-blue-500/20">
          <Zap className="w-6 h-6 text-white fill-current" />
        </div>
        <div>
          <h1 className="text-lg font-black text-[#1A2244] tracking-tight leading-none">NEXUS</h1>
          <p className="text-[8px] font-black text-[#5B7CFA] uppercase tracking-[0.2em] mt-1">Admin OS v2.1</p>
        </div>
      </div>

      <nav className="flex-1 p-4 space-y-1 overflow-y-auto no-scrollbar">
        <p className="px-4 py-2 text-[10px] font-black text-slate-400 uppercase tracking-widest">Operations</p>
        {menuItems.map((item) => (
          <button
            key={item.id}
            onClick={() => setActiveTab(item.id)}
            className={cn(
              "w-full flex items-center justify-between px-4 py-2.5 rounded-xl transition-all group",
              activeTab === item.id 
                ? "bg-[#5B7CFA]/10 text-[#5B7CFA] shadow-sm" 
                : "hover:bg-slate-50 hover:text-[#1A2244]"
            )}
          >
            <div className="flex items-center gap-3">
              <item.icon className={cn(
                "w-4 h-4 transition-colors",
                activeTab === item.id ? "text-[#5B7CFA]" : "text-slate-400 group-hover:text-[#5B7CFA]"
              )} />
              <span className="text-xs font-bold tracking-tight">{item.label}</span>
            </div>
            {activeTab === item.id && <div className="w-1 h-4 bg-[#5B7CFA] rounded-full" />}
          </button>
        ))}
      </nav>

      <div className="p-4 border-t border-slate-100 space-y-1 bg-slate-50/30">
        <button 
          onClick={() => setActiveTab('settings')}
          className={cn(
            "w-full flex items-center gap-3 px-4 py-2.5 rounded-xl transition-all",
            activeTab === 'settings' ? "bg-[#5B7CFA]/10 text-[#5B7CFA]" : "text-slate-400 hover:bg-slate-50 hover:text-[#1A2244]"
          )}
        >
          <Settings className="w-4 h-4" />
          <span className="text-xs font-bold">Settings</span>
        </button>
        <button className="w-full flex items-center gap-3 px-4 py-2.5 rounded-xl hover:bg-red-50 hover:text-red-500 transition-all text-slate-400">
          <LogOut className="w-4 h-4" />
          <span className="text-xs font-bold">Exit Admin</span>
        </button>
      </div>
    </aside>
  );
}
