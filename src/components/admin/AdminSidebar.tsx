import React from 'react';
import {
  LayoutDashboard,
  Users,
  BarChart3,
  Cpu,
  FileText,
  ShieldAlert,
  TrendingUp,
  Settings,
  LogOut,
  Zap,
  MessageSquare,
  PieChart,
  Building2,
  Lightbulb,
} from 'lucide-react';

interface AdminSidebarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
}

const menuItems = [
  { id: 'dashboard',     label: 'Overview',              icon: LayoutDashboard },
  { id: 'clients',       label: 'Clients',               icon: Users },
  { id: 'pipeline',      label: 'Pipeline',              icon: BarChart3 },
  { id: 'credit',        label: 'Credit Ops',            icon: ShieldAlert },
  { id: 'funding',       label: 'Funding Engine',        icon: Zap },
  { id: 'opportunities', label: 'Business Opportunities', icon: Lightbulb },
  { id: 'documents',     label: 'Documents',             icon: FileText },
  { id: 'messages',      label: 'Messages',              icon: MessageSquare },
  { id: 'ai-workforce',  label: 'AI Workforce',          icon: Cpu },
  { id: 'trading',       label: 'Trading Lab',           icon: TrendingUp },
  { id: 'my-business',   label: 'My Business',           icon: Building2 },
  { id: 'reports',       label: 'Reports',               icon: PieChart },
];

export function AdminSidebar({ activeTab, setActiveTab }: AdminSidebarProps) {
  return (
    <div
      className="w-52 h-screen flex-col fixed left-0 top-0 z-50 hidden md:flex"
      style={{
        background: '#ffffff',
        borderRight: '1px solid #e8e9f2',
        padding: '20px 12px',
      }}
    >
      {/* Logo + ADMIN badge */}
      <div className="flex items-center gap-2.5 px-2 mb-4">
        <div
          style={{
            width: 32,
            height: 32,
            borderRadius: 8,
            background: 'linear-gradient(135deg, #1a1c3a, #2d3068)',
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

      {/* ADMIN badge */}
      <div className="px-2 mb-5">
        <span
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 5,
            background: '#1a1c3a',
            color: '#ffffff',
            fontSize: 9,
            fontWeight: 800,
            letterSpacing: '0.18em',
            borderRadius: 6,
            padding: '3px 8px',
            textTransform: 'uppercase',
          }}
        >
          <span
            style={{
              width: 5,
              height: 5,
              borderRadius: '50%',
              background: '#22c55e',
              flexShrink: 0,
              display: 'inline-block',
            }}
          />
          Admin Portal
        </span>
      </div>

      {/* Navigation */}
      <nav
        className="flex-1 overflow-y-auto no-scrollbar"
        style={{ display: 'flex', flexDirection: 'column', gap: 2 }}
      >
        <div
          style={{
            fontSize: 9,
            fontWeight: 800,
            color: '#8b8fa8',
            letterSpacing: '0.18em',
            textTransform: 'uppercase',
            padding: '0 14px',
            marginBottom: 6,
          }}
        >
          Operations
        </div>

        {menuItems.map((item) => {
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
                transition: 'background 0.15s, color 0.15s',
                width: '100%',
                textAlign: 'left',
                fontFamily: 'inherit',
              }}
              onMouseEnter={(e) => {
                if (!isActive) {
                  (e.currentTarget as HTMLButtonElement).style.background = '#f5f6fb';
                  (e.currentTarget as HTMLButtonElement).style.color = '#1a1c3a';
                }
              }}
              onMouseLeave={(e) => {
                if (!isActive) {
                  (e.currentTarget as HTMLButtonElement).style.background = 'transparent';
                  (e.currentTarget as HTMLButtonElement).style.color = '#8b8fa8';
                }
              }}
            >
              <Icon
                size={16}
                style={{ color: isActive ? '#3d5af1' : '#8b8fa8', flexShrink: 0 }}
              />
              <span style={{ flex: 1 }}>{item.label}</span>
              {isActive && (
                <span
                  style={{
                    width: 4,
                    height: 16,
                    borderRadius: 2,
                    background: '#3d5af1',
                    flexShrink: 0,
                  }}
                />
              )}
            </button>
          );
        })}
      </nav>

      {/* Footer actions */}
      <div style={{ borderTop: '1px solid #e8e9f2', paddingTop: 12, marginTop: 8, display: 'flex', flexDirection: 'column', gap: 2 }}>
        <button
          onClick={() => setActiveTab('settings')}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 10,
            padding: '9px 14px',
            borderRadius: 10,
            cursor: 'pointer',
            border: 'none',
            background: activeTab === 'settings' ? '#eef0fd' : 'transparent',
            color: activeTab === 'settings' ? '#3d5af1' : '#8b8fa8',
            fontWeight: activeTab === 'settings' ? 600 : 400,
            fontSize: 14,
            transition: 'background 0.15s, color 0.15s',
            width: '100%',
            textAlign: 'left',
            fontFamily: 'inherit',
          }}
        >
          <Settings size={16} style={{ color: activeTab === 'settings' ? '#3d5af1' : '#8b8fa8', flexShrink: 0 }} />
          <span>Settings</span>
        </button>

        <button
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 10,
            padding: '9px 14px',
            borderRadius: 10,
            cursor: 'pointer',
            border: 'none',
            background: 'transparent',
            color: '#8b8fa8',
            fontWeight: 400,
            fontSize: 14,
            transition: 'background 0.15s, color 0.15s',
            width: '100%',
            textAlign: 'left',
            fontFamily: 'inherit',
          }}
          onMouseEnter={(e) => {
            (e.currentTarget as HTMLButtonElement).style.background = '#fef2f2';
            (e.currentTarget as HTMLButtonElement).style.color = '#ef4444';
          }}
          onMouseLeave={(e) => {
            (e.currentTarget as HTMLButtonElement).style.background = 'transparent';
            (e.currentTarget as HTMLButtonElement).style.color = '#8b8fa8';
          }}
        >
          <LogOut size={16} style={{ flexShrink: 0 }} />
          <span>Exit Admin</span>
        </button>

        {/* Admin identity footer */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '10px 4px 0 4px', marginTop: 4 }}>
          <div
            style={{
              width: 34,
              height: 34,
              borderRadius: '50%',
              background: 'linear-gradient(135deg, #1a1c3a, #3d5af1)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0,
              fontSize: 13,
              fontWeight: 700,
              color: '#fff',
            }}
          >
            AR
          </div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: 12, fontWeight: 600, color: '#1a1c3a', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              Admin Root
            </div>
            <div style={{ fontSize: 11, color: '#3d5af1', textTransform: 'uppercase', letterSpacing: '0.08em', fontWeight: 600 }}>
              Superuser
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
