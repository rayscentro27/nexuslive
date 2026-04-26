import React from 'react';
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
  Building2,
  Shield,
  Trophy,
  TrendingUp,
  Lock,
} from 'lucide-react';
import { useAuth } from './AuthProvider';

interface SidebarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
}

const menuItems = [
  { id: 'home',           label: 'Home',           icon: Home },
  { id: 'action-center',  label: 'Actions',         icon: Zap,          badge: '2' },
  { id: 'documents',      label: 'Documents',       icon: FileText },
  { id: 'messages',       label: 'Messages',        icon: MessageSquare },
  { id: 'funding',        label: 'Funding',         icon: CreditCard },
  { id: 'grants',         label: 'Grants',          icon: PlusCircle },
  { id: 'trading',        label: 'Trading',         icon: TrendingUp },
  { id: 'account',        label: 'Account',         icon: User },
  { id: 'settings',       label: 'Settings',        icon: Settings },
  { id: 'divider1',       label: '',                icon: Home,         isDivider: true },
  { id: 'business-setup', label: 'Business Setup',  icon: Building2 },
  { id: 'credit',         label: 'Credit Analysis', icon: Shield },
  { id: 'roadmap',        label: 'Roadmap',         icon: Map },
  { id: 'referral',       label: 'Refer & Earn',    icon: Trophy },
];

function getInitials(user: { email?: string; user_metadata?: { full_name?: string } } | null): string {
  if (!user) return 'N';
  const name = user.user_metadata?.full_name;
  if (name) return name.split(' ').map((n: string) => n[0]).join('').toUpperCase().slice(0, 2);
  return (user.email ?? 'NX').slice(0, 2).toUpperCase();
}

export function Sidebar({ activeTab, setActiveTab }: SidebarProps) {
  const { user } = useAuth();
  const initials = getInitials(user);
  const displayName = user?.user_metadata?.full_name ?? user?.email ?? 'Nexus User';

  return (
    <div
      className="w-52 h-screen flex-col fixed left-0 top-0 z-50 hidden md:flex"
      style={{
        background: '#ffffff',
        borderRight: '1px solid #e8e9f2',
        padding: '20px 12px',
      }}
    >
      {/* Logo */}
      <div className="flex items-center gap-2.5 px-2 mb-7">
        <div
          style={{
            width: 32,
            height: 32,
            borderRadius: 8,
            background: 'linear-gradient(135deg, #3d5af1, #5b8ef5)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0,
          }}
        >
          <span style={{ color: '#fff', fontWeight: 800, fontSize: 18, fontFamily: 'serif', letterSpacing: -1 }}>N</span>
        </div>
        <span style={{ fontWeight: 700, fontSize: 17, color: '#1a1c3a', letterSpacing: -0.5 }}>Nexus</span>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto no-scrollbar" style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
        {menuItems.map((item) => {
          if ('isDivider' in item && item.isDivider) {
            return <div key={item.id} style={{ height: 1, background: '#e8e9f2', margin: '8px 4px' }} />;
          }

          const isActive = activeTab === item.id;
          const Icon = item.icon;

          return (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 10,
                padding: '9px 14px',
                borderRadius: 10,
                cursor: 'pointer',
                border: 'none',
                background: isActive ? '#eef0fd' : 'transparent',
                color: isActive ? '#3d5af1' : '#8b8fa8',
                fontWeight: isActive ? 600 : 400,
                fontSize: 14,
                transition: 'background 0.15s',
                width: '100%',
                textAlign: 'left',
                fontFamily: 'inherit',
              }}
            >
              <Icon
                size={16}
                style={{ color: isActive ? '#3d5af1' : '#8b8fa8', flexShrink: 0 }}
              />
              <span style={{ flex: 1 }}>{item.label}</span>
              {'badge' in item && item.badge && (
                <span
                  style={{
                    background: '#3d5af1',
                    color: '#fff',
                    borderRadius: 10,
                    fontSize: 10,
                    fontWeight: 700,
                    padding: '1px 6px',
                  }}
                >
                  {item.badge}
                </span>
              )}
            </button>
          );
        })}
      </nav>

      {/* User Profile */}
      <div style={{ borderTop: '1px solid #e8e9f2', paddingTop: 16, marginTop: 8 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '0 4px' }}>
          <div
            style={{
              width: 34,
              height: 34,
              borderRadius: '50%',
              background: 'linear-gradient(135deg, #3d5af1, #8b5cf6)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0,
              fontSize: 13,
              fontWeight: 700,
              color: '#fff',
            }}
          >
            {initials}
          </div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: 12, fontWeight: 600, color: '#1a1c3a', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {displayName}
            </div>
            <div style={{ fontSize: 11, color: '#8b8fa8' }}>Nexus Pro</div>
          </div>
        </div>
      </div>
    </div>
  );
}
