import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  Home, TrendingUp, CreditCard, MessageSquare, Zap,
} from 'lucide-react';
import { cn } from '../lib/utils';
import { usePlan, PlanTier } from '../hooks/usePlan';

type NavItem = {
  path: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  requiredPlan?: PlanTier;
};

const NAV_ITEMS: NavItem[] = [
  { path: '/app/dashboard', label: 'Home',    icon: Home },
  { path: '/app/trading',   label: 'Trading', icon: TrendingUp, requiredPlan: 'pro' },
  { path: '/app/funding',   label: 'Funding', icon: CreditCard, requiredPlan: 'pro' },
  { path: '/app/messages',  label: 'Inbox',   icon: MessageSquare },
  { path: '/app/actions',   label: 'Actions', icon: Zap },
];

export function MobileBottomNav() {
  const navigate = useNavigate();
  const location = useLocation();
  const { isAtLeast } = usePlan();

  return (
    <nav className="md:hidden fixed bottom-0 left-0 right-0 z-50 bg-white border-t border-slate-100 safe-area-bottom">
      <div className="flex items-center justify-around px-2 pt-2 pb-safe">
        {NAV_ITEMS.map(item => {
          const locked = item.requiredPlan ? !isAtLeast(item.requiredPlan) : false;
          const isActive = location.pathname === item.path ||
                           location.pathname.startsWith(item.path + '/');

          return (
            <button
              key={item.path}
              onClick={() => !locked && navigate(item.path)}
              className={cn(
                'flex flex-col items-center gap-0.5 px-3 py-1.5 rounded-xl transition-all min-w-[56px]',
                isActive
                  ? 'text-[#3d5af1]'
                  : locked
                  ? 'text-slate-200'
                  : 'text-slate-400 active:scale-95'
              )}
            >
              <div className={cn(
                'w-8 h-8 flex items-center justify-center rounded-xl transition-all',
                isActive ? 'bg-[#eef0fd]' : ''
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
            </button>
          );
        })}
      </div>
    </nav>
  );
}
