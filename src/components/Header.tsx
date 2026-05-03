import React from 'react';
import { MessageSquare, Coins, Rocket } from 'lucide-react';
import { useAuth } from './AuthProvider';
import { NotificationBell } from './NotificationBell';

function getInitials(user: { email?: string; user_metadata?: { full_name?: string } } | null): string {
  if (!user) return 'N';
  const name = user.user_metadata?.full_name;
  if (name) return name.split(' ').map((n: string) => n[0]).join('').toUpperCase().slice(0, 2);
  return (user.email ?? 'NX').slice(0, 2).toUpperCase();
}

export function Header({ onNavigate }: { onNavigate?: (tab: string) => void }) {
  const { user, profile } = useAuth();
  const initials = getInitials(user);
  const readinessScore = profile?.readiness_score ?? 0;

  return (
    <header className="flex items-center gap-2 md:gap-4 shrink-0 sticky top-0 z-40 bg-white border-b border-[#e8e9f2]"
      style={{ height: 56, padding: '0 16px' }}
    >
      {/* Logo — hidden on md+ since sidebar shows it */}
      <div className="flex md:hidden items-center gap-2">
        <div style={{ width: 28, height: 28, borderRadius: 8, background: 'linear-gradient(135deg, #3d5af1, #5b8ef5)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <span style={{ color: '#fff', fontWeight: 800, fontSize: 15, fontFamily: 'serif' }}>N</span>
        </div>
        <span style={{ fontWeight: 700, fontSize: 16, color: '#1a1c3a', letterSpacing: -0.5 }}>Nexus</span>
      </div>

      <div style={{ flex: 1 }} />

      {/* Right Controls */}
      <div className="flex items-center gap-2">

        {/* Score pill — hidden on small phones */}
        <div className="hidden sm:flex items-center gap-1 rounded-lg px-3 py-1.5 text-sm font-semibold text-[#1a1c3a]"
          style={{ background: '#eaebf6' }}>
          <span>{readinessScore}%</span>
        </div>

        {/* Messages */}
        <button
          onClick={() => onNavigate?.('messages')}
          className="rounded-lg flex items-center justify-center"
          style={{ background: '#eaebf6', padding: '8px 10px', border: 'none', cursor: 'pointer' }}
        >
          <MessageSquare size={16} style={{ color: '#8b8fa8' }} />
        </button>

        {/* Notification Bell — real, live */}
        <NotificationBell onOpenPage={() => onNavigate?.('notifications')} />

        {/* Coins — hidden on mobile */}
        <div className="hidden sm:flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-semibold cursor-pointer"
          style={{ background: '#fff9e6', color: '#92400e' }}>
          <Coins size={14} style={{ color: '#f59e0b' }} />
          <span>1,290</span>
        </div>

        {/* Rocket — hidden on mobile */}
        <div className="hidden md:flex items-center rounded-lg cursor-pointer"
          style={{ background: '#eef0fd', padding: '7px 10px' }}>
          <Rocket size={16} style={{ color: '#3d5af1' }} />
        </div>

        {/* Avatar */}
        <div className="rounded-full flex items-center justify-center text-xs font-bold text-white cursor-pointer"
          style={{ width: 34, height: 34, background: 'linear-gradient(135deg, #3d5af1, #8b5cf6)', flexShrink: 0 }}>
          {initials}
        </div>
      </div>
    </header>
  );
}
