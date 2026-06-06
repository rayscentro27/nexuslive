import React, { useEffect, useState } from 'react';
import {
  LayoutDashboard, Home, MessageSquare, Video, TrendingUp,
  CheckCircle2, Bell, Network, BookOpen, Cpu, Brain,
} from 'lucide-react';
import { supabase } from '../../lib/supabase';
import type { OsSection } from './types';

interface DockItem { id: OsSection; label: string; icon: React.ElementType; badgeKey?: 'approvals' | 'notifications'; }

const DOCK: DockItem[] = [
  { id: 'overview', label: 'Overview', icon: LayoutDashboard },
  { id: 'command-center', label: 'Command', icon: Home },
  { id: 'hermes-chat', label: 'Hermes', icon: MessageSquare },
  { id: 'hermes-training', label: 'Training', icon: Brain },
  { id: 'content', label: 'Content', icon: Video },
  { id: 'trading', label: 'Trading', icon: TrendingUp },
  { id: 'approvals', label: 'Approvals', icon: CheckCircle2, badgeKey: 'approvals' },
  { id: 'notifications', label: 'Alerts', icon: Bell, badgeKey: 'notifications' },
  { id: 'graph', label: 'Graph', icon: Network },
  { id: 'knowledge', label: 'Artifacts', icon: BookOpen },
  { id: 'tools', label: 'Tools', icon: Cpu },
];

/**
 * Premium glass bottom dock for Nexus OS section navigation.
 * Token-driven (dark/light aware). Fixed bottom-center, horizontal scroll on mobile.
 */
export function NexusDock({ active, onNavigate }: { active: OsSection; onNavigate: (s: OsSection) => void }) {
  const [badges, setBadges] = useState<{ approvals: number; notifications: number }>({ approvals: 0, notifications: 0 });

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const [appr, notif] = await Promise.all([
          supabase.from('owner_approval_queue').select('id', { count: 'exact', head: true }).eq('status', 'pending'),
          supabase.from('notifications').select('id', { count: 'exact', head: true }).is('read_at', null).is('dismissed_at', null),
        ]);
        if (alive) setBadges({ approvals: appr.count ?? 0, notifications: notif.count ?? 0 });
      } catch { /* read-only, ignore */ }
    })();
    return () => { alive = false; };
  }, [active]);

  return (
    <div
      className="fixed left-1/2 -translate-x-1/2 z-[150]"
      style={{ bottom: 'calc(12px + env(safe-area-inset-bottom, 0px))', maxWidth: 'calc(100vw - 24px)' }}
    >
      <div
        className="flex items-center gap-1 px-2 py-1.5 rounded-2xl overflow-x-auto scrollbar-hide"
        style={{
          background: 'var(--nexus-surface)',
          border: '1px solid var(--nexus-border)',
          backdropFilter: 'blur(20px)',
          WebkitBackdropFilter: 'blur(20px)',
          boxShadow: '0 0 0 1px rgba(124,58,237,0.10), 0 18px 50px -12px rgba(59,130,246,0.40)',
        }}
      >
        {DOCK.map(item => {
          const Icon = item.icon;
          const isActive = active === item.id;
          const badge = item.badgeKey ? badges[item.badgeKey] : 0;
          return (
            <button
              key={item.id}
              onClick={() => onNavigate(item.id)}
              title={item.label}
              className="relative shrink-0 flex flex-col items-center justify-center gap-0.5 rounded-xl transition-all"
              style={{
                minWidth: 52, padding: '6px 8px',
                ...(isActive
                  ? { backgroundImage: 'linear-gradient(135deg, var(--nexus-purple), var(--nexus-blue))', color: '#fff' }
                  : { color: 'var(--nexus-text-muted)' }),
              }}
            >
              <Icon className="w-4 h-4" style={{ color: isActive ? '#fff' : 'var(--nexus-text-muted)' }} />
              <span className="text-[8px] font-bold tracking-wide" style={{ color: isActive ? '#fff' : 'var(--nexus-text-muted)' }}>
                {item.label}
              </span>
              {badge > 0 && (
                <span
                  className="absolute -top-0.5 -right-0.5 min-w-[15px] h-[15px] px-1 rounded-full text-[8px] font-black text-white flex items-center justify-center"
                  style={{ background: item.badgeKey === 'approvals' ? 'var(--nexus-warning)' : 'var(--nexus-danger)' }}
                >
                  {badge > 9 ? '9+' : badge}
                </span>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
