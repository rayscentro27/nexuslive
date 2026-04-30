/**
 * AppShell — shared layout for all /app/* routes.
 * Uses react-router-dom Outlet for page content.
 * URL path drives the active sidebar item.
 */
import React, { useState } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import {
  Home, Zap, FileText, MessageSquare, CreditCard,
  TrendingUp, User, Settings, Building2, Shield,
  Map, Trophy, Bot, Lock, LogOut, Menu, X, ShieldCheck,
} from 'lucide-react';
import { useAuth } from './AuthProvider';
import { usePlan, PlanTier } from '../hooks/usePlan';
import { cn } from '../lib/utils';

const ROUTES: Array<{
  path: string;
  label: string;
  icon: React.ElementType;
  requiredPlan?: PlanTier;
  adminOnly?: boolean;
  divider?: boolean;
}> = [
  { path: '/app/dashboard',  label: 'Home',           icon: Home },
  { path: '/app/actions',    label: 'Actions',         icon: Zap },
  { path: '/app/messages',   label: 'Messages',        icon: MessageSquare },
  { path: '/app/documents',  label: 'Documents',       icon: FileText },
  { path: '',                label: '',                 icon: Home, divider: true },
  { path: '/app/funding',    label: 'Funding',         icon: CreditCard,  requiredPlan: 'pro' },
  { path: '/app/readiness',  label: 'Business Setup',  icon: Building2 },
  { path: '/app/trading',    label: 'Trading',         icon: TrendingUp,  requiredPlan: 'pro' },
  { path: '/app/credit',     label: 'Credit',          icon: Shield,      requiredPlan: 'pro' },
  { path: '/app/roadmap',    label: 'Roadmap',         icon: Map,         requiredPlan: 'elite' },
  { path: '/app/bots',       label: 'AI Workforce',    icon: Bot,         requiredPlan: 'elite' },
  { path: '',                label: '',                 icon: Home, divider: true },
  { path: '/app/account',    label: 'Account',         icon: User },
  { path: '/app/settings',   label: 'Settings',        icon: Settings },
  { path: '/app/admin',      label: 'Admin',           icon: ShieldCheck, adminOnly: true },
];

function getInitials(user: { email?: string; user_metadata?: { full_name?: string } } | null) {
  if (!user) return 'NX';
  const name = user.user_metadata?.full_name;
  if (name) return name.split(' ').map((n: string) => n[0]).join('').toUpperCase().slice(0, 2);
  return (user.email ?? 'NX').slice(0, 2).toUpperCase();
}

function SidebarContent({ onNavigate }: { onNavigate?: () => void }) {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, profile, signOut } = useAuth();
  const { plan, isAtLeast } = usePlan();
  const isAdmin = profile?.role === 'admin' || profile?.role === 'super_admin';

  const displayName = user?.user_metadata?.full_name ?? user?.email ?? 'Nexus User';

  function go(path: string) {
    navigate(path);
    onNavigate?.();
  }

  return (
    <div className="flex flex-col h-full" style={{ padding: '20px 12px' }}>
      {/* Logo */}
      <div className="flex items-center gap-2 mb-6 px-2">
        <div className="w-7 h-7 rounded-lg flex items-center justify-center shrink-0"
          style={{ background: 'linear-gradient(135deg, #3d5af1, #8b5cf6)' }}>
          <TrendingUp className="w-3.5 h-3.5 text-white" />
        </div>
        <span className="text-sm font-black text-[#1a1c3a] tracking-tight">Nexus</span>
      </div>

      {/* Nav items */}
      <nav className="flex-1 space-y-0.5 overflow-y-auto">
        {ROUTES.map((item, i) => {
          if (item.divider) return <div key={i} className="my-3 border-t border-slate-100" />;
          if (item.adminOnly && !isAdmin) return null;

          const locked = item.requiredPlan ? !isAtLeast(item.requiredPlan) : false;
          const isActive = location.pathname === item.path || location.pathname.startsWith(item.path + '/');

          return (
            <button
              key={item.path}
              onClick={() => !locked && go(item.path)}
              className={cn(
                'w-full flex items-center gap-2.5 px-3.5 py-2.5 rounded-xl text-sm transition-all',
                isActive
                  ? 'bg-[#eef0fd] text-[#3d5af1] font-semibold'
                  : locked
                  ? 'text-slate-300 cursor-default'
                  : 'text-[#8b8fa8] hover:bg-slate-50 hover:text-[#1a1c3a] font-medium'
              )}
            >
              <item.icon size={15} className="shrink-0" />
              <span className="flex-1 text-left">{item.label}</span>
              {locked && <Lock size={10} style={{ color: '#c7d2fe' }} />}
            </button>
          );
        })}
      </nav>

      {/* User footer */}
      <div className="border-t border-slate-100 pt-3 mt-2 space-y-1">
        <div className="flex items-center gap-2.5 px-2 py-1">
          <div className="w-8 h-8 rounded-full flex items-center justify-center shrink-0 text-xs font-bold text-white"
            style={{ background: 'linear-gradient(135deg, #3d5af1, #8b5cf6)' }}>
            {getInitials(user)}
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-xs font-semibold text-[#1a1c3a] truncate">{displayName}</div>
            <div className="text-[10px] text-slate-400 capitalize">Nexus {plan}</div>
          </div>
        </div>
        <button
          onClick={() => signOut().then(() => navigate('/'))}
          className="w-full flex items-center gap-2.5 px-3.5 py-2 rounded-xl text-xs text-slate-400 hover:text-red-500 hover:bg-red-50 transition-all font-medium"
        >
          <LogOut size={14} />
          Sign out
        </button>
      </div>
    </div>
  );
}

export function AppShell() {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <div className="flex h-screen overflow-hidden" style={{ background: '#eaebf6' }}>

      {/* Desktop sidebar */}
      <aside
        className="w-52 h-screen fixed left-0 top-0 z-40 hidden md:flex flex-col"
        style={{ background: '#fff', borderRight: '1px solid #e8e9f2' }}
      >
        <SidebarContent />
      </aside>

      {/* Mobile drawer */}
      {mobileOpen && (
        <div className="fixed inset-0 z-50 md:hidden">
          <div className="absolute inset-0 bg-black/30" onClick={() => setMobileOpen(false)} />
          <aside
            className="absolute left-0 top-0 bottom-0 w-60 flex flex-col"
            style={{ background: '#fff' }}
          >
            <button
              onClick={() => setMobileOpen(false)}
              className="absolute top-4 right-4 p-1 text-slate-400 hover:text-slate-600"
            >
              <X size={18} />
            </button>
            <SidebarContent onNavigate={() => setMobileOpen(false)} />
          </aside>
        </div>
      )}

      {/* Main content */}
      <main className="flex-1 flex flex-col h-screen overflow-hidden md:ml-[208px]">

        {/* Mobile top bar */}
        <div className="flex md:hidden items-center gap-3 px-4 py-3 bg-white border-b border-slate-100 shrink-0">
          <button onClick={() => setMobileOpen(true)} className="p-1 text-slate-500">
            <Menu size={20} />
          </button>
          <span className="text-sm font-black text-[#1a1c3a]">Nexus</span>
        </div>

        <div className="flex-1 overflow-y-auto scrollbar-hide">
          <Outlet />
        </div>

        <footer
          className="hidden md:block p-3 text-center text-[8px] font-bold uppercase tracking-widest shrink-0"
          style={{ color: '#8b8fa8', borderTop: '1px solid #e8e9f2', background: '#fff' }}
        >
          © 2026 Nexus · All rights reserved · Paper trading only
        </footer>
      </main>
    </div>
  );
}
