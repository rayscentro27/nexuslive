import React, { useState } from 'react';
import {
  Settings,
  Shield,
  Bell,
  Users,
  Globe,
  Database,
  Lock,
  Mail,
  Zap,
  ChevronRight,
  CreditCard,
  Key,
  DollarSign
} from 'lucide-react';
import { cn } from '../../lib/utils';
import { AdminSubscriptionSettings } from './AdminSubscriptionSettings';

type Section = 'general' | 'security' | 'notifications' | 'users' | 'integrations' | 'subscriptions';

export function AdminSettings({ onNavigate }: { onNavigate?: (tab: string) => void }) {
  const [activeSection, setActiveSection] = useState<Section>('general');

  const navItems: { label: string; icon: React.ElementType; id: Section }[] = [
    { label: 'General', icon: Settings, id: 'general' },
    { label: 'Subscriptions', icon: DollarSign, id: 'subscriptions' },
    { label: 'Security', icon: Shield, id: 'security' },
    { label: 'Notifications', icon: Bell, id: 'notifications' },
    { label: 'Users', icon: Users, id: 'users' },
    { label: 'Integrations', icon: Zap, id: 'integrations' },
  ];

  const sections = [
    {
      title: 'General Settings',
      items: [
        { label: 'Platform Branding', desc: 'Manage logos, colors, and theme settings.', icon: Globe },
        { label: 'Email Configuration', desc: 'Set up SMTP and system notifications.', icon: Mail },
        { label: 'User Management', desc: 'Control admin roles and permissions.', icon: Users },
      ]
    },
    {
      title: 'Security & Access',
      items: [
        { label: 'Authentication', desc: 'Manage OAuth providers and MFA settings.', icon: Lock },
        { label: 'API Keys', desc: 'Generate and manage system-wide API keys.', icon: Key },
        { label: 'Audit Logs', desc: 'View detailed system activity and security logs.', icon: Shield },
      ]
    },
    {
      title: 'System & Data',
      items: [
        { label: 'Database Backup', desc: 'Manage automated backups and data retention.', icon: Database },
        { label: 'Billing & Plans', desc: 'Manage platform subscription and usage limits.', icon: CreditCard, onClick: () => setActiveSection('subscriptions') },
        { label: 'Integrations', desc: 'Connect third-party services and webhooks.', icon: Zap },
      ]
    }
  ];

  return (
    <div className="p-8 space-y-8 bg-slate-50/50 min-h-full text-slate-600">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-black text-[#1A2244] tracking-tight">System Settings</h1>
          <p className="text-slate-500 font-medium mt-1 text-sm">Configure platform-wide parameters, security, and integrations.</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Settings Navigation */}
        <div className="lg:col-span-4 space-y-6">
          <div className="bg-white border border-slate-200 rounded-3xl p-6 shadow-sm">
            <h3 className="text-sm font-black text-[#1A2244] uppercase tracking-widest mb-6">Settings Menu</h3>
            <div className="space-y-2">
              {navItems.map((item) => (
                <button
                  key={item.id}
                  onClick={() => setActiveSection(item.id)}
                  className={cn(
                    "w-full flex items-center justify-between p-3 rounded-xl transition-all group",
                    activeSection === item.id
                      ? "bg-blue-50 text-[#5B7CFA]"
                      : "hover:bg-slate-50 text-slate-400 hover:text-[#1A2244]"
                  )}
                >
                  <div className="flex items-center gap-3">
                    <item.icon className="w-4 h-4" />
                    <span className="text-[10px] font-black uppercase tracking-widest">{item.label}</span>
                  </div>
                  <ChevronRight className={cn(
                    "w-4 h-4 transition-all",
                    activeSection === item.id ? "opacity-100" : "opacity-0 group-hover:opacity-100"
                  )} />
                </button>
              ))}
            </div>
          </div>

          <div className="bg-gradient-to-br from-[#1A2244] to-[#2A3354] rounded-3xl p-6 text-white shadow-xl">
            <h4 className="text-xs font-black uppercase tracking-widest mb-2">System Status</h4>
            <div className="flex items-center gap-2 text-green-400 mb-4">
              <div className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
              <span className="text-[10px] font-black uppercase tracking-widest">All Systems Operational</span>
            </div>
            <p className="text-[10px] text-slate-400 font-medium leading-relaxed mb-4">
              Version 2.4.0-stable. Last backup completed 2 hours ago.
            </p>
            <button onClick={() => onNavigate?.('reports')} className="w-full py-2 rounded-lg bg-white/10 hover:bg-white/20 text-[9px] font-black uppercase tracking-widest transition-all">
              View System Logs
            </button>
          </div>
        </div>

        {/* Settings Content */}
        <div className="lg:col-span-8">
          {activeSection === 'subscriptions' && <AdminSubscriptionSettings />}

          {activeSection !== 'subscriptions' && (
            <div className="space-y-8">
              {sections.filter((_, i) =>
                activeSection === 'general' ? i === 0 :
                activeSection === 'security' ? i === 1 :
                activeSection === 'integrations' ? i === 2 :
                activeSection === 'users' ? i === 0 :
                activeSection === 'notifications' ? i === 0 : true
              ).map((section, i) => (
                <div key={i} className="bg-white border border-slate-200 rounded-3xl overflow-hidden shadow-sm">
                  <div className="p-6 border-b border-slate-100 bg-slate-50/30">
                    <h3 className="text-sm font-black text-[#1A2244] uppercase tracking-widest">{section.title}</h3>
                  </div>
                  <div className="divide-y divide-slate-50">
                    {section.items.map((item, j) => (
                      <div
                        key={j}
                        onClick={(item as any).onClick}
                        className={cn(
                          "p-6 flex items-center justify-between transition-all group",
                          (item as any).onClick ? "cursor-pointer hover:bg-blue-50/50" : "hover:bg-slate-50/50 cursor-default"
                        )}
                      >
                        <div className="flex items-center gap-4">
                          <div className={cn(
                            "w-10 h-10 rounded-xl border flex items-center justify-center transition-all",
                            (item as any).onClick
                              ? "bg-blue-50 border-[#5B7CFA]/20 text-[#5B7CFA]"
                              : "bg-slate-50 border-slate-100 text-slate-400 group-hover:text-[#5B7CFA] group-hover:border-[#5B7CFA]/30"
                          )}>
                            <item.icon className="w-5 h-5" />
                          </div>
                          <div>
                            <h4 className="text-sm font-black text-[#1A2244]">{item.label}</h4>
                            <p className="text-xs text-slate-500 mt-1">{item.desc}</p>
                          </div>
                        </div>
                        {(item as any).onClick && (
                          <span className="text-[10px] font-black text-[#5B7CFA] uppercase tracking-widest">
                            Configure
                          </span>
                        )}
                        {!(item as any).onClick && (
                          <button className="text-[10px] font-black text-[#5B7CFA] uppercase tracking-widest opacity-0 group-hover:opacity-100 transition-all">
                            Configure
                          </button>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
