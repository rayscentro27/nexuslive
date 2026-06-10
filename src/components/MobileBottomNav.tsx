import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  Home, TrendingUp, CreditCard, MessageSquare, Zap,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { cn } from '../lib/utils';
import { usePlan, PlanTier } from '../hooks/usePlan';

type NavItem = {
  path: string;
  label: string;
  icon: LucideIcon;
  requiredPlan?: PlanTier;
};

const NAV_ITEMS: NavItem[] = [
  { path: '/app/dashboard', label: 'Home',    icon: Home },
  { path: '/app/trading',   label: 'Trading', icon: TrendingUp, requiredPlan: 'pro' },
  { path: '/app/funding',   label: 'Funding', icon: CreditCard, requiredPlan: 'pro' },
  { path: '/app/messages',  label: 'Inbox',   icon: MessageSquare },
  { path: '/app/actions',   label: 'Actions', icon: Zap },
];

const BADGES: Record<string, string> = {
  '/app/messages': '3',
  '/app/actions': '2',
};

export function MobileBottomNav() {
  const navigate = useNavigate();
  const location = useLocation();
  const { isAtLeast } = usePlan();

  return (
    <nav className="dock-nav md:hidden safe-area-bottom" aria-label="Primary navigation dock">
      <div className="flex items-center justify-around gap-0.5 px-1 pt-1 pb-safe">
        {NAV_ITEMS.map(item => {
          const locked = item.requiredPlan ? !isAtLeast(item.requiredPlan) : false;
          const isActive = location.pathname === item.path ||
                           location.pathname.startsWith(item.path + '/');

          return (
            <button
              key={item.path}
              onClick={() => !locked && navigate(item.path)}
              className={cn(
                'group relative flex flex-col items-center gap-0.5 px-2.5 py-1.5 rounded-2xl transition-all min-w-[54px] hover:-translate-y-1',
                isActive
                  ? 'text-[#3d5af1]'
                  : locked
                  ? 'text-slate-200'
                  : 'text-slate-400 active:scale-95'
              )}
            >
              <div className={cn(
                'w-8 h-8 flex items-center justify-center rounded-xl transition-all',
                isActive ? 'bg-[#eef0fd] shadow-[0_0_0_3px_rgba(91,124,250,0.18)]' : 'group-hover:bg-white/80'
              )}>
                <item.icon
                  size={18}
                  strokeWidth={isActive ? 2.5 : 1.75}
                />
              </div>
              <span className={cn(
                'text-[9px] font-bold leading-none',
                isActive ? 'text-[#3d5af1]' : 'text-slate-400'
              )}>
                {item.label}
              </span>
              {!isActive && BADGES[item.path] ? (
                <span className="absolute right-1 top-1 min-w-4 h-4 px-1 rounded-full bg-red-500 text-white text-[9px] font-black flex items-center justify-center border border-white">
                  {BADGES[item.path]}
                </span>
              ) : null}
            </button>
          );
        })}
      </div>
    </nav>
  );
}
