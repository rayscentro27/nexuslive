import React from 'react';
import { Bell, MessageSquare, Coins, Rocket } from 'lucide-react';
import { useAuth } from './AuthProvider';

function getInitials(user: { email?: string; user_metadata?: { full_name?: string } } | null): string {
  if (!user) return 'N';
  const name = user.user_metadata?.full_name;
  if (name) return name.split(' ').map((n: string) => n[0]).join('').toUpperCase().slice(0, 2);
  return (user.email ?? 'NX').slice(0, 2).toUpperCase();
}

export function Header({ onNavigate }: { onNavigate?: (tab: string) => void }) {
  const { user } = useAuth();
  const initials = getInitials(user);

  return (
    <header
      style={{
        height: 56,
        background: '#ffffff',
        borderBottom: '1px solid #e8e9f2',
        display: 'flex',
        alignItems: 'center',
        padding: '0 24px',
        gap: 16,
        flexShrink: 0,
        position: 'sticky',
        top: 0,
        zIndex: 40,
      }}
    >
      {/* Logo */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <div
          style={{
            width: 28,
            height: 28,
            borderRadius: 8,
            background: 'linear-gradient(135deg, #3d5af1, #5b8ef5)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <span style={{ color: '#fff', fontWeight: 800, fontSize: 15, fontFamily: 'serif' }}>N</span>
        </div>
        <span style={{ fontWeight: 700, fontSize: 16, color: '#1a1c3a', letterSpacing: -0.5 }}>Nexus</span>
      </div>

      <div style={{ flex: 1 }} />

      {/* Right Controls */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>

        {/* Score pill */}
        <div
          style={{
            background: '#eaebf6',
            borderRadius: 8,
            padding: '5px 12px',
            display: 'flex',
            alignItems: 'center',
            gap: 4,
            fontSize: 13,
            fontWeight: 600,
            color: '#1a1c3a',
          }}
        >
          <span>3%</span>
        </div>

        {/* Messages */}
        <button
          onClick={() => onNavigate?.('messages')}
          style={{
            background: '#eaebf6',
            borderRadius: 8,
            padding: '7px 10px',
            border: 'none',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <MessageSquare size={15} style={{ color: '#8b8fa8' }} />
        </button>

        {/* Bell */}
        <button
          style={{
            background: '#eaebf6',
            borderRadius: 8,
            padding: '7px 10px',
            border: 'none',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            position: 'relative',
          }}
        >
          <Bell size={15} style={{ color: '#8b8fa8' }} />
          <span
            style={{
              position: 'absolute',
              top: 5,
              right: 6,
              width: 7,
              height: 7,
              borderRadius: '50%',
              background: '#3d5af1',
              border: '1.5px solid #fff',
            }}
          />
        </button>

        {/* Coins */}
        <div
          style={{
            background: '#fff9e6',
            borderRadius: 8,
            padding: '5px 12px',
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            fontSize: 13,
            fontWeight: 600,
            color: '#92400e',
            cursor: 'pointer',
          }}
        >
          <Coins size={14} style={{ color: '#f59e0b' }} />
          <span>1,290</span>
        </div>

        {/* Rocket */}
        <div
          style={{
            background: '#eef0fd',
            borderRadius: 8,
            padding: '5px 10px',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
          }}
        >
          <Rocket size={16} style={{ color: '#3d5af1' }} />
        </div>

        {/* Avatar */}
        <div
          style={{
            width: 34,
            height: 34,
            borderRadius: '50%',
            background: 'linear-gradient(135deg, #3d5af1, #8b5cf6)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: 12,
            fontWeight: 700,
            color: '#fff',
            cursor: 'pointer',
            marginLeft: 4,
          }}
        >
          {initials}
        </div>
      </div>
    </header>
  );
}
